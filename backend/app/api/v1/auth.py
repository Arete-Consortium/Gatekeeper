"""ESI OAuth2 Authentication Routes.

Implements EVE SSO authentication flow:
1. /auth/login - Redirects to EVE SSO
2. /auth/callback - Handles OAuth callback
3. /auth/refresh - Refreshes expired tokens
4. /auth/me - Returns authenticated character info
5. /auth/logout - Clears session
6. /auth/token - Issue JWT session token
7. /auth/verify - Verify JWT token

Security Features:
- JWT session tokens for stateless API authentication
- Encrypted token storage at rest
- Proactive token refresh
- Client fingerprinting (optional)
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.database import get_db
from ...db.models import User
from ...services.jwt_service import (
    cleanup_revoked_tokens,
    generate_client_fingerprint,
    generate_jwt,
    is_token_revoked,
    revoke_token,
    should_refresh_esi_token,
    validate_jwt,
)
from ...services.token_store import TokenStore, get_token_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# =============================================================================
# Response Models
# =============================================================================


class CharacterInfo(BaseModel):
    """Authenticated character information."""

    character_id: int
    character_name: str
    scopes: list[str]
    expires_at: datetime
    authenticated: bool = True
    needs_refresh: bool = False


class AuthStatus(BaseModel):
    """Authentication status."""

    authenticated: bool
    character: CharacterInfo | None = None


class TokenResponse(BaseModel):
    """Token refresh response."""

    access_token: str
    expires_at: datetime
    character_id: int


class LoginResponse(BaseModel):
    """Login initiation response."""

    auth_url: str
    state: str


class JWTTokenResponse(BaseModel):
    """JWT session token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    character_id: int
    character_name: str
    refresh_recommended: bool = False


class TokenVerification(BaseModel):
    """JWT token verification result."""

    valid: bool
    character_id: int | None = None
    character_name: str | None = None
    expires_at: datetime | None = None
    error: str | None = None


# =============================================================================
# OAuth State Management
# =============================================================================

# State configuration
OAUTH_STATE_TTL_MINUTES = 10
OAUTH_STATE_MAX_ENTRIES = 10000  # Prevent memory exhaustion

# In-memory state storage (use Redis in production)
_oauth_states: dict[str, datetime] = {}


def generate_state(ttl_minutes: int = OAUTH_STATE_TTL_MINUTES) -> str:
    """Generate a secure random state parameter.

    Args:
        ttl_minutes: State validity in minutes

    Returns:
        Secure random state token
    """
    # Enforce max entries to prevent memory exhaustion
    if len(_oauth_states) >= OAUTH_STATE_MAX_ENTRIES:
        cleanup_expired_states()
        # If still over limit, remove oldest entries
        if len(_oauth_states) >= OAUTH_STATE_MAX_ENTRIES:
            sorted_states = sorted(_oauth_states.items(), key=lambda x: x[1])
            for state, _ in sorted_states[: len(sorted_states) // 2]:
                _oauth_states.pop(state, None)

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
    return state


def validate_state(state: str) -> bool:
    """Validate and consume OAuth state.

    State tokens are single-use to prevent replay attacks.

    Args:
        state: State token to validate

    Returns:
        True if state is valid and not expired
    """
    if state not in _oauth_states:
        return False
    expires = _oauth_states.pop(state)
    return datetime.now(UTC) < expires


def cleanup_expired_states() -> int:
    """Remove expired state tokens.

    Returns:
        Number of expired states removed
    """
    now = datetime.now(UTC)
    expired = [s for s, exp in _oauth_states.items() if now >= exp]
    for s in expired:
        _oauth_states.pop(s, None)
    return len(expired)


def get_state_count() -> int:
    """Get current number of pending OAuth states.

    Returns:
        Number of active state tokens
    """
    return len(_oauth_states)


# =============================================================================
# ESI Scopes Configuration
# =============================================================================

# Default scopes for navigation features
DEFAULT_SCOPES = [
    "esi-location.read_location.v1",  # Current system
    "esi-location.read_online.v1",  # Online status
    "esi-ui.write_waypoint.v1",  # Set autopilot
    "esi-characters.read_standings.v1",  # Faction standings for route safety
    "esi-search.search_structures.v1",  # Search for structures
]


# =============================================================================
# Routes
# =============================================================================


@router.get("/login", response_model=LoginResponse)
async def login(
    redirect_uri: str | None = Query(None, description="Override callback URL"),
    scopes: str | None = Query(None, description="Space-separated ESI scopes"),
) -> LoginResponse:
    """
    Initiate EVE SSO login.

    Returns the authorization URL to redirect the user to EVE's login page.
    The state parameter should be stored and validated on callback.
    """
    if not settings.ESI_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="ESI OAuth not configured. Set ESI_CLIENT_ID environment variable.",
        )

    # Clean up expired states
    cleanup_expired_states()

    # Generate state for CSRF protection
    state = generate_state()

    # Parse scopes
    scope_list = scopes.split() if scopes else DEFAULT_SCOPES

    # Build authorization URL
    callback = redirect_uri or settings.ESI_CALLBACK_URL
    from urllib.parse import urlencode

    params = {
        "response_type": "code",
        "client_id": settings.ESI_CLIENT_ID,
        "redirect_uri": callback,
        "scope": " ".join(scope_list),
        "state": state,
    }
    auth_url = f"https://login.eveonline.com/v2/oauth/authorize?{urlencode(params)}"

    logger.info("Login initiated", extra={"scopes_requested": len(scope_list)})
    return LoginResponse(auth_url=auth_url, state=state)


