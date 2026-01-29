"""JWT Service for session token management.

Provides:
- JWT-based session tokens for API authentication
- Token encryption for secure storage of ESI tokens
- Proactive token refresh scheduling
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from ..core.config import settings

# =============================================================================
# Configuration Constants
# =============================================================================

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
JWT_REFRESH_THRESHOLD_MINUTES = 30  # Refresh if expiring within this time

# ESI token refresh threshold (refresh 5 minutes before expiry)
ESI_REFRESH_THRESHOLD_SECONDS = 300


# =============================================================================
# JWT Models
# =============================================================================


class JWTPayload(BaseModel):
    """JWT payload structure."""

    sub: int  # character_id as subject
    name: str  # character_name
    scopes: list[str]  # ESI scopes
    iat: datetime  # issued at
    exp: datetime  # expiration
    jti: str  # unique token ID for revocation
    fingerprint: str | None = None  # optional client fingerprint


class JWTToken(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    character_id: int
    character_name: str


# =============================================================================
# Token Encryption (for ESI tokens at rest)
# =============================================================================


def _derive_key(secret: str, salt: bytes) -> bytes:
    """Derive encryption key from secret using PBKDF2."""
    return hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 100000, dklen=32)


def encrypt_token(plaintext: str, secret: str | None = None) -> str:
    """Encrypt a token for secure storage.

    Uses XOR cipher with derived key for simplicity (no external deps).
    For production with higher security needs, use cryptography.Fernet.

    Args:
        plaintext: Token to encrypt
        secret: Encryption key (defaults to settings.SECRET_KEY)

    Returns:
        Base64-encoded encrypted token with salt prefix
    """
    if not plaintext:
        return plaintext

    secret = secret or settings.SECRET_KEY
    salt = os.urandom(16)
    key = _derive_key(secret, salt)

    # XOR cipher (simple but effective with good key derivation)
    plaintext_bytes = plaintext.encode()
    encrypted = bytes(p ^ key[i % len(key)] for i, p in enumerate(plaintext_bytes))

    # Combine salt + encrypted data
    combined = salt + encrypted
    return base64.b64encode(combined).decode()


def decrypt_token(encrypted: str, secret: str | None = None) -> str:
    """Decrypt a stored token.

    Args:
        encrypted: Base64-encoded encrypted token
        secret: Encryption key (defaults to settings.SECRET_KEY)

    Returns:
        Decrypted plaintext token
    """
    if not encrypted:
        return encrypted

    secret = secret or settings.SECRET_KEY

    try:
        combined = base64.b64decode(encrypted.encode())
        salt = combined[:16]
        encrypted_data = combined[16:]

        key = _derive_key(secret, salt)
        decrypted = bytes(e ^ key[i % len(key)] for i, e in enumerate(encrypted_data))
        return decrypted.decode()
    except Exception:
        # Return original if decryption fails (backward compatibility)
        return encrypted


# =============================================================================
# JWT Generation and Validation
# =============================================================================


def _base64url_encode(data: bytes) -> str:
    """Base64URL encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _base64url_decode(data: str) -> bytes:
    """Base64URL decode with padding restoration."""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode())


def generate_jwt(
    character_id: int,
    character_name: str,
    scopes: list[str],
    expiry_hours: int = JWT_EXPIRY_HOURS,
    fingerprint: str | None = None,
) -> JWTToken:
    """Generate a JWT session token.

    Args:
        character_id: EVE character ID
        character_name: Character name
        scopes: Granted ESI scopes
        expiry_hours: Token validity in hours
        fingerprint: Optional client fingerprint for token binding

    Returns:
        JWTToken with access token and metadata
    """
    now = datetime.now(UTC)
    expires = now + timedelta(hours=expiry_hours)
    jti = secrets.token_urlsafe(16)

    payload = JWTPayload(
        sub=character_id,
        name=character_name,
        scopes=scopes,
        iat=now,
        exp=expires,
        jti=jti,
        fingerprint=fingerprint,
    )

    # Create JWT
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header).encode())

    # Convert datetime to timestamp for JSON serialization
    payload_dict = payload.model_dump()
    payload_dict["iat"] = int(payload.iat.timestamp())
    payload_dict["exp"] = int(payload.exp.timestamp())
    payload_b64 = _base64url_encode(json.dumps(payload_dict).encode())

    # Sign
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    access_token = f"{message}.{signature_b64}"

    return JWTToken(
        access_token=access_token,
        expires_at=expires,
        character_id=character_id,
        character_name=character_name,
    )


