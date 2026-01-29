"""WebSocket endpoints for real-time updates."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...services.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/killfeed")
async def killfeed_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time kill feed.

    Connect to receive kills as they happen. Send a JSON message to configure filters:

    ```json
    {
        "type": "subscribe",
        "systems": [30000142, 30002187],  // Optional: System IDs to watch
        "regions": [10000002],             // Optional: Region IDs to watch
        "min_value": 1000000,              // Optional: Minimum ISK value
        "include_pods": true               // Optional: Include pod kills (default: true)
    }
    ```

    Kill events are sent as:
    ```json
    {
        "type": "kill",
        "data": {
            "kill_id": 123456789,
            "solar_system_id": 30000142,
            "solar_system_name": "Jita",
            "region_id": 10000002,
            "kill_time": "2025-01-01T12:00:00Z",
            "ship_type_id": 670,
            "is_pod": true,
            "total_value": 50000000,
            "risk_score": 0.85,
            ...
        }
    }
    ```
    """
    client_id = str(uuid.uuid4())

    try:
        await connection_manager.connect(client_id, websocket)
        logger.info(
            "WebSocket client connected",
            extra={
                "client_id": client_id,
                "active_connections": connection_manager.connection_count,
            },
        )

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connected",
                "client_id": client_id,
                "message": "Connected to EVE Gatekeeper kill feed",
                "active_connections": connection_manager.connection_count,
            }
        )

        # Listen for messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_client_message(client_id, data, websocket)
            except ValueError:
                # Invalid JSON
                logger.warning("WebSocket received invalid JSON", extra={"client_id": client_id})
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "Invalid JSON message",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.exception(f"WebSocket error for client {client_id}: {e}")
    finally:
        await connection_manager.disconnect(client_id)


async def handle_client_message(
    client_id: str,
    data: dict[str, Any],
    websocket: WebSocket,
) -> None:
    """Handle incoming messages from WebSocket clients."""
    message_type = data.get("type")

    if message_type == "subscribe":
        # Update subscription filters
        systems: list[int] | None = data.get("systems")
        regions: list[int] | None = data.get("regions")
        min_value: float | None = data.get("min_value")
        include_pods: bool | None = data.get("include_pods")

        success = await connection_manager.update_subscription(
            client_id,
            systems=systems,
            regions=regions,
            min_value=min_value,
            include_pods=include_pods,
        )

        if success:
            logger.debug(
                "WebSocket subscription updated",
                extra={
                    "client_id": client_id,
                    "systems_count": len(systems) if systems else 0,
                    "regions_count": len(regions) if regions else 0,
                },
            )
            await websocket.send_json(
                {
                    "type": "subscribed",
                    "filters": {
                        "systems": systems,
                        "regions": regions,
                        "min_value": min_value,
                        "include_pods": include_pods,
                    },
                }
            )
        else:
            logger.warning("WebSocket subscription update failed", extra={"client_id": client_id})
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Failed to update subscription",
                }
            )

    elif message_type == "ping":
        await websocket.send_json({"type": "pong"})

    elif message_type == "status":
        stats = connection_manager.get_stats()
        await websocket.send_json(
            {
                "type": "status",
                "data": stats,
            }
        )

    else:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "valid_types": ["subscribe", "ping", "status"],
            }
        )
