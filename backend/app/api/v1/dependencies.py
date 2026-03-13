"""FastAPI Dependencies for Authentication and Authorization.

Provides dependency injection for:
- Current authenticated character (via query param or JWT)
- ESI client with valid token
- Scope verification
- Bearer token extraction
"""

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_db
from ...db.models import User
from ...services.jwt_service import (
    generate_client_fingerprint,
    is_token_revoked,
    validate_jwt,
)
from ...services.token_store import TokenStore, get_token_store


class AuthenticatedCharacter(BaseModel):
    """Authenticated character context."""

    character_id: int
    character_name: str
    access_token: str
    scopes: list[str]
    expires_at: datetime
    auth_method: str = "query"  # "query" or "bearer"
    subscription_tier: str = "free"  # "free" or "pro"


async def _get_subscription_tier(character_id: int, db: AsyncSession) -> str:
    """Look up subscription tier from the users table.

    Checks comp expiration — if comp has expired and there's no Stripe
    subscription, downgrades to free automatically.

    Returns "free" if the user doesn't exist or the DB isn't available.
    """
    try:
        result = await db.execute(
            select(User).where(User.character_id == character_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return "free"

        # Check comp expiration
        if (
            user.subscription_tier == "pro"
            and user.comp_expires_at
            and not user.stripe_subscription_id
            and datetime.now(UTC) >= user.comp_expires_at
        ):
            user.subscription_tier = "free"
            user.comp_expires_at = None
            user.comp_reason = None
            await db.commit()
            return "free"

        return user.subscription_tier or "free"
    except Exception:
        return "free"


async def get_character_from_bearer(
    request: Request,
    authorization: str | None = Header(None),
    user_agent: str | None = Header(None),
    token_store: TokenStore = Depends(get_token_store),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedCharacter | None:
    """
    Extract character from JWT Bearer token or httpOnly session cookie.

    Priority: Authorization header > gk_session cookie.
    Returns None if no valid token is present.
    """
    token = None
    auth_method = "bearer"

    # 1. Try Authorization header first
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    # 2. Fall back to httpOnly cookie
    if not token:
        token = request.cookies.get("gk_session")
        auth_method = "cookie"

    if not token:
        return None

    # Generate fingerprint for validation
    client_ip = None
    if request and request.client:
        client_ip = request.client.host
    fingerprint = generate_client_fingerprint(user_agent, client_ip)

    # Validate JWT
    payload, error = validate_jwt(token, verify_fingerprint=fingerprint)
    if error or payload is None:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Bearer token: {error}",
        )

    # Check revocation
    if is_token_revoked(payload.jti):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked",
        )

    # Get ESI token for the character
    stored = await token_store.get_token(payload.sub)
    if not stored:
        raise HTTPException(
            status_code=401,
            detail="ESI token not found. Please re-authenticate.",
        )

    if datetime.now(UTC) >= stored["expires_at"]:
        raise HTTPException(
            status_code=401,
            detail="ESI token expired. Please refresh via /api/v1/auth/refresh",
        )

    tier = await _get_subscription_tier(stored["character_id"], db)

    return AuthenticatedCharacter(
        character_id=stored["character_id"],
        character_name=stored["character_name"],
        access_token=stored["access_token"],
        scopes=stored["scopes"],
        expires_at=stored["expires_at"],
        auth_method=auth_method,
        subscription_tier=tier,
    )


async def get_current_character(
    request: Request,
    character_id: int | None = Query(None, description="Character ID for authenticated request"),
    authorization: str | None = Header(None),
    user_agent: str | None = Header(None),
    token_store: TokenStore = Depends(get_token_store),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedCharacter:
    """
    Dependency to get the current authenticated character.

    Supports two authentication methods:
    1. JWT Bearer token in Authorization header (preferred)
    2. character_id query parameter (legacy)

    Bearer tokens are validated for signature, expiration, and client fingerprint.

    Validates the token is present and not expired.
    Raises 401 if not authenticated or token expired.

    Usage:
        @router.get("/protected")
        async def protected_route(
            character: AuthenticatedCharacter = Depends(get_current_character)
        ):
            # character.character_id, character.access_token available
    """
    # Try Bearer token first
    if authorization:
        bearer_char = await get_character_from_bearer(
            request=request,
            authorization=authorization,
            user_agent=user_agent,
            token_store=token_store,
            db=db,
        )
        if bearer_char:
            return bearer_char

    # Fall back to query parameter
    if character_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Use Bearer token or character_id query parameter.",
        )

    stored = await token_store.get_token(character_id)

    if not stored:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please login via /api/v1/auth/login",
        )

    if datetime.now(UTC) >= stored["expires_at"]:
        raise HTTPException(
            status_code=401,
            detail="Token expired. Please refresh via /api/v1/auth/refresh",
        )

    tier = await _get_subscription_tier(stored["character_id"], db)

    return AuthenticatedCharacter(
        character_id=stored["character_id"],
        character_name=stored["character_name"],
        access_token=stored["access_token"],
        scopes=stored["scopes"],
        expires_at=stored["expires_at"],
        auth_method="query",
        subscription_tier=tier,
    )


