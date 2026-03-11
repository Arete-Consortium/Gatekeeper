"""Intel API v1 endpoints.

Provides endpoints for submitting and retrieving intel channel data.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.intel_parser import (
    IntelReport,
    IntelStats,
    SystemIntel,
    get_intel_stats,
    get_intel_store,
    get_nearby_intel,
    parse_intel_text,
    submit_intel,
)
from ...services.pilot_intel import get_pilot_stats, resolve_character_names

router = APIRouter(prefix="/intel", tags=["intel"])


# =============================================================================
# Request/Response Models
# =============================================================================


class IntelSubmitRequest(BaseModel):
    """Request to submit intel text."""

    text: str = Field(..., description="Intel channel text (single or multi-line)")
    reporter: str | None = Field(None, description="Optional reporter name")


class IntelReportResponse(BaseModel):
    """Response model for a single intel report."""

    system_name: str
    hostile_count: int
    hostile_names: list[str]
    reported_at: datetime
    reporter: str | None
    raw_text: str
    is_clear: bool
    threat_type: str = Field(
        default="hostile", description="Type of threat: hostile, gate_camp, bubble, fleet"
    )
    ship_types: list[str] = Field(default_factory=list, description="Ship types detected in report")
    direction: str | None = Field(None, description="Direction of travel if detected")

    @classmethod
    def from_report(cls, report: IntelReport) -> "IntelReportResponse":
        """Create from IntelReport."""
        return cls(
            system_name=report.system_name,
            hostile_count=report.hostile_count,
            hostile_names=report.hostile_names,
            reported_at=report.reported_at,
            reporter=report.reporter,
            raw_text=report.raw_text,
            is_clear=report.is_clear,
            threat_type=report.threat_type.value,
            ship_types=report.ship_types,
            direction=report.direction,
        )


class IntelSubmitResponse(BaseModel):
    """Response after submitting intel."""

    reports_parsed: int
    reports: list[IntelReportResponse]


class SystemIntelResponse(BaseModel):
    """Response model for system intel."""

    system_name: str
    total_hostiles: int
    is_clear: bool
    last_updated: datetime
    age_seconds: float
    reports: list[IntelReportResponse]

    @classmethod
    def from_intel(cls, intel: SystemIntel) -> "SystemIntelResponse":
        """Create from SystemIntel."""
        return cls(
            system_name=intel.system_name,
            total_hostiles=intel.total_hostiles,
            is_clear=intel.is_clear,
            last_updated=intel.last_updated,
            age_seconds=intel.age_seconds,
            reports=[IntelReportResponse.from_report(r) for r in intel.reports],
        )


class AllIntelResponse(BaseModel):
    """Response model for all intel."""

    total_systems: int
    total_hostiles: int
    systems: dict[str, SystemIntelResponse]


class ParsePreviewResponse(BaseModel):
    """Response for parsing preview (doesn't store)."""

    valid: bool
    reports: list[IntelReportResponse]


class HostileSystemsResponse(BaseModel):
    """Response listing systems with hostiles."""

    count: int
    systems: list[str]


class IntelStatsResponse(BaseModel):
    """Response model for intel statistics."""

    total_systems: int = Field(..., description="Number of systems with intel")
    total_hostiles: int = Field(..., description="Total hostile count across all systems")
    total_reports: int = Field(..., description="Total number of intel reports")
    gate_camps: int = Field(..., description="Number of gate camp reports")
    bubbles: int = Field(..., description="Number of bubble reports")
    fleets: int = Field(..., description="Number of fleet reports")
    oldest_report_seconds: float = Field(..., description="Age of oldest report in seconds")
    newest_report_seconds: float = Field(..., description="Age of newest report in seconds")

    @classmethod
    def from_stats(cls, stats: IntelStats) -> "IntelStatsResponse":
        """Create from IntelStats."""
        return cls(
            total_systems=stats.total_systems,
            total_hostiles=stats.total_hostiles,
            total_reports=stats.total_reports,
            gate_camps=stats.gate_camps,
            bubbles=stats.bubbles,
            fleets=stats.fleets,
            oldest_report_seconds=stats.oldest_report_seconds,
            newest_report_seconds=stats.newest_report_seconds,
        )


class NearbyIntelResponse(BaseModel):
    """Response model for nearby systems intel."""

    center_system: str
    max_jumps: int
    systems_with_intel: int
    systems: dict[str, SystemIntelResponse]


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/submit",
    response_model=IntelSubmitResponse,
    summary="Submit intel text",
    description="Parse and store intel channel text. Supports single or multi-line input.",
)
async def submit_intel_text(request: IntelSubmitRequest) -> IntelSubmitResponse:
    """
    Submit intel channel text for parsing and storage.

    Supports common intel formats:
    - "Jita +1" - one hostile in Jita
    - "Jita +3" - three hostiles in Jita
    - "Jita clear" or "Jita clr" - Jita cleared
    - "Jita HostileName" - hostile by name in Jita
    """
    reports = submit_intel(request.text, request.reporter)
    return IntelSubmitResponse(
        reports_parsed=len(reports),
        reports=[IntelReportResponse.from_report(r) for r in reports],
    )


