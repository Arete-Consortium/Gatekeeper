"""Map Visualization API v1 endpoints.

Provides endpoints for route and region map data with security and threat overlays.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.map_visualization import (
    ConnectionType,
    RegionMapData,
    RouteVisualization,
    SecurityLevel,
    SystemConnection,
    SystemNode,
    ThreatLevel,
    get_constellation_map,
    get_region_map,
    get_route_visualization,
    get_security_color,
    get_systems_in_range,
    get_threat_color,
)

router = APIRouter(prefix="/map", tags=["map"])


# =============================================================================
# Response Models
# =============================================================================


class SystemNodeResponse(BaseModel):
    """System node for map rendering."""

    system_id: int
    system_name: str
    security_status: float
    security_level: str
    security_color: str
    region_name: str | None
    constellation_name: str | None
    threat_level: str
    threat_color: str
    kills_last_hour: int
    npc_kills_last_hour: int
    jumps_last_hour: int
    is_route_system: bool
    route_index: int | None

    @classmethod
    def from_node(cls, node: SystemNode) -> "SystemNodeResponse":
        return cls(
            system_id=node.system_id,
            system_name=node.system_name,
            security_status=node.security_status,
            security_level=node.security_level.value,
            security_color=get_security_color(node.security_status),
            region_name=node.region_name,
            constellation_name=node.constellation_name,
            threat_level=node.threat_level.value,
            threat_color=get_threat_color(node.threat_level),
            kills_last_hour=node.kills_last_hour,
            npc_kills_last_hour=node.npc_kills_last_hour,
            jumps_last_hour=node.jumps_last_hour,
            is_route_system=node.is_route_system,
            route_index=node.route_index,
        )


class ConnectionResponse(BaseModel):
    """Connection between systems."""

    from_system_id: int
    to_system_id: int
    from_system_name: str
    to_system_name: str
    connection_type: str
    is_route_connection: bool

    @classmethod
    def from_connection(cls, conn: SystemConnection) -> "ConnectionResponse":
        return cls(
            from_system_id=conn.from_system_id,
            to_system_id=conn.to_system_id,
            from_system_name=conn.from_system_name,
            to_system_name=conn.to_system_name,
            connection_type=conn.connection_type.value,
            is_route_connection=conn.is_route_connection,
        )


class RouteVisualizationResponse(BaseModel):
    """Complete route visualization data."""

    route_id: str
    systems: list[SystemNodeResponse]
    connections: list[ConnectionResponse]
    total_jumps: int
    high_sec_jumps: int
    low_sec_jumps: int
    null_sec_jumps: int
    dangerous_systems: list[str]
    jump_bridge_used: int
    cyno_jumps_used: int

    @classmethod
    def from_visualization(cls, viz: RouteVisualization) -> "RouteVisualizationResponse":
        return cls(
            route_id=viz.route_id,
            systems=[SystemNodeResponse.from_node(s) for s in viz.systems],
            connections=[ConnectionResponse.from_connection(c) for c in viz.connections],
            total_jumps=viz.total_jumps,
            high_sec_jumps=viz.high_sec_jumps,
            low_sec_jumps=viz.low_sec_jumps,
            null_sec_jumps=viz.null_sec_jumps,
            dangerous_systems=viz.dangerous_systems,
            jump_bridge_used=viz.jump_bridge_used,
            cyno_jumps_used=viz.cyno_jumps_used,
        )


class RegionMapResponse(BaseModel):
    """Region map data."""

    region_id: int
    region_name: str
    system_count: int
    connection_count: int
    systems: list[SystemNodeResponse]
    connections: list[ConnectionResponse]

    @classmethod
    def from_region_data(cls, data: RegionMapData) -> "RegionMapResponse":
        return cls(
            region_id=data.region_id,
            region_name=data.region_name,
            system_count=len(data.systems),
            connection_count=len(data.connections),
            systems=[SystemNodeResponse.from_node(s) for s in data.systems],
            connections=[ConnectionResponse.from_connection(c) for c in data.connections],
        )


class SystemsInRangeResponse(BaseModel):
    """Systems within jump range."""

    center_system: str
    max_jumps: int
    system_count: int
    connection_count: int
    systems: list[SystemNodeResponse]
    connections: list[ConnectionResponse]


class RouteVisualizationRequest(BaseModel):
    """Request for route visualization."""

    route: list[str] = Field(..., description="List of system names in route order")
    jump_bridges: list[tuple[str, str]] = Field(
        default_factory=list, description="Jump bridge connections used"
    )
    cyno_jumps: list[tuple[str, str]] = Field(
        default_factory=list, description="Cyno jump connections used"
    )
    threat_systems: dict[str, str] = Field(
        default_factory=dict,
        description="System name to threat level mapping (safe, caution, dangerous, deadly)",
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/route",
    response_model=RouteVisualizationResponse,
    summary="Get route visualization",
    description="Get visualization data for a route including security colors and threat overlays.",
)
async def visualize_route(request: RouteVisualizationRequest) -> RouteVisualizationResponse:
    """
    Generate visualization data for a route.

    Includes security status colors, jump bridge/cyno indicators,
    and threat level overlays for each system.
    """
    if len(request.route) < 2:
        raise HTTPException(status_code=400, detail="Route must have at least 2 systems")

    # Convert threat level strings to enum
    threat_data: dict[str, ThreatLevel] = {}
    for system, level in request.threat_systems.items():
        try:
            threat_data[system] = ThreatLevel(level)
        except ValueError:
            pass  # Ignore invalid threat levels

    viz = get_route_visualization(
        route=request.route,
        jump_bridges=request.jump_bridges,
        cyno_jumps=request.cyno_jumps,
        threat_data=threat_data,
    )

    if not viz:
        raise HTTPException(status_code=404, detail="Could not generate route visualization")

    return RouteVisualizationResponse.from_visualization(viz)


@router.get(
    "/region/{region_name}",
    response_model=RegionMapResponse,
    summary="Get region map",
    description="Get all systems and connections for a region.",
)
async def get_region_map_endpoint(region_name: str) -> RegionMapResponse:
    """Get region map data for visualization."""
    data = get_region_map(region_name)
    if not data:
        raise HTTPException(status_code=404, detail=f"Region not found: {region_name}")
    return RegionMapResponse.from_region_data(data)


@router.get(
    "/constellation/{constellation_name}",
    response_model=RegionMapResponse,
    summary="Get constellation map",
    description="Get all systems and connections for a constellation.",
)
async def get_constellation_map_endpoint(constellation_name: str) -> RegionMapResponse:
    """Get constellation map data for visualization."""
    data = get_constellation_map(constellation_name)
    if not data:
        raise HTTPException(
            status_code=404, detail=f"Constellation not found: {constellation_name}"
        )
    return RegionMapResponse.from_region_data(data)


@router.get(
    "/range/{center_system}",
    response_model=SystemsInRangeResponse,
    summary="Get systems in range",
    description="Get all systems within a certain jump range of a center system.",
)
async def get_systems_in_range_endpoint(
    center_system: str,
    max_jumps: int = Query(5, ge=1, le=20, description="Maximum jump distance"),
    include_connections: bool = Query(True, description="Include gate connections"),
) -> SystemsInRangeResponse:
    """Get all systems within jump range of center."""
    result = get_systems_in_range(center_system, max_jumps, include_connections)
    if not result:
        raise HTTPException(status_code=404, detail=f"System not found: {center_system}")

    systems, connections = result
    return SystemsInRangeResponse(
        center_system=center_system,
        max_jumps=max_jumps,
        system_count=len(systems),
        connection_count=len(connections),
        systems=[SystemNodeResponse.from_node(s) for s in systems],
        connections=[ConnectionResponse.from_connection(c) for c in connections],
    )


@router.get(
    "/colors/security",
    summary="Get security color legend",
    description="Get the color mapping for security status values.",
)
async def get_security_colors() -> dict[str, str]:
    """Get security status color legend."""
    return {
        "1.0": get_security_color(1.0),
        "0.9": get_security_color(0.9),
        "0.8": get_security_color(0.8),
        "0.7": get_security_color(0.7),
        "0.6": get_security_color(0.6),
        "0.5": get_security_color(0.5),
        "0.4": get_security_color(0.4),
        "0.3": get_security_color(0.3),
        "0.2": get_security_color(0.2),
        "0.1": get_security_color(0.1),
        "0.0": get_security_color(0.0),
        "-0.5": get_security_color(-0.5),
        "-1.0": get_security_color(-1.0),
    }


@router.get(
    "/colors/threat",
    summary="Get threat color legend",
    description="Get the color mapping for threat levels.",
)
async def get_threat_colors() -> dict[str, str]:
    """Get threat level color legend."""
    return {level.value: get_threat_color(level) for level in ThreatLevel}


@router.get(
    "/connection-types",
    summary="List connection types",
    description="List all supported connection types.",
)
async def list_connection_types() -> list[str]:
    """List all connection types."""
    return [ct.value for ct in ConnectionType]


@router.get(
    "/security-levels",
    summary="List security levels",
    description="List all security level classifications.",
)
async def list_security_levels() -> list[str]:
    """List all security levels."""
    return [sl.value for sl in SecurityLevel]


# =============================================================================
# Market Hub Models & Endpoint
# =============================================================================


class MarketHubResponse(BaseModel):
    """A major trade hub with estimated daily volume."""

    system_id: int
    system_name: str
    region_name: str
    is_primary: bool = Field(description="True for Jita (the dominant hub)")
    daily_volume_estimate: float = Field(description="Estimated daily ISK volume")
    active_orders: int = Field(
        default=0, description="Estimated active market orders in the region"
    )


class MarketHubsResponse(BaseModel):
    """All major trade hubs."""

    hubs: list[MarketHubResponse]


@router.get(
    "/market-hubs",
    response_model=MarketHubsResponse,
    summary="Get major trade hub data",
    description="Returns market activity data for the 5 major EVE trade hubs with live ESI order counts.",
)
async def get_market_hubs() -> MarketHubsResponse:
    """Get trade hub data for map overlay.

    Fetches live active order counts from ESI (cached 30 min).
    Falls back to static estimates if ESI is unavailable.
    """
    from ...services.market_hubs import fetch_market_hub_data

    hub_data = await fetch_market_hub_data()
    return MarketHubsResponse(
        hubs=[
            MarketHubResponse(
                system_id=h.system_id,
                system_name=h.system_name,
                region_name=h.region_name,
                is_primary=h.is_primary,
                daily_volume_estimate=h.daily_volume_estimate,
                active_orders=h.active_orders,
            )
            for h in hub_data
        ]
    )
