"""Character API v1 endpoints - authenticated ESI operations.

These endpoints require ESI OAuth2 authentication and interact
with the authenticated character's data via ESI.
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...services.data_loader import load_universe
from .dependencies import LocationScope, WaypointScope

router = APIRouter(prefix="/character", tags=["character"])


# =============================================================================
# Response Models
# =============================================================================


class CharacterLocation(BaseModel):
    """Character's current location."""

    solar_system_id: int
    solar_system_name: str | None = None
    security: float | None = None
    region_name: str | None = None
    station_id: int | None = None
    structure_id: int | None = None


class CharacterOnlineStatus(BaseModel):
    """Character's online status."""

    online: bool
    last_login: str | None = None
    last_logout: str | None = None
    logins: int | None = None


class WaypointRequest(BaseModel):
    """Request to set an autopilot waypoint."""

    destination_id: int
    add_to_beginning: bool = False
    clear_other_waypoints: bool = False


class WaypointResponse(BaseModel):
    """Response after setting waypoint."""

    success: bool
    destination_id: int
    destination_name: str | None = None


class CharacterShip(BaseModel):
    """Character's current ship."""

    ship_type_id: int
    ship_item_id: int
    ship_name: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/location",
    response_model=CharacterLocation,
    summary="Get character location",
    description="Returns the authenticated character's current solar system location.",
)
async def get_character_location(
    character: LocationScope,
) -> CharacterLocation:
    """
    Get the authenticated character's current location.

    Requires scope: esi-location.read_location.v1
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://esi.evetech.net/latest/characters/{character.character_id}/location/",
            headers={"Authorization": f"Bearer {character.access_token}"},
            params={"datasource": "tranquility"},
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Token expired or invalid. Please refresh.",
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ESI error: {response.text}",
            )

        data = response.json()

    # Enrich with system name if available
    solar_system_id = data["solar_system_id"]
    solar_system_name = None
    security = None
    region_name = None

    try:
        universe = load_universe()
        # Find system by ID
        for sys in universe.systems.values():
            if sys.id == solar_system_id:
                solar_system_name = sys.name
                security = sys.security
                region_name = sys.region_name
                break
    except Exception:
        pass  # Enrichment is optional

    return CharacterLocation(
        solar_system_id=solar_system_id,
        solar_system_name=solar_system_name,
        security=security,
        region_name=region_name,
        station_id=data.get("station_id"),
        structure_id=data.get("structure_id"),
    )


@router.get(
    "/online",
    response_model=CharacterOnlineStatus,
    summary="Get online status",
    description="Returns whether the character is currently online.",
)
async def get_character_online(
    character: LocationScope,
) -> CharacterOnlineStatus:
    """
    Get the authenticated character's online status.

    Requires scope: esi-location.read_online.v1
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://esi.evetech.net/latest/characters/{character.character_id}/online/",
            headers={"Authorization": f"Bearer {character.access_token}"},
            params={"datasource": "tranquility"},
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Token expired or invalid. Please refresh.",
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ESI error: {response.text}",
            )

        data = response.json()

    return CharacterOnlineStatus(
        online=data.get("online", False),
        last_login=data.get("last_login"),
        last_logout=data.get("last_logout"),
        logins=data.get("logins"),
    )


@router.get(
    "/ship",
    response_model=CharacterShip,
    summary="Get current ship",
    description="Returns the character's currently active ship.",
)
async def get_character_ship(
    character: LocationScope,
) -> CharacterShip:
    """
    Get the authenticated character's current ship.

    Requires scope: esi-location.read_ship_type.v1
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://esi.evetech.net/latest/characters/{character.character_id}/ship/",
            headers={"Authorization": f"Bearer {character.access_token}"},
            params={"datasource": "tranquility"},
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Token expired or invalid. Please refresh.",
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ESI error: {response.text}",
            )

        data = response.json()

    return CharacterShip(
        ship_type_id=data["ship_type_id"],
        ship_item_id=data["ship_item_id"],
        ship_name=data.get("ship_name"),
    )


@router.post(
    "/waypoint",
    response_model=WaypointResponse,
    summary="Set autopilot waypoint",
    description="Sets an in-game autopilot waypoint for the character.",
)
async def set_waypoint(
    waypoint: WaypointRequest,
    character: WaypointScope,
) -> WaypointResponse:
    """
    Set an autopilot waypoint in the EVE client.

    Requires scope: esi-ui.write_waypoint.v1

    The character must be online for this to work.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://esi.evetech.net/latest/ui/autopilot/waypoint/",
            headers={"Authorization": f"Bearer {character.access_token}"},
            params={
                "datasource": "tranquility",
                "add_to_beginning": str(waypoint.add_to_beginning).lower(),
                "clear_other_waypoints": str(waypoint.clear_other_waypoints).lower(),
                "destination_id": waypoint.destination_id,
            },
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Token expired or invalid. Please refresh.",
            )
        if response.status_code not in (200, 204):
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ESI error: {response.text}",
            )

    # Try to get destination name
    destination_name = None
    try:
        universe = load_universe()
        for sys in universe.systems.values():
            if sys.id == waypoint.destination_id:
                destination_name = sys.name
                break
    except Exception:
        pass

    return WaypointResponse(
        success=True,
        destination_id=waypoint.destination_id,
        destination_name=destination_name,
    )


@router.post(
    "/route",
    response_model=WaypointResponse,
    summary="Set route destination",
    description="Sets a full route by clearing existing waypoints and setting the destination.",
)
async def set_route_destination(
    destination_id: int,
    character: WaypointScope,
) -> WaypointResponse:
    """
    Set a route to a destination (clears existing waypoints).

    Requires scope: esi-ui.write_waypoint.v1
    """
    return await set_waypoint(
        WaypointRequest(
            destination_id=destination_id,
            add_to_beginning=False,
            clear_other_waypoints=True,
        ),
        character,
    )
