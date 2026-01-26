"""Intel API v1 endpoints.

Provides endpoints for submitting and retrieving intel channel data.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...services.intel_parser import (
    IntelReport,
    SystemIntel,
    get_intel_store,
    parse_intel_text,
    submit_intel,
)

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
