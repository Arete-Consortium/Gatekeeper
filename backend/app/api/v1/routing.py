"""Routing API v1 endpoints."""

from collections import deque
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...models.route import (
    BulkRouteRequest,
    BulkRouteResponse,
    BulkRouteResult,
    RouteCompareRequest,
    RouteCompareResponse,
    RouteResponse,
    RouteSummary,
)
from ...services.data_loader import load_risk_config, load_universe
from ...services.risk_engine import compute_risk, risk_to_color
from ...services.routing import compute_route

router = APIRouter()

# Route history storage (in-memory, last 100 routes)
MAX_HISTORY_SIZE = 100
_route_history: deque["RouteHistoryEntry"] = deque(maxlen=MAX_HISTORY_SIZE)


class RouteHistoryEntry(BaseModel):
    """Entry in route history."""

    from_system: str
    to_system: str
    profile: str
    total_jumps: int
    bridges_used: int = 0
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RouteHistoryResponse(BaseModel):
    """Response for route history."""

    total: int
    routes: list[RouteHistoryEntry]


def _add_to_history(route: RouteResponse) -> None:
    """Add a route to history."""
    entry = RouteHistoryEntry(
        from_system=route.from_system,
        to_system=route.to_system,
        profile=route.profile,
        total_jumps=route.total_jumps,
        bridges_used=route.bridges_used,
    )
    _route_history.appendleft(entry)


def get_route_history() -> list[RouteHistoryEntry]:
    """Get current route history (for testing)."""
    return list(_route_history)


def clear_route_history() -> None:
    """Clear route history (for testing)."""
    _route_history.clear()


@router.get(
    "/",
    response_model=RouteResponse,
    summary="Calculate route between systems",
    description="Calculates a route between two systems using the specified routing profile.",
)
def calculate_route(
    from_system: str = Query(..., alias="from", description="Origin system name"),
    to_system: str = Query(..., alias="to", description="Destination system name"),
    profile: str = Query(
        "shortest",
        description="Routing profile: 'shortest', 'safer', or 'paranoid'",
    ),
    avoid: list[str] | None = Query(
        None,
        description="Systems to avoid (comma-separated or repeated param)",
    ),
    bridges: bool = Query(
        False,
        description="Use Ansiblex jump bridges if available",
    ),
) -> RouteResponse:
    """
    Calculate a route between two systems.

    - **from**: The starting system name (e.g., "Jita")
    - **to**: The destination system name (e.g., "Amarr")
    - **profile**: Routing strategy
        - `shortest`: Minimum jumps, ignores risk
        - `safer`: Balanced approach, avoids high-risk systems
        - `paranoid`: Maximum safety, avoids all dangerous areas
    - **avoid**: Systems to exclude from routing (e.g., "Tama,Rancer" or multiple &avoid=Tama&avoid=Rancer)
    - **bridges**: Use Ansiblex jump bridges in route calculation
    """
    cfg = load_risk_config()
    if profile not in cfg.routing_profiles:
        available = ", ".join(cfg.routing_profiles.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown routing profile: '{profile}'. Available: {available}",
        )

    # Parse avoid list - handle comma-separated values
    avoid_set: set[str] = set()
    if avoid:
        for item in avoid:
            # Support comma-separated values in single param
            avoid_set.update(name.strip() for name in item.split(",") if name.strip())

    try:
        route = compute_route(from_system, to_system, profile, avoid=avoid_set, use_bridges=bridges)
        _add_to_history(route)
        return route
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/history",
    response_model=RouteHistoryResponse,
    summary="Get recent route history",
    description="Returns the most recently calculated routes (up to 100).",
)
def get_history(
    limit: int = Query(20, ge=1, le=100, description="Maximum routes to return"),
) -> RouteHistoryResponse:
    """Get recently calculated routes."""
    history = list(_route_history)[:limit]
    return RouteHistoryResponse(total=len(_route_history), routes=history)


@router.get(
    "/config",
    summary="Get map configuration",
    description="Returns the complete map configuration including all systems, risk scores, and colors.",
)
async def get_map_config() -> dict[str, Any]:
    """Get the complete map configuration for visualization."""
    universe = load_universe()
    cfg = load_risk_config()

    systems_payload = {}
    for name, sys in universe.systems.items():
        risk = compute_risk(name)
        color = risk_to_color(risk.score)
        systems_payload[name] = {
            "id": sys.id,
            "region_id": sys.region_id,
            "security": sys.security,
            "category": sys.category,
            "position": sys.position.dict(),
            "risk_score": risk.score,
            "risk_color": color,
        }

    return {
        "metadata": universe.metadata.dict(),
        "systems": systems_payload,
        "layers": cfg.map_layers,
        "routing_profiles": list(cfg.routing_profiles.keys()),
    }


