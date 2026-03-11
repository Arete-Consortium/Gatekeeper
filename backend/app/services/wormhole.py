"""Wormhole connection service for user-submitted wormhole routes.

Since EVE's ESI doesn't track dynamic wormholes (they require scanning),
this service provides user-submitted wormhole connection management
similar to tools like Tripwire or Pathfinder.

Persistence: All connections are stored in PostgreSQL via SQLAlchemy async sessions.
An in-memory cache is maintained for fast reads and routing integration.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_session_factory
from ..db.models import WormholeConnectionDB
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


def _db_to_pydantic(row: WormholeConnectionDB) -> WormholeConnection:
    """Convert a database row to a Pydantic WormholeConnection."""
    return WormholeConnection(
        id=row.id,
        from_system=row.from_system,
        to_system=row.to_system,
        wormhole_type=WormholeType(row.wormhole_type),
        mass_status=WormholeMass(row.mass_status),
        life_status=WormholeLife(row.life_status),
        bidirectional=row.bidirectional,
        created_at=row.created_at,
        created_by=row.created_by,
        expires_at=row.expires_at,
        notes=row.notes or "",
        from_sig=row.from_sig or "",
        to_sig=row.to_sig or "",
    )


def _pydantic_to_db(
    conn: WormholeConnection,
    from_system_id: int,
    to_system_id: int,
    max_lifetime_hours: float,
) -> WormholeConnectionDB:
    """Convert a Pydantic WormholeConnection to a database row."""
    return WormholeConnectionDB(
        id=conn.id,
        from_system=conn.from_system,
        from_system_id=from_system_id,
        to_system=conn.to_system,
        to_system_id=to_system_id,
        wormhole_type=conn.wormhole_type.value,
        mass_status=conn.mass_status.value,
        life_status=conn.life_status.value,
        bidirectional=conn.bidirectional,
        max_lifetime_hours=max_lifetime_hours,
        created_at=conn.created_at,
        expires_at=conn.expires_at,
        created_by=conn.created_by,
        notes=conn.notes or None,
        from_sig=conn.from_sig or "",
        to_sig=conn.to_sig or "",
    )


class WormholeService:
    """Manages user-submitted wormhole connections.

    Features:
    - Add/update/delete wormhole connections
    - Automatic expiry tracking
    - Integration with routing graph
    - Per-system and global queries
    - PostgreSQL persistence with in-memory cache
    """

    def __init__(self):
        # In-memory cache for fast reads (populated from DB on startup)
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

    async def _get_session(self) -> AsyncSession:
        """Get a new async session."""
        factory = get_session_factory()
        return factory()

    async def load_from_db(self) -> int:
        """Load active (non-expired) connections from the database on startup.

        Returns:
            Number of connections loaded
        """
        session = await self._get_session()
        try:
            now = datetime.now(UTC)
            # Fetch non-expired connections
            result = await session.execute(
                select(WormholeConnectionDB).where(
                    (WormholeConnectionDB.expires_at.is_(None))
                    | (WormholeConnectionDB.expires_at > now)
                )
            )
            rows = result.scalars().all()

            # Clear existing cache
            self._connections.clear()
            self._by_system.clear()

            for row in rows:
                conn = _db_to_pydantic(row)
                self._connections[conn.id] = conn
                self._index_connection(conn)

            # Clean up expired rows in DB while we're at it
            await session.execute(
                delete(WormholeConnectionDB).where(
                    WormholeConnectionDB.expires_at.isnot(None),
                    WormholeConnectionDB.expires_at <= now,
                )
            )
            await session.commit()

            logger.info(f"Loaded {len(self._connections)} wormhole connections from database")
            return len(self._connections)

        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def _get_system_id(self, system_name: str) -> int:
        """Look up system ID from universe data."""
        universe = load_universe()
        system = universe.systems.get(system_name)
        if system is None:
            return 0
        return system.id

    async def add_connection(
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

        # Calculate expiry and lifetime
        if data.expires_hours is not None:
            max_lifetime_hours = data.expires_hours
            expires_at = datetime.now(UTC) + timedelta(hours=data.expires_hours)
        elif data.wormhole_type == WormholeType.FRIGATE:
            max_lifetime_hours = FRIGATE_LIFETIME_HOURS
            expires_at = datetime.now(UTC) + timedelta(hours=FRIGATE_LIFETIME_HOURS)
        else:
            max_lifetime_hours = DEFAULT_LIFETIME_HOURS
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

        # Persist to database
        from_system_id = self._get_system_id(data.from_system)
        to_system_id = self._get_system_id(data.to_system)
        db_row = _pydantic_to_db(conn, from_system_id, to_system_id, max_lifetime_hours)

        session = await self._get_session()
        try:
            session.add(db_row)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

        # Update in-memory cache
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

    async def update_connection(
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

        # Build update dict for database
        updates: dict[str, Any] = {}

        if data.mass_status is not None:
            conn.mass_status = data.mass_status
            updates["mass_status"] = data.mass_status.value
        if data.life_status is not None:
            conn.life_status = data.life_status
            updates["life_status"] = data.life_status.value
        if data.notes is not None:
            conn.notes = data.notes
            updates["notes"] = data.notes
        if data.from_sig is not None:
            conn.from_sig = data.from_sig
            updates["from_sig"] = data.from_sig
        if data.to_sig is not None:
            conn.to_sig = data.to_sig
            updates["to_sig"] = data.to_sig
        if data.expires_hours is not None:
            new_expires = datetime.now(UTC) + timedelta(hours=data.expires_hours)
            conn.expires_at = new_expires
            updates["expires_at"] = new_expires
            updates["max_lifetime_hours"] = data.expires_hours

        if updates:
            session = await self._get_session()
            try:
                await session.execute(
                    update(WormholeConnectionDB)
                    .where(WormholeConnectionDB.id == connection_id)
                    .values(**updates)
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

        logger.debug(f"Wormhole connection updated: {connection_id}")
        return conn

    async def delete_connection(self, connection_id: str) -> bool:
        """Delete a wormhole connection.

        Args:
            connection_id: Connection ID to delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return False

        # Remove from database
        session = await self._get_session()
        try:
            await session.execute(
                delete(WormholeConnectionDB).where(
                    WormholeConnectionDB.id == connection_id
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

        # Remove from cache
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
        """Remove expired connections from in-memory cache.

        Note: DB cleanup happens during load_from_db() and periodically.
        This only cleans the in-memory cache for fast reads.

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
            conn = self._connections.pop(conn_id, None)  # type: ignore[arg-type]
            if conn is not None:
                self._remove_from_index(conn)
                self._total_expired += 1

        if expired_ids:
            logger.debug(f"Cleaned up {len(expired_ids)} expired wormhole connections")

        return len(expired_ids)

    async def cleanup_expired_db(self) -> int:
        """Remove expired connections from the database.

        Can be called periodically or on demand.

        Returns:
            Number of rows deleted
        """
        now = datetime.now(UTC)
        session = await self._get_session()
        try:
            result = await session.execute(
                delete(WormholeConnectionDB).where(
                    WormholeConnectionDB.expires_at.isnot(None),
                    WormholeConnectionDB.expires_at <= now,
                )
            )
            await session.commit()
            count = result.rowcount  # type: ignore[union-attr]
            if count:
                logger.debug(f"Cleaned up {count} expired wormhole connections from DB")
            return count
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

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

    async def clear_all(self) -> int:
        """Clear all connections (for testing/admin)."""
        count = len(self._connections)
        self._connections.clear()
        self._by_system.clear()

        # Clear from database
        session = await self._get_session()
        try:
            await session.execute(delete(WormholeConnectionDB))
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

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
