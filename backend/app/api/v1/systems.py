"""Systems API v1 endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...models.risk import RiskReport, ShipProfile, SHIP_PROFILES
from ...models.system import SystemSummary
from ...services.data_loader import get_neighbors, load_universe
from ...services.risk_engine import compute_risk_async

router = APIRouter()


class ShipProfileResponse(BaseModel):
    """Response for ship profile."""

    name: str
    description: str
    highsec_multiplier: float
    lowsec_multiplier: float
    nullsec_multiplier: float
    kills_multiplier: float
    pods_multiplier: float


class ShipProfileListResponse(BaseModel):
    """Response for listing ship profiles."""

    profiles: list[ShipProfileResponse]


@router.get(
    "/",
    response_model=list[SystemSummary],
    summary="List all systems",
    description="Returns a list of all systems in the EVE universe with basic information.",
)
def list_systems() -> list[SystemSummary]:
    """Get all systems in the universe."""
    universe = load_universe()
    return [
        SystemSummary(
            name=sys.name,
            security=sys.security,
            category=sys.category,
            region_id=sys.region_id,
            region_name=sys.region_name,
            constellation_id=sys.constellation_id,
            constellation_name=sys.constellation_name,
        )
        for sys in universe.systems.values()
    ]


@router.get(
    "/{system_name}",
    response_model=SystemSummary,
    summary="Get system details",
    description="Returns details for a specific system.",
)
def get_system(system_name: str) -> SystemSummary:
    """Get details for a specific system."""
    universe = load_universe()
    if system_name not in universe.systems:
        raise HTTPException(status_code=404, detail=f"System '{system_name}' not found")
    sys = universe.systems[system_name]
    return SystemSummary(
        name=sys.name,
        security=sys.security,
        category=sys.category,
        region_id=sys.region_id,
        region_name=sys.region_name,
        constellation_id=sys.constellation_id,
        constellation_name=sys.constellation_name,
    )


@router.get(
    "/{system_name}/risk",
    response_model=RiskReport,
    summary="Get system risk report",
    description="Returns a risk assessment for the specified system based on recent activity.",
)
async def get_system_risk(
    system_name: str,
    live: bool = Query(True, description="Fetch fresh kill data from zKillboard"),
    ship_profile: str | None = Query(
        None,
        description="Ship profile for adjusted risk (hauler, frigate, cruiser, battleship, mining, capital, cloaky)",
    ),
) -> RiskReport:
    """
    Get risk assessment for a system.

    Args:
        system_name: Name of the system
        live: If true, fetch fresh kill data from zKillboard (default: true)
        ship_profile: Optional ship profile for adjusted risk calculation
    """
    universe = load_universe()
    if system_name not in universe.systems:
        raise HTTPException(status_code=404, detail=f"System '{system_name}' not found")

    if ship_profile and ship_profile not in SHIP_PROFILES:
        available = ", ".join(SHIP_PROFILES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown ship profile: '{ship_profile}'. Available: {available}",
        )

    return await compute_risk_async(system_name, fetch_live=live, ship_profile_name=ship_profile)


@router.get(
    "/{system_name}/neighbors",
    response_model=list[str],
    summary="Get neighboring systems",
    description="Returns a list of systems directly connected via stargates.",
)
def get_system_neighbors(system_name: str) -> list[str]:
    """Get systems connected to the specified system."""
    universe = load_universe()
    if system_name not in universe.systems:
        raise HTTPException(status_code=404, detail=f"System '{system_name}' not found")

    neighbors = get_neighbors(system_name)
    names: set[str] = set()
    for gate in neighbors:
        if gate.from_system == system_name:
            names.add(gate.to_system)
        else:
            names.add(gate.from_system)
    return sorted(names)


@router.get(
    "/profiles/ships",
    response_model=ShipProfileListResponse,
    summary="List ship profiles",
    description="Returns available ship profiles for risk assessment.",
)
def list_ship_profiles() -> ShipProfileListResponse:
    """List all available ship profiles."""
    profiles = [
        ShipProfileResponse(
            name=p.name,
            description=p.description,
            highsec_multiplier=p.highsec_multiplier,
            lowsec_multiplier=p.lowsec_multiplier,
            nullsec_multiplier=p.nullsec_multiplier,
            kills_multiplier=p.kills_multiplier,
            pods_multiplier=p.pods_multiplier,
        )
        for p in SHIP_PROFILES.values()
    ]
    return ShipProfileListResponse(profiles=profiles)
