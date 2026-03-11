"""Multi-character management API endpoints.

Provides endpoints for:
- Listing all authenticated characters
- Linking / unlinking alt characters
- Switching active character
- Managing per-character preferences
- Bulk operations across characters
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from ...models.character_preferences import (
    ActiveCharacterResponse,
    AlertPreferences,
    CharacterListResponse,
    CharacterPreferences,
    CharacterPreferencesUpdate,
    CharacterSwitchRequest,
    RoutingPreferences,
    UIPreferences,
)
from ...services.character_preferences import (
    ActiveCharacterManager,
    CharacterPreferencesStore,
    get_active_manager,
    get_preferences_store,
)
from ...services.token_store import TokenStore, get_token_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/characters", tags=["characters"])


# =============================================================================
# Character Listing
# =============================================================================


@router.get(
    "/",
    response_model=CharacterListResponse,
    summary="List all authenticated characters",
    description="Returns all characters that have valid stored tokens with their preferences.",
)
async def list_characters(
    x_session_id: str | None = Header(None, description="Session ID for active character tracking"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
    active_manager: ActiveCharacterManager = Depends(get_active_manager),
) -> CharacterListResponse:
    """
    List all authenticated characters with their current status.

    Returns character info, authentication status, and preferences for each
    character that has a stored token.
    """
    from datetime import UTC, datetime

    characters = await token_store.list_characters()
    now = datetime.now(UTC)

    result = []
    for char in characters:
        is_authenticated = now < char["expires_at"]

        # Get preferences if they exist
        prefs = await prefs_store.get_preferences(char["character_id"])

        result.append(
            ActiveCharacterResponse(
                character_id=char["character_id"],
                character_name=char["character_name"],
                is_active=is_authenticated,
                preferences=prefs,
            )
        )

    # Get active character for this session
    active_id = None
    if x_session_id:
        active_id = active_manager.get_active(x_session_id)

    return CharacterListResponse(
        characters=result,
        active_character_id=active_id,
        total_count=len(result),
    )


class LinkCharacterResponse(BaseModel):
    """Response after linking a new character."""

    auth_url: str
    state: str
    message: str = "Redirect user to auth_url to complete SSO for the alt character."


class UnlinkCharacterResponse(BaseModel):
    """Response after unlinking a character."""

    status: str
    character_id: int
    character_name: str | None = None


@router.post(
    "/link",
    response_model=LinkCharacterResponse,
    summary="Link an additional character",
    description="Starts a new SSO flow to link an alt character. "
    "The callback will store the token, making the character available.",
)
async def link_character() -> LinkCharacterResponse:
    """
    Initiate SSO flow to link an additional character.

    Returns an authorization URL. The user should be redirected to this URL.
    On successful SSO callback, the new character's token is stored and
    the character appears in the /characters/ listing.
    """
    from .auth import login

    login_response = await login(redirect_uri=None, scopes=None)
    return LinkCharacterResponse(
        auth_url=login_response.auth_url,
        state=login_response.state,
    )


@router.delete(
    "/{character_id}",
    response_model=UnlinkCharacterResponse,
    summary="Unlink a character",
    description="Remove a character's stored token and preferences, unlinking it from the account.",
)
async def unlink_character(
    character_id: int,
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> UnlinkCharacterResponse:
    """
    Unlink a character by removing its token and preferences.

    The character will no longer appear in the listing and cannot be
    switched to until re-authenticated.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    character_name = token["character_name"]
    await token_store.remove_token(character_id)
    await prefs_store.delete_preferences(character_id)

    logger.info(
        "Character unlinked",
        extra={"character_id": character_id, "character_name": character_name},
    )

    return UnlinkCharacterResponse(
        status="unlinked",
        character_id=character_id,
        character_name=character_name,
    )