@router.get("/login/redirect")
async def login_redirect(
    redirect_uri: str | None = Query(None),
    scopes: str | None = Query(None),
) -> RedirectResponse:
    """
    Redirect directly to EVE SSO.

    For browser-based flows, use this endpoint to immediately redirect
    to EVE's login page instead of returning the URL.
    """
    login_response = await login(redirect_uri=redirect_uri, scopes=scopes)
    return RedirectResponse(url=login_response.auth_url, status_code=302)


@router.get("/callback")
async def callback(
    code: str = Query(..., description="Authorization code from EVE SSO"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    token_store: TokenStore = Depends(get_token_store),
    db: AsyncSession = Depends(get_db),
) -> CharacterInfo:
    """
    Handle OAuth callback from EVE SSO.

    Exchanges the authorization code for access and refresh tokens,
    then stores them for the authenticated character.
    """
    # Validate state
    if not validate_state(state):
        logger.warning("OAuth callback failed: invalid state")
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired state parameter",
        )

    if not settings.ESI_CLIENT_ID or not settings.ESI_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="ESI OAuth not configured",
        )

    # Exchange code for tokens
    import httpx

    async with httpx.AsyncClient() as client:
        # Token exchange
        token_response = await client.post(
            "https://login.eveonline.com/v2/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
            },
            auth=(settings.ESI_CLIENT_ID, settings.ESI_SECRET_KEY),
        )

        if token_response.status_code != 200:
            logger.warning(
                "OAuth token exchange failed",
                extra={"status_code": token_response.status_code},
            )
            raise HTTPException(
                status_code=400,
                detail=f"Token exchange failed: {token_response.text}",
            )

        token_data = token_response.json()

        # Verify token and get character info
        verify_response = await client.get(
            "https://login.eveonline.com/oauth/verify",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )

        if verify_response.status_code != 200:
            logger.warning("OAuth token verification failed")
            raise HTTPException(
                status_code=400,
                detail="Token verification failed",
            )

        verify_data = verify_response.json()

    # Calculate expiration
    expires_at = datetime.now(UTC) + timedelta(seconds=token_data["expires_in"] - 60)

    # Store token
    character_id = verify_data["CharacterID"]
    await token_store.store_token(
        character_id=character_id,
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=expires_at,
        character_name=verify_data["CharacterName"],
        scopes=verify_data.get("Scopes", "").split(),
    )

    # Upsert User row (auto-create on first login)
    result = await db.execute(select(User).where(User.character_id == character_id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            character_id=character_id,
            character_name=verify_data["CharacterName"],
            subscription_tier="free",
        )
        db.add(user)
    else:
        user.character_name = verify_data["CharacterName"]
    await db.flush()

    logger.info(
        "OAuth callback successful",
        extra={"character_id": character_id, "character_name": verify_data["CharacterName"]},
    )
    return CharacterInfo(
        character_id=character_id,
        character_name=verify_data["CharacterName"],
        scopes=verify_data.get("Scopes", "").split(),
        expires_at=expires_at,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    character_id: int = Query(..., description="Character ID to refresh token for"),
    token_store: TokenStore = Depends(get_token_store),
) -> TokenResponse:
    """
    Refresh an expired access token.

    Uses the stored refresh token to obtain a new access token.
    """
    if not settings.ESI_CLIENT_ID or not settings.ESI_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="ESI OAuth not configured",
        )

    # Get stored token
    stored = await token_store.get_token(character_id)
    if not stored:
        raise HTTPException(
            status_code=404,
            detail="No token found for character",
        )

    # Refresh the token
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://login.eveonline.com/v2/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": stored["refresh_token"],
            },
            auth=(settings.ESI_CLIENT_ID, settings.ESI_SECRET_KEY),
        )

        if response.status_code != 200:
            # Token may be revoked, remove it
            logger.warning(
                "Token refresh failed",
                extra={"character_id": character_id, "status_code": response.status_code},
            )
            await token_store.remove_token(character_id)
            raise HTTPException(
                status_code=401,
                detail="Token refresh failed. Please re-authenticate.",
            )

        token_data = response.json()

    # Update stored token
    expires_at = datetime.now(UTC) + timedelta(seconds=token_data["expires_in"] - 60)
    await token_store.store_token(
        character_id=character_id,
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=expires_at,
        character_name=stored["character_name"],
        scopes=stored["scopes"],
    )

    logger.info("Token refreshed", extra={"character_id": character_id})
    return TokenResponse(
        access_token=token_data["access_token"],
        expires_at=expires_at,
        character_id=character_id,
    )