@router.post(
    "/parse",
    response_model=ParsePreviewResponse,
    summary="Preview intel parsing",
    description="Parse intel text without storing. Use for preview/validation.",
)
async def preview_intel_parse(request: IntelSubmitRequest) -> ParsePreviewResponse:
    """
    Preview how intel text would be parsed without storing it.

    Use this to validate intel format before submitting.
    """
    reports = parse_intel_text(request.text, request.reporter)
    return ParsePreviewResponse(
        valid=len(reports) > 0,
        reports=[IntelReportResponse.from_report(r) for r in reports],
    )


@router.get(
    "/system/{system_name}",
    response_model=SystemIntelResponse,
    summary="Get system intel",
    description="Get current intel for a specific system.",
)
async def get_system_intel(system_name: str) -> SystemIntelResponse:
    """
    Get current intel for a specific system.

    Returns 404 if no intel exists for the system.
    """
    store = get_intel_store()
    intel = store.get_system_intel(system_name)

    if not intel:
        raise HTTPException(
            status_code=404,
            detail=f"No intel for system: {system_name}",
        )

    return SystemIntelResponse.from_intel(intel)


@router.get(
    "/all",
    response_model=AllIntelResponse,
    summary="Get all intel",
    description="Get current intel for all systems with reported hostiles.",
)
async def get_all_intel() -> AllIntelResponse:
    """
    Get current intel for all systems with reported hostiles.

    Only returns systems that currently have hostile reports (not cleared).
    """
    store = get_intel_store()
    all_intel = store.get_all_intel()

    systems = {name: SystemIntelResponse.from_intel(intel) for name, intel in all_intel.items()}

    total_hostiles = sum(intel.total_hostiles for intel in all_intel.values())

    return AllIntelResponse(
        total_systems=len(systems),
        total_hostiles=total_hostiles,
        systems=systems,
    )


@router.get(
    "/hostile-systems",
    response_model=HostileSystemsResponse,
    summary="Get hostile systems list",
    description="Get list of system names with reported hostiles.",
)
async def get_hostile_systems() -> HostileSystemsResponse:
    """
    Get a simple list of system names with reported hostiles.

    Useful for route planning to avoid hostile systems.
    """
    store = get_intel_store()
    systems = sorted(store.get_hostile_systems())

    return HostileSystemsResponse(
        count=len(systems),
        systems=systems,
    )


@router.delete(
    "/system/{system_name}",
    summary="Clear system intel",
    description="Clear all intel for a specific system.",
)
async def clear_system_intel(system_name: str) -> dict[str, str]:
    """
    Clear all intel for a specific system.

    Use this to manually mark a system as no longer having hostiles.
    """
    store = get_intel_store()
    store.clear_system(system_name)

    return {"status": "cleared", "system": system_name}


@router.delete(
    "/all",
    summary="Clear all intel",
    description="Clear all intel data. Use with caution.",
)
async def clear_all_intel() -> dict[str, str]:
    """
    Clear all intel data.

    Warning: This removes all current intel reports.
    """
    store = get_intel_store()
    store.clear_all()

    return {"status": "cleared", "message": "All intel cleared"}


@router.get(
    "/stats",
    response_model=IntelStatsResponse,
    summary="Get intel statistics",
    description="Get summary statistics about current intel state.",
)
async def get_stats() -> IntelStatsResponse:
    """
    Get summary statistics about current intel.

    Includes counts by threat type (gate camps, bubbles, fleets).
    """
    stats = get_intel_stats()
    return IntelStatsResponse.from_stats(stats)


@router.get(
    "/nearby/{system_name}",
    response_model=NearbyIntelResponse,
    summary="Get nearby systems intel",
    description="Get intel for systems within a certain number of jumps.",
)
async def get_nearby_systems_intel(
    system_name: str,
    max_jumps: int = Query(3, ge=1, le=10, description="Maximum jumps to search"),
) -> NearbyIntelResponse:
    """
    Get intel for systems within a certain number of jumps.

    Useful for situational awareness of nearby threats.
    """
    nearby = get_nearby_intel(system_name, max_jumps)

    systems = {name: SystemIntelResponse.from_intel(intel) for name, intel in nearby.items()}

    return NearbyIntelResponse(
        center_system=system_name,
        max_jumps=max_jumps,
        systems_with_intel=len(systems),
        systems=systems,
    )


