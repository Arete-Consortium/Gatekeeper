"""Fleet tracking API v1 endpoints — real-time fleet member locations.

Provides session-based fleet tracking with share codes. Members join
a fleet session and their ESI locations are polled for map overlay.
Sessions are in-memory with auto-expire after 4 hours.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...services.data_loader import load_universe
from ...services.token_store import get_token_store
from .dependencies import CurrentCharacter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fleet-tracker", tags=["fleet-tracker"])

# =============================================================================
# In-Memory Fleet Sessions
# =============================================================================

FLEET_EXPIRY_HOURS = 4

# fleet_code -> FleetSession data
_fleet_sessions: dict[str, dict[str, Any]] = {}


def _generate_share_code() -> str:
    """Generate a 6-character uppercase alphanumeric share code."""
    return secrets.token_urlsafe(4)[:6].upper()


def _cleanup_expired() -> None:
    """Remove expired fleet sessions."""
    now = datetime.now(UTC)
    expired = [code for code, session in _fleet_sessions.items() if session["expires_at"] < now]
    for code in expired:
        del _fleet_sessions[code]


def _get_session(code: str) -> dict[str, Any]:
    """Get a fleet session by code, raising 404 if not found or expired."""
    _cleanup_expired()
    session = _fleet_sessions.get(code)
    if not session:
        raise HTTPException(status_code=404, detail="Fleet session not found or expired")
    return session


# =============================================================================
# Models
# =============================================================================


class FleetCreateResponse(BaseModel):
    """Response after creating a fleet session."""

    code: str = Field(..., description="6-character share code")
    created_at: str
    expires_at: str
    owner_character_id: int


class FleetJoinResponse(BaseModel):
    """Response after joining a fleet session."""

    code: str
    character_id: int
    character_name: str
    member_count: int


class FleetMember(BaseModel):
    """A fleet member's current location."""

    character_id: int
    character_name: str
    system_id: int | None = None
    system_name: str | None = None
    ship_type_id: int | None = None
    ship_type_name: str | None = None
    online: bool = False
    last_updated: str | None = None


class FleetMembersResponse(BaseModel):
    """Response with all fleet member locations."""

    code: str
    member_count: int
    members: list[FleetMember]


class FleetLeaveResponse(BaseModel):
    """Response after leaving a fleet session."""

    code: str
    character_id: int
    remaining_members: int


# =============================================================================
# ESI Helpers
# =============================================================================


async def _fetch_member_location(
    character_id: int,
    character_name: str,
    access_token: str,
) -> FleetMember:
    """Fetch a single member's location and ship from ESI."""
    member = FleetMember(
        character_id=character_id,
        character_name=character_name,
    )

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Fetch location
        try:
            loc_resp = await client.get(
                f"https://esi.evetech.net/latest/characters/{character_id}/location/",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"datasource": "tranquility"},
            )
            if loc_resp.status_code == 200:
                loc_data = loc_resp.json()
                member.system_id = loc_data.get("solar_system_id")
                member.online = True

                # Enrich system name
                if member.system_id:
                    try:
                        universe = load_universe()
                        for sys in universe.systems.values():
                            if sys.id == member.system_id:
                                member.system_name = sys.name
                                break
                    except Exception:
                        pass
        except Exception as exc:
            logger.debug("Failed to fetch location for %d: %s", character_id, exc)

        # Fetch ship type
        try:
            ship_resp = await client.get(
                f"https://esi.evetech.net/latest/characters/{character_id}/ship/",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"datasource": "tranquility"},
            )
            if ship_resp.status_code == 200:
                ship_data = ship_resp.json()
                member.ship_type_id = ship_data.get("ship_type_id")
                member.ship_type_name = ship_data.get("ship_name")
        except Exception as exc:
            logger.debug("Failed to fetch ship for %d: %s", character_id, exc)

    member.last_updated = datetime.now(UTC).isoformat()
    return member


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/create",
    response_model=FleetCreateResponse,
    summary="Create a fleet tracking session",
    description="Creates a new fleet session with a share code. The creator is automatically added.",
)
async def create_fleet(
    character: CurrentCharacter,
) -> FleetCreateResponse:
    """Create a new fleet tracking session.

    Generates a 6-character share code and adds the creator as first member.
    Sessions expire after 4 hours.
    """
    _cleanup_expired()

    code = _generate_share_code()
    # Ensure uniqueness (extremely unlikely collision)
    while code in _fleet_sessions:
        code = _generate_share_code()

    now = datetime.now(UTC)
    expires = now + timedelta(hours=FLEET_EXPIRY_HOURS)

    _fleet_sessions[code] = {
        "owner_character_id": character.character_id,
        "created_at": now,
        "expires_at": expires,
        "members": {
            character.character_id: {
                "character_id": character.character_id,
                "character_name": character.character_name,
                "joined_at": now,
            }
        },
    }

    logger.info(
        "Fleet session created: %s by %s (%d)",
        code,
        character.character_name,
        character.character_id,
    )

    return FleetCreateResponse(
        code=code,
        created_at=now.isoformat(),
        expires_at=expires.isoformat(),
        owner_character_id=character.character_id,
    )


