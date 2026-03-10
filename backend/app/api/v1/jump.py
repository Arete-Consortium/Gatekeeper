"""Jump drive API v1 endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query

from ...models.jump import (
    FuelType,
    JumpLegResponse,
    JumpRangeResponse,
    JumpRouteResponse,
    ShipType,
    SystemInRangeResponse,
    SystemsInRangeResponse,
)
from ...services.appraisal import get_jita_prices
from ...services.jump_drive import (
    DEFAULT_FUEL_TYPE,
    FUEL_ISOTOPES,
    CapitalShipType,
    calculate_distance_ly,
    calculate_jump_range,
    find_systems_in_range,
    plan_jump_route,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/range",
    response_model=JumpRangeResponse,
    summary="Calculate jump range",
    description="Calculate jump range for a capital ship based on skills.",
)
def get_jump_range(
    ship: ShipType = Query(
        ShipType.JUMP_FREIGHTER,
        description="Capital ship type",
    ),
    jdc: int = Query(5, ge=0, le=5, description="Jump Drive Calibration level"),
    jfc: int = Query(5, ge=0, le=5, description="Jump Fuel Conservation level"),
) -> JumpRangeResponse:
    """
    Calculate jump range for a capital ship.

    - **ship**: Type of capital ship
    - **jdc**: Jump Drive Calibration skill level (0-5)
    - **jfc**: Jump Fuel Conservation skill level (0-5)
    """
    ship_type = CapitalShipType(ship.value)
    result = calculate_jump_range(ship_type, jdc, jfc)

    return JumpRangeResponse(
        ship_type=ship.value,
        base_range_ly=result.base_range_ly,
        max_range_ly=result.max_range_ly,
        jdc_level=result.jdc_level,
        jfc_level=result.jfc_level,
        fuel_per_ly=result.fuel_per_ly,
    )


@router.get(
    "/distance",
    summary="Calculate distance between systems",
    description="Calculate light year distance between two systems.",
)
def get_distance(
    from_system: str = Query(..., alias="from", description="Origin system"),
    to_system: str = Query(..., alias="to", description="Destination system"),
) -> dict:
    """Calculate light year distance between two systems."""
    try:
        distance = calculate_distance_ly(from_system, to_system)
        return {
            "from_system": from_system,
            "to_system": to_system,
            "distance_ly": round(distance, 2),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/systems-in-range",
    response_model=SystemsInRangeResponse,
    summary="Find systems within jump range",
    description="Find all systems within jump range of origin.",
)
def get_systems_in_range(
    origin: str = Query(..., description="Origin system name"),
    ship: ShipType = Query(
        ShipType.JUMP_FREIGHTER,
        description="Capital ship type",
    ),
    jdc: int = Query(5, ge=0, le=5, description="Jump Drive Calibration level"),
    security: str | None = Query(
        None,
        description="Filter by security: 'lowsec' or 'nullsec'",
    ),
    limit: int = Query(50, ge=1, le=500, description="Max systems to return"),
) -> SystemsInRangeResponse:
    """
    Find all systems within jump range.

    - **origin**: Origin system name
    - **ship**: Capital ship type (determines base range)
    - **jdc**: Jump Drive Calibration level (0-5)
    - **security**: Optional filter - 'lowsec' or 'nullsec'
    - **limit**: Maximum number of systems to return
    """
    ship_type = CapitalShipType(ship.value)
    jump_range = calculate_jump_range(ship_type, jdc, 5)

    try:
        systems = find_systems_in_range(
            origin,
            jump_range.max_range_ly,
            security_filter=security,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Add fuel requirements
    for sys in systems:
        sys.fuel_required = int(sys.distance_ly * jump_range.fuel_per_ly)

    return SystemsInRangeResponse(
        origin=origin,
        max_range_ly=jump_range.max_range_ly,
        count=len(systems[:limit]),
        systems=[
            SystemInRangeResponse(
                name=s.name,
                system_id=s.system_id,
                distance_ly=s.distance_ly,
                security=s.security,
                category=s.category,
                fuel_required=s.fuel_required,
            )
            for s in systems[:limit]
        ],
    )


@router.get(
    "/route",
    response_model=JumpRouteResponse,
    summary="Plan jump route",
    description="Plan a capital ship jump route between two systems.",
)
async def get_jump_route(
    from_system: str = Query(..., alias="from", description="Origin system"),
    to_system: str = Query(..., alias="to", description="Destination system"),
    ship: ShipType = Query(
        ShipType.JUMP_FREIGHTER,
        description="Capital ship type",
    ),
    jdc: int = Query(5, ge=0, le=5, description="Jump Drive Calibration level"),
    jfc: int = Query(5, ge=0, le=5, description="Jump Fuel Conservation level"),
    via: list[str] | None = Query(
        None,
        description="Specific midpoint systems to use",
    ),
    fuel: FuelType | None = Query(
        None,
        description="Fuel isotope type (nitrogen/helium/oxygen/hydrogen). "
        "Defaults to ship category's default.",
    ),
    prefer_stations: bool = Query(
        True,
        description="Prefer systems with NPC stations for waypoints",
    ),
) -> JumpRouteResponse:
    """
    Plan a jump route for a capital ship.

    - **from**: Origin system
    - **to**: Destination system
    - **ship**: Capital ship type
    - **jdc**: Jump Drive Calibration level (0-5)
    - **jfc**: Jump Fuel Conservation level (0-5)
    - **via**: Optional specific midpoint cyno systems
    - **fuel**: Fuel isotope type override
    """
    ship_type = CapitalShipType(ship.value)

    try:
        route = plan_jump_route(
            from_system,
            to_system,
            ship_type,
            jdc,
            jfc,
            midpoints=via,
            fuel_type=fuel.value if fuel else None,
            prefer_stations=prefer_stations,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Fetch Jita fuel price
    fuel_unit_cost = 0.0
    total_fuel_cost = 0.0
    if route.fuel_type_id and route.total_fuel:
        try:
            prices = await get_jita_prices([route.fuel_type_id])
            if route.fuel_type_id in prices:
                _buy, sell = prices[route.fuel_type_id]
                fuel_unit_cost = sell
                total_fuel_cost = sell * route.total_fuel
        except Exception:
            logger.warning(
                "Failed to fetch Jita fuel price for type_id=%d",
                route.fuel_type_id,
            )

    return JumpRouteResponse(
        from_system=route.from_system,
        to_system=route.to_system,
        ship_type=route.ship_type,
        total_jumps=route.total_jumps,
        total_distance_ly=route.total_distance_ly,
        total_fuel=route.total_fuel,
        total_fatigue_minutes=route.total_fatigue_minutes,
        total_travel_time_minutes=route.total_travel_time_minutes,
        legs=[
            JumpLegResponse(
                from_system=leg.from_system,
                to_system=leg.to_system,
                distance_ly=leg.distance_ly,
                fuel_required=leg.fuel_required,
                fatigue_added_minutes=leg.fatigue_added_minutes,
                total_fatigue_minutes=leg.total_fatigue_minutes,
                wait_time_minutes=leg.wait_time_minutes,
            )
            for leg in route.legs
        ],
        fuel_type_id=route.fuel_type_id,
        fuel_type_name=route.fuel_type_name,
        fuel_unit_cost=round(fuel_unit_cost, 2),
        total_fuel_cost=round(total_fuel_cost, 2),
    )


@router.get(
    "/fuel-types",
    summary="List fuel isotope types",
    description="Returns available fuel isotope types and their EVE type IDs.",
)
def get_fuel_types() -> dict:
    """Return available fuel isotope types for frontend dropdown."""
    return {
        "fuel_types": [
            {
                "key": key,
                "type_id": type_id,
                "name": name,
            }
            for key, (type_id, name) in FUEL_ISOTOPES.items()
        ],
        "defaults": {
            ship_type.value: fuel_key for ship_type, fuel_key in DEFAULT_FUEL_TYPE.items()
        },
    }