def validate_jwt(
    token: str, verify_fingerprint: str | None = None
) -> tuple[JWTPayload | None, str | None]:
    """Validate a JWT token.

    Args:
        token: JWT token string
        verify_fingerprint: Optional fingerprint to verify against

    Returns:
        Tuple of (payload, error_message). payload is None if invalid.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None, "Invalid token format"

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256
        ).digest()
        actual_sig = _base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None, "Invalid signature"

        # Decode payload
        payload_json = json.loads(_base64url_decode(payload_b64).decode())

        # Convert timestamps back to datetime
        payload_json["iat"] = datetime.fromtimestamp(payload_json["iat"], tz=UTC)
        payload_json["exp"] = datetime.fromtimestamp(payload_json["exp"], tz=UTC)

        payload = JWTPayload(**payload_json)

        # Check expiration
        if datetime.now(UTC) >= payload.exp:
            return None, "Token expired"

        # Check fingerprint if provided
        if verify_fingerprint and payload.fingerprint:
            if payload.fingerprint != verify_fingerprint:
                return None, "Token fingerprint mismatch"

        return payload, None

    except json.JSONDecodeError:
        return None, "Invalid token payload"
    except Exception as e:
        return None, f"Token validation error: {str(e)}"


def should_refresh_jwt(payload: JWTPayload) -> bool:
    """Check if JWT should be refreshed (approaching expiration).

    Args:
        payload: JWT payload

    Returns:
        True if token should be refreshed
    """
    threshold = timedelta(minutes=JWT_REFRESH_THRESHOLD_MINUTES)
    return datetime.now(UTC) + threshold >= payload.exp


# =============================================================================
# ESI Token Refresh Utilities
# =============================================================================


def should_refresh_esi_token(expires_at: datetime) -> bool:
    """Check if ESI token should be proactively refreshed.

    Args:
        expires_at: Token expiration time

    Returns:
        True if token should be refreshed
    """
    threshold = timedelta(seconds=ESI_REFRESH_THRESHOLD_SECONDS)
    return datetime.now(UTC) + threshold >= expires_at


def generate_client_fingerprint(
    user_agent: str | None = None, ip_address: str | None = None
) -> str:
    """Generate a client fingerprint for token binding.

    Args:
        user_agent: Client User-Agent header
        ip_address: Client IP address

    Returns:
        Fingerprint hash
    """
    data = f"{user_agent or ''}{ip_address or ''}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# =============================================================================
# Token Revocation Support
# =============================================================================

# In-memory revocation list (use Redis for production multi-instance)
_revoked_tokens: set[str] = set()
_revoked_token_expiry: dict[str, datetime] = {}


def revoke_token(jti: str, expires_at: datetime) -> None:
    """Add a token to the revocation list.

    Args:
        jti: JWT token ID
        expires_at: Token expiration (for cleanup)
    """
    _revoked_tokens.add(jti)
    _revoked_token_expiry[jti] = expires_at


def is_token_revoked(jti: str) -> bool:
    """Check if a token has been revoked.

    Args:
        jti: JWT token ID

    Returns:
        True if token is revoked
    """
    return jti in _revoked_tokens


def cleanup_revoked_tokens() -> int:
    """Remove expired tokens from revocation list.

    Returns:
        Number of tokens cleaned up
    """
    now = datetime.now(UTC)
    expired = [jti for jti, exp in _revoked_token_expiry.items() if now >= exp]

    for jti in expired:
        _revoked_tokens.discard(jti)
        _revoked_token_expiry.pop(jti, None)

    return len(expired)


def clear_revoked_tokens() -> int:
    """Clear all revoked tokens (for testing).

    Returns:
        Number of tokens cleared
    """
    count = len(_revoked_tokens)
    _revoked_tokens.clear()
    _revoked_token_expiry.clear()
    return count
