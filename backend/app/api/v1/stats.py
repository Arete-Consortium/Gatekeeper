"""Kill statistics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .dependencies import AuthenticatedCharacter, require_pro

from ...models.risk import ZKillStats
from ...services.data_loader import load_universe
from ...services.zkill_stats import (
    fetch_bulk_system_stats,
    fetch_system_kills,
    get_zkill_preloader,
)

router = APIRouter()


class SystemStatsResponse(BaseModel):
    """Response for single system stats."""

    system_id: int
    system_name: str
    hours: int = Field(description="Lookback period in hours")
    stats: ZKillStats


class BulkStatsRequest(BaseModel):
    """Request for bulk system stats."""

    systems: list[str] = Field(..., min_length=1, max_length=50, description="System names")
    hours: int = Field(24, ge=1, le=168, description="Lookback period (1-168 hours)")


class BulkStatsResponse(BaseModel):
    """Response for bulk system stats."""

    hours: int
    total_systems: int
    stats: dict[str, ZKillStats]


class HotSystemStats(BaseModel):
    """Stats for a hot system."""

    system_id: int
    system_name: str
    recent_kills: int
    recent_pods: int
    total_activity: int


class HotSystemsResponse(BaseModel):
    """Response for hot systems endpoint."""

    hours: int
    systems: list[HotSystemStats]


@router.get(
    "/system/{system_name}",
    response_model=SystemStatsResponse,
    summary="Get kill stats for a system",
    description="Returns recent kill statistics from zKillboard for a specific system.",
)
async def get_system_stats(
    system_name: str,
    hours: int = Query(24, ge=1, le=168, description="Lookback period in hours"),
) -> SystemStatsResponse:
    """Get kill statistics for a single system."""
    universe = load_universe()

    if system_name not in universe.systems:
        raise HTTPException(status_code=404, detail=f"Unknown system: {system_name}")

    system = universe.systems[system_name]
    stats = await fetch_system_kills(system.id, hours)

    return SystemStatsResponse(
        system_id=system.id,
        system_name=system_name,
        hours=hours,
        stats=stats,
    )


@router.post(
    "/bulk",
    response_model=BulkStatsResponse,
    summary="Get kill stats for multiple systems",
    description="Returns recent kill statistics for multiple systems. Limited to 50 systems per request.",
)
async def get_bulk_stats(
    request: BulkStatsRequest,
    _character: AuthenticatedCharacter = Depends(require_pro),
) -> BulkStatsResponse:
    """Get kill statistics for multiple systems."""
    universe = load_universe()

    # Validate systems and collect IDs
    system_ids: list[int] = []
    name_to_id: dict[int, str] = {}

    for name in request.systems:
        if name not in universe.systems:
            raise HTTPException(status_code=400, detail=f"Unknown system: {name}")
        system = universe.systems[name]
        system_ids.append(system.id)
        name_to_id[system.id] = name

    # Fetch stats
    stats_by_id = await fetch_bulk_system_stats(system_ids, request.hours)

    # Convert to name-keyed response
    stats_by_name: dict[str, ZKillStats] = {}
    for system_id, stats in stats_by_id.items():
        name = name_to_id[system_id]
        stats_by_name[name] = stats

    return BulkStatsResponse(
        hours=request.hours,
        total_systems=len(stats_by_name),
        stats=stats_by_name,
    )


@router.get(
    "/hot",
    response_model=HotSystemsResponse,
    summary="Get hot systems",
    description="Returns the most active systems (trade hubs and dangerous pipes) with current kill stats.",
)
async def get_hot_systems(
    hours: int = Query(24, ge=1, le=168, description="Lookback period in hours"),
) -> HotSystemsResponse:
    """Get stats for known hot systems (trade hubs, pipes)."""
    universe = load_universe()
    preloader = get_zkill_preloader()

    # Use preloader's priority systems
    priority_ids = preloader._priority_systems

    # Build name mapping
    id_to_name: dict[int, str] = {}
    for name, system in universe.systems.items():
        if system.id in priority_ids:
            id_to_name[system.id] = name

    # Fetch stats
    stats_by_id = await fetch_bulk_system_stats(priority_ids, hours)

    # Build response sorted by activity
    systems: list[HotSystemStats] = []
    for system_id, stats in stats_by_id.items():
        name = id_to_name.get(system_id, f"System-{system_id}")
        systems.append(
            HotSystemStats(
                system_id=system_id,
                system_name=name,
                recent_kills=stats.recent_kills,
                recent_pods=stats.recent_pods,
                total_activity=stats.recent_kills + stats.recent_pods,
            )
        )

    # Sort by total activity descending
    systems.sort(key=lambda s: s.total_activity, reverse=True)

    return HotSystemsResponse(hours=hours, systems=systems)
