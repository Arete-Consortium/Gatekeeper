"""Systems API v1 endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...core.pagination import PaginationParams, get_pagination_params, paginate
from ...models.risk import SHIP_PROFILES, RiskReport
from ...models.system import SystemListResponse, SystemSummary
from ...services.cache import get_cache
from ...services.data_loader import get_neighbors, load_universe
from ...services.risk_engine import compute_risk_async
from ..metrics import record_risk_cache_hit, record_risk_cache_miss

logger = logging.getLogger(__name__)

# Risk cache TTL (2 minutes - risk data can change frequently from zKill)
RISK_CACHE_TTL = 120

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
    response_model=SystemListResponse,
    summary="List all systems",
    description="Returns a paginated list of all systems in the EVE universe with basic information.",
)
def list_systems(
    pagination: PaginationParams = Depends(get_pagination_params),
    category: str | None = Query(
        None, description="Filter by category (highsec, lowsec, nullsec, wh)"
    ),
    region_name: str | None = Query(None, description="Filter by region name"),
    search: str | None = Query(
        None, min_length=2, description="Search by system name (partial match)"
    ),
) -> SystemListResponse:
    """Get all systems in the universe with pagination.

    Supports filtering by category, region, and search by name.
    """
    universe = load_universe()

    # Build list and apply filters
    all_systems = []
    for sys in universe.systems.values():
        # Apply category filter
        if category and sys.category != category:
            continue
        # Apply region filter
        if region_name and sys.region_name.lower() != region_name.lower():
            continue
        # Apply search filter
        if search and search.lower() not in sys.name.lower():
            continue

        all_systems.append(
            SystemSummary(
                name=sys.name,
                security=sys.security,
                category=sys.category,
                region_id=sys.region_id,
                region_name=sys.region_name,
                constellation_id=sys.constellation_id,
                constellation_name=sys.constellation_name,
            )
        )

    # Sort by name for consistent ordering
    all_systems.sort(key=lambda s: s.name)

    # Apply pagination
    items, meta = paginate(all_systems, pagination.page, pagination.page_size)

    return SystemListResponse(items=items, pagination=meta)


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


def _build_risk_cache_key(system_name: str, live: bool, ship_profile: str | None) -> str:
    """Build a cache key for risk calculations."""
    profile_part = ship_profile or "default"
    return f"risk:{system_name}:{live}:{profile_part}"


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

    # Check cache before computing
    cache_key = _build_risk_cache_key(system_name, live, ship_profile)
    cache = await get_cache()
    cached_data = await cache.get_json(cache_key)
    if cached_data:
        record_risk_cache_hit()
        logger.debug("Risk cache hit", extra={"key": cache_key, "system": system_name})
        return RiskReport(**cached_data)

    record_risk_cache_miss()
    logger.debug("Risk cache miss", extra={"key": cache_key, "system": system_name})

    risk = await compute_risk_async(system_name, fetch_live=live, ship_profile_name=ship_profile)

    # Cache the result
    await cache.set_json(cache_key, risk.model_dump(mode="json"), ttl=RISK_CACHE_TTL)

    return risk


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
