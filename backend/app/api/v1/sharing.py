"""Route sharing API v1 endpoints.

Enables sharing routes via short tokens and exporting in various formats.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...core.pagination import (
    PaginationMeta,
    PaginationParams,
    get_pagination_params,
    paginate,
)
from ...services.route_sharing import (
    SharedRoute,
    export_to_dotlan_url,
    export_to_eveeye_url,
    export_to_json,
    export_to_text,
    export_to_waypoint_names,
    get_share_store,
)

router = APIRouter(prefix="/share", tags=["sharing"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateShareRequest(BaseModel):
    """Request to create a shared route."""

    route_data: dict[str, Any] = Field(..., description="Full route response data")
    ttl_hours: int | None = Field(None, description="Hours until expiry (-1 for never)")
    creator_name: str | None = Field(None, description="Creator name")
    description: str | None = Field(None, description="Optional description")


class SharedRouteResponse(BaseModel):
    """Response model for a shared route."""

    token: str
    url_path: str
    from_system: str
    to_system: str
    total_jumps: int
    profile: str
    created_at: datetime
    expires_at: datetime | None
    creator_name: str | None
    description: str | None
    access_count: int
    last_accessed: datetime | None

    @classmethod
    def from_shared(cls, shared: SharedRoute) -> "SharedRouteResponse":
        """Create from SharedRoute."""
        return cls(
            token=shared.token,
            url_path=shared.url_path,
            from_system=shared.from_system,
            to_system=shared.to_system,
            total_jumps=shared.total_jumps,
            profile=shared.profile,
            created_at=shared.created_at,
            expires_at=shared.expires_at,
            creator_name=shared.creator_name,
            description=shared.description,
            access_count=shared.access_count,
            last_accessed=shared.last_accessed,
        )


class SharedRouteFullResponse(SharedRouteResponse):
    """Full response including route data."""

    route_data: dict[str, Any]

    @classmethod
    def from_shared(cls, shared: SharedRoute) -> "SharedRouteFullResponse":
        """Create from SharedRoute."""
        return cls(
            token=shared.token,
            url_path=shared.url_path,
            from_system=shared.from_system,
            to_system=shared.to_system,
            total_jumps=shared.total_jumps,
            profile=shared.profile,
            created_at=shared.created_at,
            expires_at=shared.expires_at,
            creator_name=shared.creator_name,
            description=shared.description,
            access_count=shared.access_count,
            last_accessed=shared.last_accessed,
            route_data=shared.route_data,
        )


class SharedRoutesListResponse(BaseModel):
    """Response for listing shared routes."""

    items: list[SharedRouteResponse]
    pagination: PaginationMeta


class ExportResponse(BaseModel):
    """Response with exported route data."""

    format: str
    content: str


class ExportAllFormatsResponse(BaseModel):
    """Response with all export formats."""

    text: str
    json_str: str = Field(..., alias="json")
    waypoint_systems: list[str]
    dotlan_url: str
    eveeye_url: str

    model_config = {"populate_by_name": True}


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=SharedRouteResponse,
    summary="Create shared route",
    description="Create a shareable link for a route.",
)
async def create_share(request: CreateShareRequest) -> SharedRouteResponse:
    """
    Create a shared route.

    Returns a token that can be used to retrieve the route.
    """
    store = get_share_store()

    shared = store.create_share(
        route_data=request.route_data,
        ttl_hours=request.ttl_hours,
        creator_name=request.creator_name,
        description=request.description,
    )

    return SharedRouteResponse.from_shared(shared)


@router.get(
    "/{token}",
    response_model=SharedRouteFullResponse,
    summary="Get shared route",
    description="Retrieve a shared route by token.",
)
async def get_share(token: str) -> SharedRouteFullResponse:
    """
    Get a shared route by its token.

    Returns the full route data including path.
    """
    store = get_share_store()
    shared = store.get_share(token)

    if not shared:
        raise HTTPException(
            status_code=404,
            detail=f"Shared route not found or expired: {token}",
        )

    return SharedRouteFullResponse.from_shared(shared)


@router.delete(
    "/{token}",
    summary="Delete shared route",
    description="Delete a shared route by token.",
)
async def delete_share(token: str) -> dict[str, str]:
    """
    Delete a shared route.

    Returns success/failure status.
    """
    store = get_share_store()
    deleted = store.delete_share(token)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Shared route not found: {token}",
        )

    return {"status": "deleted", "token": token}


@router.get(
    "/",
    response_model=SharedRoutesListResponse,
    summary="List shared routes",
    description="List shared routes with pagination, optionally filtered by creator.",
)
async def list_shares(
    pagination: PaginationParams = Depends(get_pagination_params),
    creator: str | None = Query(None, description="Filter by creator name"),
) -> SharedRoutesListResponse:
    """
    List shared routes with pagination.

    Optionally filter by creator name.
    """
    store = get_share_store()
    # Get all routes (the store returns all matching routes)
    all_routes = store.list_shares(creator_name=creator, limit=1000)  # High limit to get all
    route_responses = [SharedRouteResponse.from_shared(r) for r in all_routes]

    items, meta = paginate(route_responses, pagination.page, pagination.page_size)

    return SharedRoutesListResponse(items=items, pagination=meta)


# =============================================================================
# Export Endpoints
# =============================================================================


@router.post(
    "/export/text",
    response_model=ExportResponse,
    summary="Export route as text",
    description="Export route data as human-readable text.",
)
async def export_text(route_data: dict[str, Any]) -> ExportResponse:
    """
    Export route as plain text.

    Example format:
    ```
    Route: Jita -> Amarr (15 jumps, safer)
    1. Jita (0.95)
    2. Perimeter (0.94)
    ...
    ```
    """
    content = export_to_text(route_data)
    return ExportResponse(format="text", content=content)


@router.post(
    "/export/json",
    response_model=ExportResponse,
    summary="Export route as JSON",
    description="Export route data as JSON string.",
)
async def export_json_format(
    route_data: dict[str, Any],
    pretty: bool = Query(False, description="Pretty print JSON"),
) -> ExportResponse:
    """Export route as JSON string."""
    content = export_to_json(route_data, pretty=pretty)
    return ExportResponse(format="json", content=content)


@router.post(
    "/export/waypoints",
    summary="Export route as waypoint list",
    description="Export route as list of system names for waypoint setting.",
)
async def export_waypoints(route_data: dict[str, Any]) -> dict[str, list[str]]:
    """
    Export route as list of system names.

    Useful for setting in-game waypoints.
    """
    systems = export_to_waypoint_names(route_data)
    return {"systems": systems}


@router.post(
    "/export/dotlan",
    response_model=ExportResponse,
    summary="Export as Dotlan URL",
    description="Generate Dotlan route URL.",
)
async def export_dotlan(route_data: dict[str, Any]) -> ExportResponse:
    """Generate Dotlan route URL."""
    url = export_to_dotlan_url(route_data)
    return ExportResponse(format="url", content=url)


@router.post(
    "/export/eveeye",
    response_model=ExportResponse,
    summary="Export as EVE Eye URL",
    description="Generate EVE Eye route URL.",
)
async def export_eveeye(route_data: dict[str, Any]) -> ExportResponse:
    """Generate EVE Eye route URL."""
    url = export_to_eveeye_url(route_data)
    return ExportResponse(format="url", content=url)


@router.post(
    "/export/all",
    response_model=ExportAllFormatsResponse,
    summary="Export in all formats",
    description="Export route in all available formats at once.",
)
async def export_all_formats(route_data: dict[str, Any]) -> ExportAllFormatsResponse:
    """Export route in all formats."""
    return ExportAllFormatsResponse(
        text=export_to_text(route_data),
        json=export_to_json(route_data),
        waypoint_systems=export_to_waypoint_names(route_data),
        dotlan_url=export_to_dotlan_url(route_data),
        eveeye_url=export_to_eveeye_url(route_data),
    )


@router.get(
    "/{token}/export",
    response_model=ExportAllFormatsResponse,
    summary="Export shared route",
    description="Export a shared route in all formats.",
)
async def export_shared_route(token: str) -> ExportAllFormatsResponse:
    """
    Export a shared route in all formats.

    Combines get and export in one call.
    """
    store = get_share_store()
    shared = store.get_share(token)

    if not shared:
        raise HTTPException(
            status_code=404,
            detail=f"Shared route not found or expired: {token}",
        )

    return ExportAllFormatsResponse(
        text=export_to_text(shared.route_data),
        json=export_to_json(shared.route_data),
        waypoint_systems=export_to_waypoint_names(shared.route_data),
        dotlan_url=export_to_dotlan_url(shared.route_data),
        eveeye_url=export_to_eveeye_url(shared.route_data),
    )
