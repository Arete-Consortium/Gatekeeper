"""ESI OAuth2 Authentication Routes.

Implements EVE SSO authentication flow:
1. /auth/login - Redirects to EVE SSO
2. /auth/callback - Handles OAuth callback
3. /auth/refresh - Refreshes expired tokens
4. /auth/me - Returns authenticated character info
5. /auth/logout - Clears session
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from ...core.config import settings
from ...services.token_store import TokenStore, get_token_store

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


# =============================================================================
# OAuth State Management
# =============================================================================

# In-memory state storage (use Redis in production)
_oauth_states: dict[str, datetime] = {}


def generate_state() -> str:
    """Generate a secure random state parameter."""
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = datetime.now(UTC) + timedelta(minutes=10)
    return state


def validate_state(state: str) -> bool:
    """Validate and consume OAuth state."""
    if state not in _oauth_states:
        return False
    expires = _oauth_states.pop(state)
    return datetime.now(UTC) < expires


def cleanup_expired_states() -> None:
    """Remove expired state tokens."""
    now = datetime.now(UTC)
    expired = [s for s, exp in _oauth_states.items() if now >= exp]
    for s in expired:
        _oauth_states.pop(s, None)


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
) -> CharacterInfo:
    """
    Handle OAuth callback from EVE SSO.

    Exchanges the authorization code for access and refresh tokens,
    then stores them for the authenticated character.
    """
    # Validate state
    if not validate_state(state):
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
    """
    stored = await token_store.get_token(character_id)

    if not stored:
        return AuthStatus(authenticated=False)

    # Check if token is expired
    if datetime.now(UTC) >= stored["expires_at"]:
        return AuthStatus(
            authenticated=False,
            character=CharacterInfo(
                character_id=character_id,
                character_name=stored["character_name"],
                scopes=stored["scopes"],
                expires_at=stored["expires_at"],
                authenticated=False,
            ),
        )

    return AuthStatus(
        authenticated=True,
        character=CharacterInfo(
            character_id=character_id,
            character_name=stored["character_name"],
            scopes=stored["scopes"],
            expires_at=stored["expires_at"],
        ),
    )


@router.get("/characters")
async def list_characters(
    token_store: TokenStore = Depends(get_token_store),
) -> list[CharacterInfo]:
    """
    List all authenticated characters.

    Returns a list of all characters that have valid stored tokens.
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
    return {"status": "cleared", "tokens_removed": str(count)}