# =============================================================================
# Pilot Intel
# =============================================================================


class PilotThreatResponse(BaseModel):
    """Pilot threat assessment combining ESI + zKill data."""

    character_id: int
    name: str
    corporation_id: int | None = None
    corporation_name: str = "Unknown"
    alliance_id: int | None = None
    alliance_name: str | None = None
    security_status: float = 0.0
    birthday: str | None = None
    kills: int = 0
    losses: int = 0
    kd_ratio: float = 0.0
    solo_kills: int = 0
    danger_ratio: int = 0
    gang_ratio: int = 0
    isk_destroyed: float = 0
    isk_lost: float = 0
    active_pvp_kills: int = 0
    threat_level: str = Field(
        "minimal",
        description="Computed threat: minimal, low, moderate, high, extreme",
    )
    active_timezone: str | None = Field(
        None, description="Inferred primary timezone: USTZ, EUTZ, AUTZ"
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Behavior flags: solo_hunter, capital_pilot, possible_cyno, gang_focus, recently_active",
    )
    top_ships: list[dict] = Field(default_factory=list)
    top_systems: list[dict] = Field(default_factory=list)


@router.get(
    "/pilot/{character_id}",
    response_model=PilotThreatResponse,
    summary="Get pilot threat assessment",
    description="Returns ESI character info + zKill aggregate stats with computed threat level.",
)
async def get_pilot_threat(character_id: int) -> PilotThreatResponse:
    """Get threat assessment for a pilot by character ID."""
    result = await get_pilot_stats(character_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Character {character_id} not found")
    return PilotThreatResponse(**result)


class FleetPilotLookupRequest(BaseModel):
    """Request to look up multiple pilots by name."""

    names: list[str] = Field(
        ..., description="Pilot names to look up", min_length=1, max_length=50
    )


class FleetPilotLookupResponse(BaseModel):
    """Aggregate fleet pilot assessment."""

    total_pilots: int
    resolved: int
    failed_names: list[str] = Field(default_factory=list)
    pilots: list[PilotThreatResponse] = Field(default_factory=list)
    aggregate: dict = Field(
        default_factory=dict,
        description="Aggregate stats: avg_kd, timezone_breakdown, threat_breakdown, total_flags",
    )


@router.post(
    "/pilot/fleet-lookup",
    response_model=FleetPilotLookupResponse,
    summary="Bulk pilot threat lookup",
    description="Resolve pilot names and return aggregate threat assessment for a fleet.",
)
async def fleet_pilot_lookup(request: FleetPilotLookupRequest) -> FleetPilotLookupResponse:
    """Look up multiple pilots by name and return aggregate threat data."""
    import asyncio

    # Resolve names to IDs
    name_to_id = await resolve_character_names(request.names)

    resolved_names = set(name_to_id.keys())
    failed_names = [n for n in request.names if n not in resolved_names]

    # Fetch stats for all resolved pilots (rate-limited, sequential)
    pilots: list[PilotThreatResponse] = []
    for name, char_id in name_to_id.items():
        result = await get_pilot_stats(char_id)
        if result:
            pilots.append(PilotThreatResponse(**result))

    # Compute aggregates
    threat_breakdown: dict[str, int] = {}
    tz_breakdown: dict[str, int] = {}
    total_kills = 0
    total_losses = 0
    flag_counts: dict[str, int] = {}

    for p in pilots:
        threat_breakdown[p.threat_level] = threat_breakdown.get(p.threat_level, 0) + 1
        if p.active_timezone:
            tz_breakdown[p.active_timezone] = tz_breakdown.get(p.active_timezone, 0) + 1
        total_kills += p.kills
        total_losses += p.losses
        for flag in p.flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    avg_kd = round(total_kills / max(total_losses, 1), 2) if pilots else 0

    # Sort pilots: highest threat first
    threat_order = {"extreme": 0, "high": 1, "moderate": 2, "low": 3, "minimal": 4}
    pilots.sort(key=lambda p: threat_order.get(p.threat_level, 5))

    return FleetPilotLookupResponse(
        total_pilots=len(request.names),
        resolved=len(pilots),
        failed_names=failed_names,
        pilots=pilots,
        aggregate={
            "avg_kd": avg_kd,
            "timezone_breakdown": tz_breakdown,
            "threat_breakdown": threat_breakdown,
            "flag_counts": flag_counts,
            "total_kills": total_kills,
            "total_losses": total_losses,
        },
    )