@router.post(
    "/compare",
    response_model=RouteCompareResponse,
    summary="Compare multiple routes",
    description="Calculate and compare routes using different profiles.",
)
def compare_routes(request: RouteCompareRequest) -> RouteCompareResponse:
    """
    Compare routes between two systems using different profiles.

    Returns a side-by-side comparison with a recommendation.
    """
    universe = load_universe()
    cfg = load_risk_config()

    # Validate systems
    if request.from_system not in universe.systems:
        raise HTTPException(status_code=400, detail=f"Unknown system: {request.from_system}")
    if request.to_system not in universe.systems:
        raise HTTPException(status_code=400, detail=f"Unknown system: {request.to_system}")

    # Validate profiles
    for profile in request.profiles:
        if profile not in cfg.routing_profiles:
            available = ", ".join(cfg.routing_profiles.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Unknown profile: '{profile}'. Available: {available}",
            )

    avoid_set = set(request.avoid)
    routes: list[RouteSummary] = []

    for profile in request.profiles:
        try:
            route = compute_route(
                request.from_system,
                request.to_system,
                profile,
                avoid=avoid_set,
                use_bridges=request.use_bridges,
            )

            # Count security categories
            highsec = lowsec = nullsec = 0
            for hop in route.path:
                sys = universe.systems[hop.system_name]
                if sys.category == "highsec":
                    highsec += 1
                elif sys.category == "lowsec":
                    lowsec += 1
                elif sys.category == "nullsec":
                    nullsec += 1

            routes.append(
                RouteSummary(
                    profile=profile,
                    total_jumps=route.total_jumps,
                    total_cost=round(route.total_cost, 2),
                    max_risk=round(route.max_risk, 1),
                    avg_risk=round(route.avg_risk, 1),
                    bridges_used=route.bridges_used,
                    highsec_jumps=highsec,
                    lowsec_jumps=lowsec,
                    nullsec_jumps=nullsec,
                    path_systems=[hop.system_name for hop in route.path],
                )
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    # Generate recommendation
    recommendation = _generate_recommendation(routes)

    return RouteCompareResponse(
        from_system=request.from_system,
        to_system=request.to_system,
        routes=routes,
        recommendation=recommendation,
    )


def _generate_recommendation(routes: list[RouteSummary]) -> str:
    """Generate a recommendation based on route comparison."""
    if not routes:
        return "No routes available"

    if len(routes) == 1:
        return f"Only {routes[0].profile} profile calculated"

    # Find best by different criteria
    shortest = min(routes, key=lambda r: r.total_jumps)
    safest = min(routes, key=lambda r: r.max_risk)
    min(routes, key=lambda r: r.avg_risk)

    # Check if all routes are the same
    if all(
        r.total_jumps == routes[0].total_jumps and r.max_risk == routes[0].max_risk for r in routes
    ):
        return f"All profiles produce the same {routes[0].total_jumps}-jump route"

    # Build recommendation
    parts = []

    if shortest.profile != safest.profile:
        jump_diff = safest.total_jumps - shortest.total_jumps
        risk_diff = shortest.max_risk - safest.max_risk
        parts.append(
            f"'{shortest.profile}' is fastest ({shortest.total_jumps} jumps) but riskier (max {shortest.max_risk:.0f}). "
            f"'{safest.profile}' adds {jump_diff} jumps but reduces max risk by {risk_diff:.0f} points."
        )
    else:
        parts.append(
            f"'{shortest.profile}' is both fastest and safest ({shortest.total_jumps} jumps, max risk {shortest.max_risk:.0f})"
        )

    # Note if any route avoids lowsec/nullsec entirely
    for route in routes:
        if route.lowsec_jumps == 0 and route.nullsec_jumps == 0 and route.total_jumps > 0:
            parts.append(f"'{route.profile}' stays entirely in highsec.")
            break

    return " ".join(parts)


@router.post(
    "/bulk",
    response_model=BulkRouteResponse,
    summary="Calculate routes to multiple destinations",
    description="Calculate routes from one origin to multiple destinations.",
)
def bulk_routes(request: BulkRouteRequest) -> BulkRouteResponse:
    """
    Calculate routes from one origin to multiple destinations.

    Useful for planning multi-stop trips or comparing distances to various systems.
    Results are sorted by jump count (shortest first).
    """
    universe = load_universe()
    cfg = load_risk_config()

    # Validate origin
    if request.from_system not in universe.systems:
        raise HTTPException(status_code=400, detail=f"Unknown origin system: {request.from_system}")

    # Validate profile
    if request.profile not in cfg.routing_profiles:
        available = ", ".join(cfg.routing_profiles.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown profile: '{request.profile}'. Available: {available}",
        )

    avoid_set = set(request.avoid)
    results: list[BulkRouteResult] = []
    successful = 0
    failed = 0

    for dest in request.to_systems:
        # Skip if destination equals origin
        if dest == request.from_system:
            results.append(
                BulkRouteResult(
                    to_system=dest,
                    success=True,
                    total_jumps=0,
                    total_cost=0.0,
                    max_risk=0.0,
                    avg_risk=0.0,
                    path_systems=[dest],
                )
            )
            successful += 1
            continue

        # Check if destination exists
        if dest not in universe.systems:
            results.append(
                BulkRouteResult(
                    to_system=dest,
                    success=False,
                    error=f"Unknown system: {dest}",
                )
            )
            failed += 1
            continue

        try:
            route = compute_route(
                request.from_system,
                dest,
                request.profile,
                avoid=avoid_set,
                use_bridges=request.use_bridges,
            )
            results.append(
                BulkRouteResult(
                    to_system=dest,
                    success=True,
                    total_jumps=route.total_jumps,
                    total_cost=round(route.total_cost, 2),
                    max_risk=round(route.max_risk, 1),
                    avg_risk=round(route.avg_risk, 1),
                    bridges_used=route.bridges_used,
                    path_systems=[hop.system_name for hop in route.path],
                )
            )
            successful += 1
        except ValueError as e:
            results.append(
                BulkRouteResult(
                    to_system=dest,
                    success=False,
                    error=str(e),
                )
            )
            failed += 1

    # Sort by jump count (successful routes first, then by jumps)
    results.sort(key=lambda r: (not r.success, r.total_jumps or 999999))

    return BulkRouteResponse(
        from_system=request.from_system,
        profile=request.profile,
        total_destinations=len(request.to_systems),
        successful=successful,
        failed=failed,
        routes=results,
    )
