"""FastAPI Dependencies for Authentication and Authorization.

Provides dependency injection for:
- Current authenticated character
- ESI client with valid token
- Scope verification
"""

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel

from ...services.token_store import TokenStore, get_token_store


class AuthenticatedCharacter(BaseModel):
    """Authenticated character context."""

    character_id: int
    character_name: str
    access_token: str
    scopes: list[str]
    expires_at: datetime


async def get_current_character(
    character_id: int = Query(..., description="Character ID for authenticated request"),
    token_store: TokenStore = Depends(get_token_store),
) -> AuthenticatedCharacter:
    """
    Dependency to get the current authenticated character.

    Validates the token is present and not expired.
    Raises 401 if not authenticated or token expired.

    Usage:
        @router.get("/protected")
        async def protected_route(
            character: AuthenticatedCharacter = Depends(get_current_character)
        ):
            # character.character_id, character.access_token available
    """
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

    return AuthenticatedCharacter(
        character_id=stored["character_id"],
        character_name=stored["character_name"],
        access_token=stored["access_token"],
        scopes=stored["scopes"],
        expires_at=stored["expires_at"],
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


async def get_optional_character(
    character_id: int | None = Query(None, description="Optional character ID"),
    token_store: TokenStore = Depends(get_token_store),
) -> AuthenticatedCharacter | None:
    """
    Dependency to optionally get authenticated character.

    Returns None if no character_id provided or token invalid.
    Does not raise exceptions - useful for routes that work
    differently when authenticated vs anonymous.

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
    if character_id is None:
        return None

    stored = await token_store.get_token(character_id)
    if not stored:
        return None

    if datetime.now(UTC) >= stored["expires_at"]:
        return None

    return AuthenticatedCharacter(
        character_id=stored["character_id"],
        character_name=stored["character_name"],
        access_token=stored["access_token"],
        scopes=stored["scopes"],
        expires_at=stored["expires_at"],
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
