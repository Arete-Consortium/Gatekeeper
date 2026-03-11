"""Wormhole connection management API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException

from ...models.wormhole import (
    WormholeConnection,
    WormholeConnectionCreate,
    WormholeConnectionUpdate,
)
from ...services.connection_manager import connection_manager
from ...services.wormhole import get_wormhole_service

router = APIRouter(prefix="/wormholes", tags=["wormholes"])


@router.get(
    "/",
    summary="List all wormhole connections",
    description="Returns all active (non-expired) wormhole connections.",
)
async def list_wormholes() -> dict[str, Any]:
    """List all active wormhole connections."""
    service = get_wormhole_service()
    connections = service.get_all_connections()
    return {
        "count": len(connections),
        "connections": [conn.model_dump() for conn in connections],
    }


@router.post(
    "/",
    summary="Add a wormhole connection",
    description="Add a new user-submitted wormhole connection for routing.",
    status_code=201,
)
async def add_wormhole(
    data: WormholeConnectionCreate,
    created_by: str | None = None,
) -> WormholeConnection:
    """Add a new wormhole connection.

    Args:
        data: Wormhole connection details
        created_by: Optional character name who added the connection
    """
    service = get_wormhole_service()
    try:
        conn = await service.add_connection(data, created_by=created_by)
        # Broadcast map update to WebSocket clients
        await connection_manager.broadcast_wormhole_update(
            "added",
            {
                "id": conn.id,
                "from_system": conn.from_system,
                "to_system": conn.to_system,
                "wormhole_type": conn.wormhole_type.value,
                "bidirectional": conn.bidirectional,
            },
        )
        return conn
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/{connection_id}",
    summary="Get a specific wormhole connection",
    description="Returns details of a specific wormhole connection by ID.",
)
async def get_wormhole(connection_id: str) -> WormholeConnection:
    """Get a specific wormhole connection."""
    service = get_wormhole_service()
    conn = service.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Wormhole connection not found")
    return conn


@router.patch(
    "/{connection_id}",
    summary="Update a wormhole connection",
    description="Update mass status, life status, or notes for a wormhole connection.",
)
async def update_wormhole(
    connection_id: str,
    data: WormholeConnectionUpdate,
) -> WormholeConnection:
    """Update a wormhole connection."""
    service = get_wormhole_service()
    conn = await service.update_connection(connection_id, data)
    if not conn:
        raise HTTPException(status_code=404, detail="Wormhole connection not found")

    # Broadcast map update to WebSocket clients
    await connection_manager.broadcast_wormhole_update(
        "updated",
        {
            "id": conn.id,
            "from_system": conn.from_system,
            "to_system": conn.to_system,
            "mass_status": conn.mass_status.value,
            "life_status": conn.life_status.value,
        },
    )
    return conn


@router.delete(
    "/{connection_id}",
    summary="Delete a wormhole connection",
    description="Remove a wormhole connection (e.g., when it collapses).",
)
async def delete_wormhole(connection_id: str) -> dict[str, str]:
    """Delete a wormhole connection."""
    service = get_wormhole_service()
    # Get connection before deleting for broadcast
    conn = service.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Wormhole connection not found")

    await service.delete_connection(connection_id)

    # Broadcast map update to WebSocket clients
    await connection_manager.broadcast_wormhole_update(
        "deleted",
        {
            "id": connection_id,
            "from_system": conn.from_system,
            "to_system": conn.to_system,
        },
    )
    return {"status": "deleted", "connection_id": connection_id}


@router.get(
    "/system/{system_name}",
    summary="Get wormholes for a system",
    description="Returns all wormhole connections involving a specific system.",
)
async def get_system_wormholes(system_name: str) -> dict[str, Any]:
    """Get all wormhole connections for a system."""
    service = get_wormhole_service()
    connections = service.get_connections_for_system(system_name)
    return {
        "system": system_name,
        "count": len(connections),
        "connections": [conn.model_dump() for conn in connections],
    }


@router.get(
    "/stats",
    summary="Get wormhole service statistics",
    description="Returns statistics about the wormhole connection service.",
)
async def get_wormhole_stats() -> dict[str, Any]:
    """Get wormhole service statistics."""
    service = get_wormhole_service()
    return service.get_stats()
