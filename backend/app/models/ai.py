"""AI route analysis models."""

from pydantic import BaseModel, Field

from .risk import DangerLevel


class SystemWarning(BaseModel):
    """Warning for a dangerous system on a route."""

    system_name: str
    system_id: int
    danger_level: DangerLevel
    recent_kills: int
    recent_pods: int
    warning_text: str = Field(..., description="Human-readable warning message")


class AlternativeRoute(BaseModel):
    """An alternative safer route suggestion."""

    profile: str = Field(..., description="Routing profile used (e.g., 'safer', 'paranoid')")
    total_jumps: int
    max_risk: float
    avg_risk: float
    dangerous_systems: int = Field(0, description="Number of high/extreme danger systems")
    improvement: str = Field(..., description="Description of how this route is better")


class PathDanger(BaseModel):
    """Danger information for a single system on the path."""

    system_name: str
    danger_level: DangerLevel
    recent_kills: int


class RouteAnalysisRequest(BaseModel):
    """Request for AI route analysis."""

    from_system: str = Field(..., description="Origin system name")
    to_system: str = Field(..., description="Destination system name")
    profile: str = Field("shortest", description="Routing profile to analyze")
    include_alternatives: bool = Field(
        True, description="Include alternative route suggestions when dangerous systems detected"
    )
    use_bridges: bool = Field(False, description="Include Ansiblex bridges in routing")
    avoid: list[str] = Field(default_factory=list, description="Systems to avoid")


class RouteAnalysisResponse(BaseModel):
    """Response from AI route analysis with human-readable assessment."""

    from_system: str
    to_system: str
    profile: str
    total_jumps: int
    overall_danger: DangerLevel = Field(
        ..., description="Overall danger level for the route (worst system)"
    )
    assessment: str = Field(..., description="Human-readable route assessment")
    warnings: list[SystemWarning] = Field(
        default_factory=list, description="Warnings for dangerous systems on route"
    )
    alternatives: list[AlternativeRoute] = Field(
        default_factory=list, description="Safer route alternatives if available"
    )
    path_danger: list[PathDanger] = Field(
        default_factory=list, description="Danger level for each system on path"
    )


class DangerThresholdsResponse(BaseModel):
    """Current danger threshold configuration."""

    medium: int = Field(..., description="Kills threshold for medium danger")
    high: int = Field(..., description="Kills threshold for high danger")
    extreme: int = Field(..., description="Kills threshold for extreme danger")
    description: str = Field(
        "Thresholds based on total kills + pods in 24h window",
        description="How thresholds are applied",
    )
