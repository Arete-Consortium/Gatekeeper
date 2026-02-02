"""WebSocket connection manager for real-time updates."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class ClientSubscription:
    """Represents a client's subscription filters."""

    systems: set[int] = field(default_factory=set)  # System IDs to watch
    regions: set[int] = field(default_factory=set)  # Region IDs to watch
    min_value: float = 0  # Minimum ISK value to receive
    include_pods: bool = True


@dataclass
class ConnectedClient:
    """Represents a connected WebSocket client."""

    websocket: WebSocket
    subscription: ClientSubscription = field(default_factory=ClientSubscription)
    connected_at: float = 0


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self._clients: dict[str, ConnectedClient] = {}
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self._clients)

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        import time

        async with self._lock:
            self._clients[client_id] = ConnectedClient(
                websocket=websocket,
                connected_at=time.time(),
            )
        logger.info(f"Client {client_id} connected. Total clients: {self.connection_count}")

    async def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
        logger.info(f"Client {client_id} disconnected. Total clients: {self.connection_count}")

    async def update_subscription(
        self,
        client_id: str,
        systems: list[int] | None = None,
        regions: list[int] | None = None,
        min_value: float | None = None,
        include_pods: bool | None = None,
    ) -> bool:
        """Update a client's subscription filters."""
        async with self._lock:
            if client_id not in self._clients:
                return False

            client = self._clients[client_id]
            if systems is not None:
                client.subscription.systems = set(systems)
            if regions is not None:
                client.subscription.regions = set(regions)
            if min_value is not None:
                client.subscription.min_value = min_value
            if include_pods is not None:
                client.subscription.include_pods = include_pods

        logger.debug(f"Updated subscription for client {client_id}")
        return True

    def _matches_filter(self, kill_data: dict[str, Any], subscription: ClientSubscription) -> bool:
        """Check if a kill matches a client's subscription filters."""
        # If no filters are set, match everything
        if not subscription.systems and not subscription.regions:
            return True

        system_id = kill_data.get("solar_system_id")
        region_id = kill_data.get("region_id")

        # Check system filter
        if subscription.systems and system_id in subscription.systems:
            return True

        # Check region filter
        if subscription.regions and region_id in subscription.regions:
            return True

        # No match
        if subscription.systems or subscription.regions:
            return False

        return True

    async def send_to_client(self, client_id: str, message: dict[str, Any]) -> bool:
        """Send a message to a specific client."""
        async with self._lock:
            if client_id not in self._clients:
                return False
            client = self._clients[client_id]

        try:
            await client.websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> int:
        """Broadcast a message to all connected clients."""
        sent_count = 0
        disconnected: list[str] = []

        async with self._lock:
            clients = list(self._clients.items())

        for client_id, client in clients:
            try:
                await client.websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast to client {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

        return sent_count

    async def broadcast_kill(self, kill_data: dict[str, Any]) -> int:
        """Broadcast a kill to clients that match the filters."""
        sent_count = 0
        disconnected: list[str] = []

        async with self._lock:
            clients = list(self._clients.items())

        for client_id, client in clients:
            # Check if kill matches client's filters
            if not self._matches_filter(kill_data, client.subscription):
                continue

            # Check pod filter
            is_pod = kill_data.get("is_pod", False)
            if is_pod and not client.subscription.include_pods:
                continue

            # Check value filter
            total_value = kill_data.get("total_value", 0) or 0
            if total_value < client.subscription.min_value:
                continue

            try:
                await client.websocket.send_json(
                    {
                        "type": "kill",
                        "data": kill_data,
                    }
                )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send kill to client {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

        return sent_count

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "active_connections": self.connection_count,
            "clients": [
                {
                    "id": client_id,
                    "systems_filter_count": len(client.subscription.systems),
                    "regions_filter_count": len(client.subscription.regions),
                }
                for client_id, client in self._clients.items()
            ],
        }

    async def broadcast_map_update(self, update_type: str, data: dict[str, Any]) -> int:
        """Broadcast a map update to all connected clients.

        Args:
            update_type: Type of update ('system_risk', 'wormhole', 'bridge', etc.)
            data: Update data

        Returns:
            Number of clients notified
        """
        message = {
            "type": "map_update",
            "update_type": update_type,
            "data": data,
        }
        return await self.broadcast(message)

    async def broadcast_system_risk_update(
        self,
        system_id: int,
        system_name: str,
        risk_score: float,
        recent_kills: int,
    ) -> int:
        """Broadcast a system risk score update."""
        return await self.broadcast_map_update(
            "system_risk",
            {
                "system_id": system_id,
                "system_name": system_name,
                "risk_score": risk_score,
                "recent_kills": recent_kills,
            },
        )

    async def broadcast_wormhole_update(
        self,
        action: str,  # 'added', 'updated', 'deleted'
        wormhole_data: dict[str, Any],
    ) -> int:
        """Broadcast a wormhole connection update."""
        return await self.broadcast_map_update(
            "wormhole",
            {
                "action": action,
                **wormhole_data,
            },
        )


# Global connection manager instance
connection_manager = ConnectionManager()
