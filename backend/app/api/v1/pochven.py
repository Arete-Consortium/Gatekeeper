"""Pochven filament routing API endpoints."""

from fastapi import APIRouter

from ...models.pochven import (
    PochvenNetwork,
    PochvenStatusResponse,
    PochvenToggleRequest,
)
from ...services.pochven import (
    get_active_pochven,
    get_pochven_systems,
    is_pochven_enabled,
    toggle_pochven,
)

router = APIRouter()


@router.get(
    "/",
    response_model=PochvenNetwork,
    summary="List Pochven connections",
    description="Returns all Pochven filament connections (internal + entry/exit).",
)
def list_pochven_connections() -> PochvenNetwork:
    """List all Pochven connections."""
    connections = get_active_pochven()
    return PochvenNetwork(
        connections=connections,
        enabled=is_pochven_enabled(),
    )


@router.get(
    "/status",
    response_model=PochvenStatusResponse,
    summary="Pochven network status",
    description="Returns whether Pochven routing is enabled and connection counts.",
)
def pochven_status() -> PochvenStatusResponse:
    """Check Pochven network status."""
    connections = get_active_pochven()
    systems = get_pochven_systems()
    return PochvenStatusResponse(
        enabled=is_pochven_enabled(),
        connection_count=len(connections),
        system_count=len(systems),
    )


@router.patch(
    "/",
    response_model=PochvenStatusResponse,
    summary="Toggle Pochven routing",
    description="Enable or disable Pochven filament routing.",
)
def toggle_pochven_routing(request: PochvenToggleRequest) -> PochvenStatusResponse:
    """Toggle Pochven routing on/off."""
    toggle_pochven(request.enabled)
    connections = get_active_pochven()
    systems = get_pochven_systems()
    return PochvenStatusResponse(
        enabled=is_pochven_enabled(),
        connection_count=len(connections),
        system_count=len(systems),
    )
