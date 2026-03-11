"""User-submitted jump bridge connection management API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException

from ...models.jumpbridge_connection import (
    JumpBridgeConnection,
    JumpBridgeConnectionCreate,
    JumpBridgeConnectionUpdate,
    JumpBridgeImportRequest,
    JumpBridgeImportResponse,
    JumpBridgeListResponse,
)
from ...services.jumpbridge_connections import get_jumpbridge_connection_service

router = APIRouter(prefix="/jumpbridges", tags=["jumpbridges"])


@router.get(
    "/",
    response_model=JumpBridgeListResponse,
    summary="List all jump bridge connections",
    description="Returns all user-submitted jump bridge connections.",
)
async def list_jumpbridges() -> JumpBridgeListResponse:
    """List all jump bridge connections."""
    service = get_jumpbridge_connection_service()
    connections = service.get_all_connections()
    return JumpBridgeListResponse(
        bridges=connections,
        total=len(connections),
    )


@router.get(
    "/{bridge_id}",
    response_model=JumpBridgeConnection,
    summary="Get a specific jump bridge connection",
    description="Returns details of a specific jump bridge connection by ID.",
)
async def get_jumpbridge(bridge_id: str) -> JumpBridgeConnection:
    """Get a specific jump bridge connection."""
    service = get_jumpbridge_connection_service()
    conn = service.get_connection(bridge_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Jump bridge connection not found")
    return conn


@router.post(
    "/",
    response_model=JumpBridgeConnection,
    summary="Add a jump bridge connection",
    description="Add a new user-submitted Ansiblex jump bridge connection.",
    status_code=201,
)
async def add_jumpbridge(
    data: JumpBridgeConnectionCreate,
    created_by: str | None = None,
) -> JumpBridgeConnection:
    """Add a new jump bridge connection."""
    service = get_jumpbridge_connection_service()
    try:
        conn = await service.add_connection(data, created_by=created_by)
        return conn
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.put(
    "/{bridge_id}",
    response_model=JumpBridgeConnection,
    summary="Update a jump bridge connection",
    description="Update status, owner, or notes for a jump bridge connection.",
)
async def update_jumpbridge(
    bridge_id: str,
    data: JumpBridgeConnectionUpdate,
) -> JumpBridgeConnection:
    """Update a jump bridge connection."""
    service = get_jumpbridge_connection_service()
    conn = await service.update_connection(bridge_id, data)
    if not conn:
        raise HTTPException(status_code=404, detail="Jump bridge connection not found")
    return conn


@router.delete(
    "/{bridge_id}",
    summary="Delete a jump bridge connection",
    description="Remove a jump bridge connection.",
)
async def delete_jumpbridge(bridge_id: str) -> dict[str, str]:
    """Delete a jump bridge connection."""
    service = get_jumpbridge_connection_service()
    conn = service.get_connection(bridge_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Jump bridge connection not found")

    await service.delete_connection(bridge_id)
    return {"status": "deleted", "bridge_id": bridge_id}


@router.post(
    "/import",
    response_model=JumpBridgeImportResponse,
    summary="Bulk import jump bridges",
    description='Import jump bridges from text paste. Format: "System A \u00bb System B" per line.',
    status_code=201,
)
async def import_jumpbridges(
    data: JumpBridgeImportRequest,
    created_by: str | None = None,
) -> JumpBridgeImportResponse:
    """Bulk import jump bridges from text paste."""
    service = get_jumpbridge_connection_service()
    return await service.import_bridges(data.text, created_by=created_by)


@router.get(
    "/stats",
    summary="Get jump bridge connection statistics",
    description="Returns statistics about user-submitted jump bridge connections.",
)
async def get_jumpbridge_stats() -> dict[str, Any]:
    """Get jump bridge connection statistics."""
    service = get_jumpbridge_connection_service()
    return service.get_stats()
