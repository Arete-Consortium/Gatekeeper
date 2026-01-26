"""Character API v1 endpoints - authenticated ESI operations.

These endpoints require ESI OAuth2 authentication and interact
with the authenticated character's data via ESI.
"""

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...models.route import RouteResponse
from ...services.data_loader import load_universe
from ...services.routing import compute_route
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


# =============================================================================
# Route from Current Location
# =============================================================================


class RouteFromHereRequest(BaseModel):
    """Request to calculate route from current location."""

    destination: str = Field(..., description="Destination system name")
    profile: str = Field("safer", description="Routing profile: shortest, safer, paranoid")
    avoid: list[str] = Field(default_factory=list, description="Systems to avoid")
    use_bridges: bool = Field(False, description="Use Ansiblex jump bridges")


class RouteFromHereResponse(BaseModel):
    """Response with route from current location."""

    current_system: str
    destination: str
    route: RouteResponse


class SetRouteWaypointsRequest(BaseModel):
    """Request to set route waypoints in-game."""

    systems: list[str] = Field(..., min_length=1, description="System names in order")
    clear_existing: bool = Field(True, description="Clear existing waypoints first")


class SetRouteWaypointsResponse(BaseModel):
    """Response after setting route waypoints."""

    success: bool
    waypoints_set: int
    systems: list[str]


@router.get(
    "/route-from-here",
    response_model=RouteFromHereResponse,
    summary="Calculate route from current location",
    description="Gets character's current location and calculates a route to the destination.",
)
async def get_route_from_current_location(
    destination: str = Query(..., description="Destination system name"),
    profile: str = Query("safer", description="Routing profile"),
    avoid: list[str] | None = Query(None, description="Systems to avoid"),
    bridges: bool = Query(False, description="Use Ansiblex bridges"),
    character: LocationScope | None = None,
) -> RouteFromHereResponse:
    """
    Calculate a route from the character's current location.

    Requires scope: esi-location.read_location.v1

    1. Gets character's current system via ESI
    2. Calculates route to destination
    3. Returns full route details
    """
    if character is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required for location-based routing",
        )

    # Get current location
    location = await get_character_location(character)

    if not location.solar_system_name:
        raise HTTPException(
            status_code=400,
            detail="Could not determine current system name",
        )

    # Validate destination
    universe = load_universe()
    if destination not in universe.systems:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown destination system: {destination}",
        )

    # Calculate route
    avoid_set = set(avoid) if avoid else set()
    route = compute_route(
        location.solar_system_name,
        destination,
        profile=profile,
        avoid=avoid_set,
        use_bridges=bridges,
    )

    if not route:
        raise HTTPException(
            status_code=404,
            detail=f"No route found from {location.solar_system_name} to {destination}",
        )

    return RouteFromHereResponse(
        current_system=location.solar_system_name,
        destination=destination,
        route=route,
    )


@router.post(
    "/set-waypoints",
    response_model=SetRouteWaypointsResponse,
    summary="Set route waypoints in-game",
    description="Sets multiple waypoints in the EVE client for a calculated route.",
)
async def set_route_waypoints(
    request: SetRouteWaypointsRequest,
    character: WaypointScope,
) -> SetRouteWaypointsResponse:
    """
    Set a full route as waypoints in the EVE client.

    Requires scope: esi-ui.write_waypoint.v1

    Sets each system in order as a waypoint. The first waypoint
    clears existing waypoints if clear_existing is True.
    """
    universe = load_universe()

    # Build system ID list
    system_ids: list[int] = []
    for system_name in request.systems:
        found = False
        for sys in universe.systems.values():
            if sys.name == system_name:
                system_ids.append(sys.id)
                found = True
                break
        if not found:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown system: {system_name}",
            )

    # Set waypoints via ESI
    async with httpx.AsyncClient() as client:
        for i, system_id in enumerate(system_ids):
            # First waypoint clears others if requested
            clear = request.clear_existing and i == 0

            response = await client.post(
                "https://esi.evetech.net/latest/ui/autopilot/waypoint/",
                headers={"Authorization": f"Bearer {character.access_token}"},
                params={
                    "datasource": "tranquility",
                    "add_to_beginning": "false",
                    "clear_other_waypoints": str(clear).lower(),
                    "destination_id": system_id,
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
                    detail=f"ESI error setting waypoint {i + 1}: {response.text}",
                )

    return SetRouteWaypointsResponse(
        success=True,
        waypoints_set=len(system_ids),
        systems=request.systems,
    )
