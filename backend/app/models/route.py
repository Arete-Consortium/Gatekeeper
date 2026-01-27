from pydantic import BaseModel, Field


class RouteHop(BaseModel):
    system_name: str
    system_id: int
    cumulative_jumps: int
    cumulative_cost: float
    risk_score: float
    connection_type: str = Field(
        "gate", description="How we reached this system: 'gate', 'bridge', 'thera', or 'pochven'"
    )


class RouteResponse(BaseModel):
    from_system: str
    to_system: str
    profile: str
    total_jumps: int
    total_cost: float
    max_risk: float
    avg_risk: float
    path: list[RouteHop]
    bridges_used: int = Field(0, description="Number of Ansiblex bridges in route")
    thera_used: int = Field(0, description="Number of Thera wormhole shortcuts in route")
    pochven_used: int = Field(0, description="Number of Pochven filament connections in route")


class RouteCompareRequest(BaseModel):
    """Request for comparing multiple routes."""

    from_system: str = Field(..., description="Origin system name")
    to_system: str = Field(..., description="Destination system name")
    profiles: list[str] = Field(
        default=["shortest", "safer", "paranoid"], description="Profiles to compare"
    )
    use_bridges: bool = Field(False, description="Include bridges in routing")
    use_thera: bool = Field(False, description="Include Thera wormhole shortcuts")
    use_pochven: bool = Field(False, description="Include Pochven filament routing")
    avoid: list[str] = Field(default_factory=list, description="Systems to avoid")
    avoid_lists: list[str] = Field(
        default_factory=list, description="Named avoidance lists to apply"
    )


class RouteSummary(BaseModel):
    """Summary of a single route for comparison."""

    profile: str
    total_jumps: int
    total_cost: float
    max_risk: float
    avg_risk: float
    bridges_used: int = 0
    thera_used: int = 0
    pochven_used: int = 0
    highsec_jumps: int = 0
    lowsec_jumps: int = 0
    nullsec_jumps: int = 0
    path_systems: list[str] = Field(default_factory=list, description="System names in order")


class RouteCompareResponse(BaseModel):
    """Response comparing multiple routes."""

    from_system: str
    to_system: str
    routes: list[RouteSummary]
    recommendation: str = Field(..., description="Which route is recommended and why")


class WaypointRouteRequest(BaseModel):
    """Request for multi-stop route calculation."""

    from_system: str = Field(..., description="Origin system name")
    waypoints: list[str] = Field(
        ..., description="Ordered list of waypoint systems", min_length=1, max_length=20
    )
    profile: str = Field("shortest", description="Routing profile")
    use_bridges: bool = Field(False, description="Include bridges")
    use_thera: bool = Field(False, description="Include Thera shortcuts")
    use_pochven: bool = Field(False, description="Include Pochven filament routing")
    optimize: bool = Field(False, description="Reorder waypoints to minimize total jumps (TSP)")
    avoid: list[str] = Field(default_factory=list, description="Systems to avoid")


class WaypointLeg(BaseModel):
    """A single leg of a multi-stop route."""

    from_system: str
    to_system: str
    jumps: int
    cost: float
    bridges_used: int = 0
    thera_used: int = 0
    pochven_used: int = 0
    path_systems: list[str] = Field(default_factory=list)


class WaypointRouteResponse(BaseModel):
    """Response for multi-stop route."""

    from_system: str
    waypoints: list[str]
    optimized: bool = False
    original_order: list[str] = Field(
        default_factory=list, description="Original order if optimized"
    )
    total_jumps: int
    total_cost: float
    legs: list[WaypointLeg]
    total_bridges_used: int = 0
    total_thera_used: int = 0
    total_pochven_used: int = 0


class BulkRouteRequest(BaseModel):
    """Request for calculating multiple routes."""

    from_system: str = Field(..., description="Origin system name")
    to_systems: list[str] = Field(..., description="List of destination systems")
    profile: str = Field("shortest", description="Routing profile to use")
    use_bridges: bool = Field(False, description="Include bridges in routing")
    use_thera: bool = Field(False, description="Include Thera wormhole shortcuts")
    use_pochven: bool = Field(False, description="Include Pochven filament routing")
    avoid: list[str] = Field(default_factory=list, description="Systems to avoid")
    avoid_lists: list[str] = Field(
        default_factory=list, description="Named avoidance lists to apply"
    )


class BulkRouteResult(BaseModel):
    """Result for a single route in bulk calculation."""

    to_system: str
    success: bool
    total_jumps: int | None = None
    total_cost: float | None = None
    max_risk: float | None = None
    avg_risk: float | None = None
    bridges_used: int = 0
    thera_used: int = 0
    pochven_used: int = 0
    path_systems: list[str] = Field(default_factory=list)
    error: str | None = None


class BulkRouteResponse(BaseModel):
    """Response for bulk route calculation."""

    from_system: str
    profile: str
    total_destinations: int
    successful: int
    failed: int
    routes: list[BulkRouteResult]