@router.post(
    "/join/{code}",
    response_model=FleetJoinResponse,
    summary="Join a fleet tracking session",
    description="Join an existing fleet session using a share code.",
)
async def join_fleet(
    code: str,
    character: CurrentCharacter,
) -> FleetJoinResponse:
    """Join a fleet tracking session by share code.

    Adds the authenticated character to the fleet's member list.
    """
    code = code.upper()
    session = _get_session(code)

    session["members"][character.character_id] = {
        "character_id": character.character_id,
        "character_name": character.character_name,
        "joined_at": datetime.now(UTC),
    }

    logger.info(
        "Character %s (%d) joined fleet %s",
        character.character_name,
        character.character_id,
        code,
    )

    return FleetJoinResponse(
        code=code,
        character_id=character.character_id,
        character_name=character.character_name,
        member_count=len(session["members"]),
    )


@router.get(
    "/{code}/members",
    response_model=FleetMembersResponse,
    summary="Get fleet member locations",
    description="Returns current locations for all fleet members by polling ESI.",
)
async def get_fleet_members(
    code: str,
    character: CurrentCharacter,
) -> FleetMembersResponse:
    """Get all fleet member locations.

    Polls ESI for each member's location and ship type using their stored tokens.
    Requires the caller to be authenticated (to prevent unauthorized snooping).
    """
    code = code.upper()
    session = _get_session(code)

    # Verify caller is a member
    if character.character_id not in session["members"]:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of this fleet session",
        )

    token_store = get_token_store()
    members: list[FleetMember] = []

    for member_info in session["members"].values():
        char_id = member_info["character_id"]
        char_name = member_info["character_name"]

        # Get stored ESI token for this member
        stored = await token_store.get_token(char_id)
        if not stored or datetime.now(UTC) >= stored["expires_at"]:
            # Token unavailable or expired — return member with no location
            members.append(
                FleetMember(
                    character_id=char_id,
                    character_name=char_name,
                    online=False,
                    last_updated=datetime.now(UTC).isoformat(),
                )
            )
            continue

        member = await _fetch_member_location(char_id, char_name, stored["access_token"])
        members.append(member)

    return FleetMembersResponse(
        code=code,
        member_count=len(members),
        members=members,
    )


@router.delete(
    "/{code}/leave",
    response_model=FleetLeaveResponse,
    summary="Leave a fleet tracking session",
    description="Removes the authenticated character from the fleet session.",
)
async def leave_fleet(
    code: str,
    character: CurrentCharacter,
) -> FleetLeaveResponse:
    """Leave a fleet tracking session.

    Removes the character from the member list. If the last member leaves,
    the session is cleaned up automatically.
    """
    code = code.upper()
    session = _get_session(code)

    if character.character_id not in session["members"]:
        raise HTTPException(
            status_code=404,
            detail="You are not a member of this fleet session",
        )

    del session["members"][character.character_id]

    remaining = len(session["members"])

    logger.info(
        "Character %s (%d) left fleet %s (%d remaining)",
        character.character_name,
        character.character_id,
        code,
        remaining,
    )

    # Clean up empty sessions
    if remaining == 0:
        del _fleet_sessions[code]
        logger.info("Fleet session %s removed (empty)", code)

    return FleetLeaveResponse(
        code=code,
        character_id=character.character_id,
        remaining_members=remaining,
    )