@router.get("/me", response_model=AuthStatus)
async def get_current_user(
    character_id: int = Query(..., description="Character ID to check"),
    token_store: TokenStore = Depends(get_token_store),
) -> AuthStatus:
    """
    Get current authentication status for a character.

    Returns character info if authenticated, or authenticated=False otherwise.
    The needs_refresh flag indicates if the token should be proactively refreshed.
    """
    stored = await token_store.get_token(character_id)

    if not stored:
        return AuthStatus(authenticated=False)

    now = datetime.now(UTC)
    is_expired = now >= stored["expires_at"]
    needs_refresh = not is_expired and should_refresh_esi_token(stored["expires_at"])

    # Check if token is expired
    if is_expired:
        return AuthStatus(
            authenticated=False,
            character=CharacterInfo(
                character_id=character_id,
                character_name=stored["character_name"],
                scopes=stored["scopes"],
                expires_at=stored["expires_at"],
                authenticated=False,
                needs_refresh=True,
            ),
        )

    return AuthStatus(
        authenticated=True,
        character=CharacterInfo(
            character_id=character_id,
            character_name=stored["character_name"],
            scopes=stored["scopes"],
            expires_at=stored["expires_at"],
            needs_refresh=needs_refresh,
        ),
    )


@router.get("/characters")
async def list_characters(
    token_store: TokenStore = Depends(get_token_store),
) -> list[CharacterInfo]:
    """
    List all authenticated characters.

    Returns a list of all characters that have valid stored tokens.
    The needs_refresh flag indicates which tokens should be proactively refreshed.
    """
    characters = await token_store.list_characters()
    now = datetime.now(UTC)

    return [
        CharacterInfo(
            character_id=char["character_id"],
            character_name=char["character_name"],
            scopes=char["scopes"],
            expires_at=char["expires_at"],
            authenticated=now < char["expires_at"],
            needs_refresh=should_refresh_esi_token(char["expires_at"]),
        )
        for char in characters
    ]


@router.post("/logout")
async def logout(
    character_id: int = Query(..., description="Character ID to log out"),
    token_store: TokenStore = Depends(get_token_store),
) -> dict[str, str]:
    """
    Log out a character by removing their stored tokens.
    """
    removed = await token_store.remove_token(character_id)

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="No token found for character",
        )

    logger.info("Character logged out", extra={"character_id": character_id})
    return {"status": "logged_out", "character_id": str(character_id)}


@router.delete("/tokens")
async def clear_all_tokens(
    token_store: TokenStore = Depends(get_token_store),
) -> dict[str, str]:
    """
    Clear all stored tokens (admin function).

    Use with caution - this logs out all characters.
    """
    count = await token_store.clear_all()
    logger.warning("All tokens cleared", extra={"tokens_removed": count})
    return {"status": "cleared", "tokens_removed": str(count)}


# =============================================================================
# JWT Session Token Endpoints
# =============================================================================


