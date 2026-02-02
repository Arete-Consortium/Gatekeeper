"""Wormhole connection service for user-submitted wormhole routes.

Since EVE's ESI doesn't track dynamic wormholes (they require scanning),
this service provides user-submitted wormhole connection management
similar to tools like Tripwire or Pathfinder.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ..models.wormhole import (
    WormholeConnection,
    WormholeConnectionCreate,
    WormholeConnectionUpdate,
    WormholeLife,
    WormholeMass,
    WormholeType,
)
from .data_loader import load_universe

logger = logging.getLogger(__name__)

# Default wormhole lifetimes in hours
DEFAULT_LIFETIME_HOURS = 16  # Standard K162
FRIGATE_LIFETIME_HOURS = 4  # Frigate holes
EOL_THRESHOLD_HOURS = 4  # Mark as EOL when < 4 hours remaining


class WormholeService:
    """Manages user-submitted wormhole connections.

    Features:
    - Add/update/delete wormhole connections
    - Automatic expiry tracking
    - Integration with routing graph
    - Per-system and global queries
    """

    def __init__(self):
        # In-memory storage (could be backed by Redis/DB)
        self._connections: dict[str, WormholeConnection] = {}
        self._by_system: dict[str, set[str]] = {}  # system -> connection IDs

        # Stats
        self._total_added = 0
        self._total_expired = 0

    def _generate_id(self) -> str:
        """Generate a unique connection ID."""
        return f"wh-{uuid.uuid4().hex[:12]}"

    def _index_connection(self, conn: WormholeConnection) -> None:
        """Add connection to system index."""
        if conn.from_system not in self._by_system:
            self._by_system[conn.from_system] = set()
        self._by_system[conn.from_system].add(conn.id)

        if conn.to_system not in self._by_system:
            self._by_system[conn.to_system] = set()
        self._by_system[conn.to_system].add(conn.id)

    def _remove_from_index(self, conn: WormholeConnection) -> None:
        """Remove connection from system index."""
        if conn.from_system in self._by_system:
            self._by_system[conn.from_system].discard(conn.id)
            if not self._by_system[conn.from_system]:
                del self._by_system[conn.from_system]

        if conn.to_system in self._by_system:
            self._by_system[conn.to_system].discard(conn.id)
            if not self._by_system[conn.to_system]:
                del self._by_system[conn.to_system]

    def add_connection(
        self,
        data: WormholeConnectionCreate,
        created_by: str | None = None,
    ) -> WormholeConnection:
        """Add a new wormhole connection.

        Args:
            data: Connection details
            created_by: Character name who added the connection

        Returns:
            Created WormholeConnection
        """
        universe = load_universe()

        # Validate systems
        if data.from_system not in universe.systems:
            raise ValueError(f"Unknown system: {data.from_system}")
        if data.to_system not in universe.systems:
            raise ValueError(f"Unknown system: {data.to_system}")
        if data.from_system == data.to_system:
            raise ValueError("Cannot connect system to itself")

        # Calculate expiry
        expires_at = None
        if data.expires_hours is not None:
            expires_at = datetime.now(UTC) + timedelta(hours=data.expires_hours)
        elif data.wormhole_type == WormholeType.FRIGATE:
            expires_at = datetime.now(UTC) + timedelta(hours=FRIGATE_LIFETIME_HOURS)
        else:
            expires_at = datetime.now(UTC) + timedelta(hours=DEFAULT_LIFETIME_HOURS)

        conn = WormholeConnection(
            id=self._generate_id(),
            from_system=data.from_system,
            to_system=data.to_system,
            wormhole_type=data.wormhole_type,
            mass_status=data.mass_status,
            life_status=data.life_status,
            bidirectional=data.bidirectional,
            created_at=datetime.now(UTC),
            created_by=created_by,
            expires_at=expires_at,
            notes=data.notes,
            from_sig=data.from_sig,
            to_sig=data.to_sig,
        )

        self._connections[conn.id] = conn
        self._index_connection(conn)
        self._total_added += 1

        logger.info(
            "Wormhole connection added",
            extra={
                "connection_id": conn.id,
                "from": conn.from_system,
                "to": conn.to_system,
                "type": conn.wormhole_type.value,
                "created_by": created_by,
            },
        )

        return conn

    def update_connection(
        self,
        connection_id: str,
        data: WormholeConnectionUpdate,
    ) -> WormholeConnection | None:
        """Update an existing wormhole connection.

        Args:
            connection_id: Connection ID to update
            data: Fields to update

        Returns:
            Updated connection or None if not found
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return None

        if data.mass_status is not None:
            conn.mass_status = data.mass_status
        if data.life_status is not None:
            conn.life_status = data.life_status
        if data.notes is not None:
            conn.notes = data.notes
        if data.from_sig is not None:
            conn.from_sig = data.from_sig
        if data.to_sig is not None:
            conn.to_sig = data.to_sig
        if data.expires_hours is not None:
            conn.expires_at = datetime.now(UTC) + timedelta(hours=data.expires_hours)

        logger.debug(f"Wormhole connection updated: {connection_id}")
        return conn

    def delete_connection(self, connection_id: str) -> bool:
        """Delete a wormhole connection.

        Args:
            connection_id: Connection ID to delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return False

        self._remove_from_index(conn)
        del self._connections[connection_id]

        logger.info(f"Wormhole connection deleted: {connection_id}")
        return True

    def get_connection(self, connection_id: str) -> WormholeConnection | None:
        """Get a specific connection by ID."""
        return self._connections.get(connection_id)

    def get_all_connections(self) -> list[WormholeConnection]:
        """Get all active (non-expired) connections."""
        self._cleanup_expired()
        return list(self._connections.values())

    def get_connections_for_system(self, system_name: str) -> list[WormholeConnection]:
        """Get all connections involving a specific system."""
        self._cleanup_expired()
        conn_ids = self._by_system.get(system_name, set())
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    def get_active_wormholes(self) -> list[WormholeConnection]:
        """Get active wormhole connections for routing integration.

        Returns connections that are:
        - Not expired
        - Not critical mass (too risky)
        """
        self._cleanup_expired()
        active = []
        for conn in self._connections.values():
            # Skip critical mass holes
            if conn.mass_status == WormholeMass.CRITICAL:
                continue
            active.append(conn)
        return active

    def _cleanup_expired(self) -> int:
        """Remove expired connections.

        Returns:
            Number of connections removed
        """
        now = datetime.now(UTC)
        expired_ids = []

        for conn_id, conn in self._connections.items():
            if conn.expires_at and conn.expires_at < now:
                expired_ids.append(conn_id)
            elif conn.life_status == WormholeLife.EOL:
                # Mark EOL holes as expired after 4 hours
                if conn.created_at + timedelta(hours=EOL_THRESHOLD_HOURS) < now:
                    expired_ids.append(conn_id)

        for conn_id in expired_ids:
            conn = self._connections.get(conn_id)
            if conn:
                self._remove_from_index(conn)
                del self._connections[conn_id]
                self._total_expired += 1

        if expired_ids:
            logger.debug(f"Cleaned up {len(expired_ids)} expired wormhole connections")

        return len(expired_ids)

    def get_stats(self) -> dict[str, Any]:
        """Get wormhole service statistics."""
        self._cleanup_expired()
        return {
            "active_connections": len(self._connections),
            "systems_with_wormholes": len(self._by_system),
            "total_added": self._total_added,
            "total_expired": self._total_expired,
            "connections_by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> dict[str, int]:
        """Count connections by wormhole type."""
        counts: dict[str, int] = {}
        for conn in self._connections.values():
            type_name = conn.wormhole_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def clear_all(self) -> int:
        """Clear all connections (for testing/admin)."""
        count = len(self._connections)
        self._connections.clear()
        self._by_system.clear()
        logger.info(f"Cleared {count} wormhole connections")
        return count


# Global instance
_wormhole_service: WormholeService | None = None


def get_wormhole_service() -> WormholeService:
    """Get or create the wormhole service instance."""
    global _wormhole_service
    if _wormhole_service is None:
        _wormhole_service = WormholeService()
    return _wormhole_service