@router.post(
    "/{character_id}/active",
    response_model=ActiveCharacterResponse,
    summary="Set active character",
    description="Set a character as the active character for this session.",
)
async def set_active_character(
    character_id: int,
    x_session_id: str = Header(..., description="Session ID for active character tracking"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
    active_manager: ActiveCharacterManager = Depends(get_active_manager),
) -> ActiveCharacterResponse:
    """
    Set a character as active for the current session.

    Equivalent to /switch but using the character_id in the path.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}. Please authenticate first.",
        )

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    if now >= token["expires_at"]:
        raise HTTPException(
            status_code=401,
            detail="Token expired. Please refresh via /auth/refresh first.",
        )

    active_manager.set_active(x_session_id, character_id)
    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])

    logger.info(
        "Active character set",
        extra={"session_id": x_session_id, "character_id": character_id},
    )

    return ActiveCharacterResponse(
        character_id=token["character_id"],
        character_name=token["character_name"],
        is_active=True,
        preferences=prefs,
    )


@router.get(
    "/active",
    response_model=ActiveCharacterResponse | None,
    summary="Get active character",
    description="Returns the currently active character for this session.",
)
async def get_active_character(
    x_session_id: str = Header(..., description="Session ID for active character tracking"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
    active_manager: ActiveCharacterManager = Depends(get_active_manager),
) -> ActiveCharacterResponse | None:
    """
    Get the currently active character for this session.

    If no character is set as active, returns null.
    """
    active_id = active_manager.get_active(x_session_id)
    if not active_id:
        return None

    token = await token_store.get_token(active_id)
    if not token:
        # Token was removed, clear active
        active_manager.clear_active(x_session_id)
        return None

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    prefs = await prefs_store.get_preferences(active_id)

    return ActiveCharacterResponse(
        character_id=token["character_id"],
        character_name=token["character_name"],
        is_active=now < token["expires_at"],
        preferences=prefs,
    )


@router.post(
    "/switch",
    response_model=ActiveCharacterResponse,
    summary="Switch active character",
    description="Set a different character as the active character for this session.",
)
async def switch_character(
    request: CharacterSwitchRequest,
    x_session_id: str = Header(..., description="Session ID for active character tracking"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
    active_manager: ActiveCharacterManager = Depends(get_active_manager),
) -> ActiveCharacterResponse:
    """
    Switch to a different character.

    The character must have a valid stored token. Creates default preferences
    if none exist for the character.
    """
    token = await token_store.get_token(request.character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {request.character_id}. Please authenticate first.",
        )

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    if now >= token["expires_at"]:
        raise HTTPException(
            status_code=401,
            detail="Token expired. Please refresh via /auth/refresh first.",
        )

    # Set as active
    active_manager.set_active(x_session_id, request.character_id)

    # Get or create preferences
    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])

    logger.info(
        "Character switched",
        extra={
            "session_id": x_session_id,
            "character_id": token["character_id"],
            "character_name": token["character_name"],
        },
    )

    return ActiveCharacterResponse(
        character_id=token["character_id"],
        character_name=token["character_name"],
        is_active=True,
        preferences=prefs,
    )


# =============================================================================
# Preferences Management
# =============================================================================


@router.get(
    "/{character_id}/preferences",
    response_model=CharacterPreferences,
    summary="Get character preferences",
    description="Returns the preferences for a specific character.",
)
async def get_character_preferences(
    character_id: int,
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Get preferences for a character.

    Creates default preferences if none exist.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])
    return prefs


@router.patch(
    "/{character_id}/preferences",
    response_model=CharacterPreferences,
    summary="Update character preferences",
    description="Update preferences for a specific character. Only provided fields are updated.",
)
async def update_character_preferences(
    character_id: int,
    update: CharacterPreferencesUpdate,
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Update preferences for a character.

    Only fields provided in the request body are updated.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    # Ensure preferences exist
    await prefs_store.get_or_create(token["character_id"], token["character_name"])

    # Apply update
    prefs = await prefs_store.update_preferences(character_id, update)
    if not prefs:
        raise HTTPException(
            status_code=500,
            detail="Failed to update preferences",
        )

    logger.info(
        "Preferences updated",
        extra={
            "character_id": character_id,
            "character_name": token["character_name"],
        },
    )

    return prefs


@router.put(
    "/{character_id}/preferences/routing",
    response_model=CharacterPreferences,
    summary="Set routing preferences",
    description="Replace the routing preferences for a character.",
)
async def set_routing_preferences(
    character_id: int,
    routing: RoutingPreferences,
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Set routing preferences for a character.

    Replaces all routing preferences with the provided values.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])
    prefs.routing = routing
    await prefs_store.save_preferences(prefs)

    return prefs


@router.put(
    "/{character_id}/preferences/alerts",
    response_model=CharacterPreferences,
    summary="Set alert preferences",
    description="Replace the alert preferences for a character.",
)
async def set_alert_preferences(
    character_id: int,
    alerts: AlertPreferences,
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Set alert preferences for a character.

    Replaces all alert preferences with the provided values.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])
    prefs.alerts = alerts
    await prefs_store.save_preferences(prefs)

    return prefs


@router.put(
    "/{character_id}/preferences/ui",
    response_model=CharacterPreferences,
    summary="Set UI preferences",
    description="Replace the UI preferences for a character.",
)
async def set_ui_preferences(
    character_id: int,
    ui: UIPreferences,
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Set UI preferences for a character.

    Replaces all UI preferences with the provided values.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])
    prefs.ui = ui
    await prefs_store.save_preferences(prefs)

    return prefs


@router.delete(
    "/{character_id}/preferences",
    summary="Delete character preferences",
    description="Delete all preferences for a character, resetting to defaults.",
)
async def delete_character_preferences(
    character_id: int,
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> dict[str, str]:
    """
    Delete preferences for a character.

    Preferences will be recreated with defaults on next access.
    """
    deleted = await prefs_store.delete_preferences(character_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No preferences found for character {character_id}",
        )

    return {"status": "deleted", "character_id": str(character_id)}


# =============================================================================
# Avoid List Management
# =============================================================================


@router.post(
    "/{character_id}/avoid",
    response_model=CharacterPreferences,
    summary="Add system to avoid list",
    description="Add a system to the character's permanent avoid list.",
)
async def add_avoid_system(
    character_id: int,
    system: str = Query(..., description="System name to avoid"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Add a system to the avoid list.

    The system will be automatically avoided in all route calculations.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])

    if system not in prefs.routing.avoid_systems:
        prefs.routing.avoid_systems.append(system)
        await prefs_store.save_preferences(prefs)
        logger.info(
            "System added to avoid list",
            extra={"character_id": character_id, "system": system},
        )

    return prefs


@router.delete(
    "/{character_id}/avoid",
    response_model=CharacterPreferences,
    summary="Remove system from avoid list",
    description="Remove a system from the character's avoid list.",
)
async def remove_avoid_system(
    character_id: int,
    system: str = Query(..., description="System name to remove from avoid list"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Remove a system from the avoid list.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])

    if system in prefs.routing.avoid_systems:
        prefs.routing.avoid_systems.remove(system)
        await prefs_store.save_preferences(prefs)
        logger.info(
            "System removed from avoid list",
            extra={"character_id": character_id, "system": system},
        )

    return prefs


# =============================================================================
# Watch List Management
# =============================================================================


@router.post(
    "/{character_id}/watch/system",
    response_model=CharacterPreferences,
    summary="Add system to watch list",
    description="Add a system to the character's watch list for kill alerts.",
)
async def add_watch_system(
    character_id: int,
    system: str = Query(..., description="System name to watch"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Add a system to the watch list for kill alerts.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])

    if system not in prefs.alerts.watch_systems:
        prefs.alerts.watch_systems.append(system)
        await prefs_store.save_preferences(prefs)

    return prefs


@router.delete(
    "/{character_id}/watch/system",
    response_model=CharacterPreferences,
    summary="Remove system from watch list",
    description="Remove a system from the character's watch list.",
)
async def remove_watch_system(
    character_id: int,
    system: str = Query(..., description="System name to remove from watch list"),
    token_store: TokenStore = Depends(get_token_store),
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
) -> CharacterPreferences:
    """
    Remove a system from the watch list.
    """
    token = await token_store.get_token(character_id)
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"No token found for character {character_id}",
        )

    prefs = await prefs_store.get_or_create(token["character_id"], token["character_name"])

    if system in prefs.alerts.watch_systems:
        prefs.alerts.watch_systems.remove(system)
        await prefs_store.save_preferences(prefs)

    return prefs


# =============================================================================
# Statistics
# =============================================================================


@router.get(
    "/stats",
    summary="Get character management statistics",
    description="Returns statistics about character management.",
)
async def get_character_stats(
    prefs_store: CharacterPreferencesStore = Depends(get_preferences_store),
    active_manager: ActiveCharacterManager = Depends(get_active_manager),
    token_store: TokenStore = Depends(get_token_store),
) -> dict[str, Any]:
    """
    Get statistics about character management.
    """
    all_prefs = await prefs_store.list_all()
    all_chars = await token_store.list_characters()
    session_stats = active_manager.get_stats()

    return {
        "total_authenticated_characters": len(all_chars),
        "characters_with_preferences": len(all_prefs),
        "active_sessions": session_stats["active_sessions"],
        "unique_active_characters": session_stats["unique_characters"],
    }