def require_scopes(
    *required_scopes: str,
) -> Callable[..., Coroutine[Any, Any, AuthenticatedCharacter]]:
    """
    Dependency factory to require specific ESI scopes.

    Usage:
        @router.get("/location")
        async def get_location(
            character: AuthenticatedCharacter = Depends(
                require_scopes("esi-location.read_location.v1")
            )
        ):
            # Character has required scope
    """

    async def verify_scopes(
        character: AuthenticatedCharacter = Depends(get_current_character),
    ) -> AuthenticatedCharacter:
        missing = [s for s in required_scopes if s not in character.scopes]
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scopes: {', '.join(missing)}",
            )
        return character

    return verify_scopes


async def require_pro(
    character: AuthenticatedCharacter = Depends(get_current_character),
) -> AuthenticatedCharacter:
    """Dependency that requires Pro subscription. Returns 402 if free tier."""
    if character.subscription_tier != "pro":
        raise HTTPException(
            status_code=402,
            detail="Pro subscription required. Upgrade at /pricing",
        )
    return character


async def get_optional_character(
    request: Request,
    character_id: int | None = Query(None, description="Optional character ID"),
    authorization: str | None = Header(None),
    user_agent: str | None = Header(None),
    token_store: TokenStore = Depends(get_token_store),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedCharacter | None:
    """
    Dependency to optionally get authenticated character.

    Returns None if no authentication provided or token invalid.
    Does not raise exceptions - useful for routes that work
    differently when authenticated vs anonymous.

    Supports both Bearer token and query parameter authentication.

    Usage:
        @router.get("/route")
        async def get_route(
            character: AuthenticatedCharacter | None = Depends(get_optional_character)
        ):
            if character:
                # Use character-specific data
            else:
                # Anonymous access
    """
    # Try Bearer token or cookie (don't raise on error, just return None)
    if authorization or request.cookies.get("gk_session"):
        try:
            bearer_char = await get_character_from_bearer(
                request=request,
                authorization=authorization,
                user_agent=user_agent,
                token_store=token_store,
                db=db,
            )
            if bearer_char:
                return bearer_char
        except HTTPException:
            pass  # Silently fail for optional auth

    # Fall back to query parameter
    if character_id is None:
        return None

    stored = await token_store.get_token(character_id)
    if not stored:
        return None

    if datetime.now(UTC) >= stored["expires_at"]:
        return None

    tier = await _get_subscription_tier(stored["character_id"], db)

    return AuthenticatedCharacter(
        character_id=stored["character_id"],
        character_name=stored["character_name"],
        access_token=stored["access_token"],
        scopes=stored["scopes"],
        expires_at=stored["expires_at"],
        auth_method="query",
        subscription_tier=tier,
    )


# =============================================================================
# ESI Client Dependencies
# =============================================================================


async def get_authenticated_esi_client(
    character: AuthenticatedCharacter = Depends(get_current_character),
):
    """
    Get an ESI client configured with the character's token.

    Usage:
        @router.get("/location")
        async def get_location(
            esi = Depends(get_authenticated_esi_client)
        ):
            async with esi as client:
                data = await client.get("/characters/{}/location/".format(
                    character.character_id
                ), authenticated=True)
    """
    from backend.starmap.esi.client import ESIClient, TokenData

    client = ESIClient()
    client.set_token(
        TokenData(
            access_token=character.access_token,
            refresh_token="",  # Not needed for requests
            expires_at=character.expires_at,
            character_id=character.character_id,
            character_name=character.character_name,
            scopes=character.scopes,
        )
    )
    return client


# =============================================================================
# Type Aliases for cleaner route signatures
# =============================================================================

# Use these in route parameters for cleaner code
CurrentCharacter = Annotated[AuthenticatedCharacter, Depends(get_current_character)]
OptionalCharacter = Annotated[AuthenticatedCharacter | None, Depends(get_optional_character)]
ProCharacter = Annotated[AuthenticatedCharacter, Depends(require_pro)]

# Scope-specific dependencies
LocationScope = Annotated[
    AuthenticatedCharacter, Depends(require_scopes("esi-location.read_location.v1"))
]
WaypointScope = Annotated[
    AuthenticatedCharacter, Depends(require_scopes("esi-ui.write_waypoint.v1"))
]
AssetsScope = Annotated[
    AuthenticatedCharacter, Depends(require_scopes("esi-assets.read_assets.v1"))
]