@router.post("/token", response_model=JWTTokenResponse)
async def issue_jwt_token(
    character_id: int = Query(..., description="Character ID to issue token for"),
    token_store: TokenStore = Depends(get_token_store),
    db: AsyncSession = Depends(get_db),
    request: Request = None,  # type: ignore[assignment]
    user_agent: str | None = Header(None),
) -> JWTTokenResponse:
    """
    Issue a JWT session token for API authentication.

    This endpoint issues a stateless JWT that can be used with Bearer authentication
    instead of passing character_id in query parameters. The JWT is bound to the
    client fingerprint for additional security.

    The returned token should be included in requests as:
        Authorization: Bearer <token>

    Returns:
        JWT token with expiration info
    """
    stored = await token_store.get_token(character_id)

    if not stored:
        raise HTTPException(
            status_code=404,
            detail="No ESI token found for character. Please authenticate via /auth/login first.",
        )

    now = datetime.now(UTC)
    if now >= stored["expires_at"]:
        raise HTTPException(
            status_code=401,
            detail="ESI token expired. Please refresh via /auth/refresh first.",
        )

    # Generate client fingerprint for token binding
    client_ip = None
    if request:
        client_ip = request.client.host if request.client else None
    fingerprint = generate_client_fingerprint(user_agent, client_ip)

    # Look up subscription tier
    tier_result = await db.execute(
        select(User.subscription_tier).where(User.character_id == stored["character_id"])
    )
    tier = tier_result.scalar_one_or_none() or "free"

    # Generate JWT
    jwt_token = generate_jwt(
        character_id=stored["character_id"],
        character_name=stored["character_name"],
        scopes=stored["scopes"],
        fingerprint=fingerprint,
        tier=tier,
    )

    # Check if ESI token needs refresh
    needs_refresh = should_refresh_esi_token(stored["expires_at"])

    logger.info(
        "JWT token issued",
        extra={"character_id": stored["character_id"], "character_name": stored["character_name"]},
    )
    return JWTTokenResponse(
        access_token=jwt_token.access_token,
        token_type=jwt_token.token_type,
        expires_at=jwt_token.expires_at,
        character_id=jwt_token.character_id,
        character_name=jwt_token.character_name,
        refresh_recommended=needs_refresh,
    )


@router.post("/token/verify", response_model=TokenVerification)
async def verify_jwt_token(
    request: Request,
    authorization: str | None = Header(None),
    user_agent: str | None = Header(None),
) -> TokenVerification:
    """
    Verify a JWT session token.

    Validates the token signature, expiration, and optionally the client fingerprint.

    The token should be provided in the Authorization header as:
        Authorization: Bearer <token>

    Returns:
        Token verification result with character info if valid
    """
    if not authorization:
        return TokenVerification(valid=False, error="No Authorization header provided")

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return TokenVerification(valid=False, error="Invalid Authorization header format")

    token = parts[1]

    # Generate fingerprint for verification
    client_ip = None
    if request:
        client_ip = request.client.host if request.client else None
    fingerprint = generate_client_fingerprint(user_agent, client_ip)

    # Validate token
    payload, error = validate_jwt(token, verify_fingerprint=fingerprint)

    if error or payload is None:
        return TokenVerification(valid=False, error=error or "Invalid token")

    # Check revocation
    if is_token_revoked(payload.jti):
        return TokenVerification(valid=False, error="Token has been revoked")

    return TokenVerification(
        valid=True,
        character_id=payload.sub,
        character_name=payload.name,
        expires_at=payload.exp,
    )


@router.post("/token/revoke")
async def revoke_jwt_token(
    authorization: str = Header(..., description="Bearer token to revoke"),
) -> dict[str, str]:
    """
    Revoke a JWT session token.

    Adds the token to the revocation list, preventing future use.
    The token remains in the revocation list until it would naturally expire.

    Returns:
        Revocation status
    """
    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=400, detail="Invalid Authorization header format")

    token = parts[1]

    # Validate token to get jti and expiration
    payload, error = validate_jwt(token)

    if error or payload is None:
        raise HTTPException(status_code=400, detail=f"Invalid token: {error}")

    # Revoke the token
    revoke_token(payload.jti, payload.exp)

    logger.info("JWT token revoked", extra={"jti": payload.jti, "character_id": payload.sub})
    return {"status": "revoked", "jti": payload.jti}


@router.get("/tokens/needing-refresh")
async def get_tokens_needing_refresh(
    token_store: TokenStore = Depends(get_token_store),
) -> list[CharacterInfo]:
    """
    List characters whose ESI tokens need proactive refresh.

    This endpoint returns characters whose tokens are approaching expiration
    and should be refreshed proactively to maintain uninterrupted service.

    Useful for background token refresh jobs.

    Returns:
        List of characters needing token refresh
    """
    tokens = await token_store.get_tokens_needing_refresh()

    return [
        CharacterInfo(
            character_id=token["character_id"],
            character_name=token["character_name"],
            scopes=token["scopes"],
            expires_at=token["expires_at"],
            authenticated=True,
            needs_refresh=True,
        )
        for token in tokens
    ]


@router.post("/maintenance/cleanup")
async def run_maintenance_cleanup() -> dict[str, int]:
    """
    Run maintenance cleanup tasks.

    Cleans up expired OAuth states and JWT revocation entries.
    Should be called periodically (e.g., hourly) or on startup.

    Returns:
        Count of cleaned up entries
    """
    expired_states = cleanup_expired_states()
    expired_tokens = cleanup_revoked_tokens()

    return {
        "expired_oauth_states_cleaned": expired_states,
        "expired_revoked_tokens_cleaned": expired_tokens,
    }
