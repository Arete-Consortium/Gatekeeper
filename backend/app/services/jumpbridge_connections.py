"""User-submitted jump bridge connection service.

Manages community-contributed Ansiblex jump bridge data with in-memory
cache backed by PostgreSQL persistence — same pattern as wormhole.py.

Key differences from wormholes:
- Jump bridges are permanent infrastructure (no expiry)
- Jump bridges are always bidirectional
- Jump bridges require nullsec systems (security <= 0.0, not wormhole space)
"""

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_session_factory
from ..db.models import JumpBridgeConnectionDB
from ..models.jumpbridge_connection import (
    JumpBridgeConnection,
    JumpBridgeConnectionCreate,
    JumpBridgeConnectionUpdate,
    JumpBridgeImportResponse,
    JumpBridgeStatus,
)
from .data_loader import load_universe

logger = logging.getLogger(__name__)

# Regex patterns for bridge separators, ordered by specificity.
# Each requires surrounding whitespace to avoid matching hyphens in system names.
_SEP_PATTERNS = [
    re.compile(r"^\s*(.+?)\s*\u00bb\s*(.+?)\s*$"),  # System A » System B
    re.compile(r"^\s*(.+?)\s*<->\s*(.+?)\s*$"),  # System A <-> System B
    re.compile(r"^\s*(.+?)\s*<>\s*(.+?)\s*$"),  # System A <> System B
    re.compile(r"^\s*(.+?)\s*-->\s*(.+?)\s*$"),  # System A --> System B
]


def _db_to_pydantic(row: JumpBridgeConnectionDB) -> JumpBridgeConnection:
    """Convert a database row to a Pydantic JumpBridgeConnection."""
    return JumpBridgeConnection(
        id=row.id,
        from_system=row.from_system,
        from_system_id=row.from_system_id,
        to_system=row.to_system,
        to_system_id=row.to_system_id,
        owner_alliance=row.owner_alliance,
        status=JumpBridgeStatus(row.status),
        created_at=row.created_at,
        created_by=row.created_by,
        notes=row.notes or "",
    )


def _pydantic_to_db(conn: JumpBridgeConnection) -> JumpBridgeConnectionDB:
    """Convert a Pydantic JumpBridgeConnection to a database row."""
    return JumpBridgeConnectionDB(
        id=conn.id,
        from_system=conn.from_system,
        from_system_id=conn.from_system_id,
        to_system=conn.to_system,
        to_system_id=conn.to_system_id,
        owner_alliance=conn.owner_alliance,
        status=conn.status.value,
        created_at=conn.created_at,
        created_by=conn.created_by,
        notes=conn.notes or None,
    )


class JumpBridgeConnectionService:
    """Manages user-submitted jump bridge connections.

    Features:
    - Add/update/delete jump bridge connections
    - Nullsec validation (bridges can only exist in nullsec/lowsec)
    - Bulk import from text paste
    - Integration with routing graph via get_active_bridges()
    - PostgreSQL persistence with in-memory cache
    """

    def __init__(self):
        self._connections: dict[str, JumpBridgeConnection] = {}
        self._by_system: dict[str, set[str]] = {}  # system name -> connection IDs
        self._total_added = 0

    def _generate_id(self) -> str:
        """Generate a unique connection ID."""
        return f"jb-{uuid.uuid4().hex[:12]}"

    def _index_connection(self, conn: JumpBridgeConnection) -> None:
        """Add connection to system index."""
        if conn.from_system not in self._by_system:
            self._by_system[conn.from_system] = set()
        self._by_system[conn.from_system].add(conn.id)

        if conn.to_system not in self._by_system:
            self._by_system[conn.to_system] = set()
        self._by_system[conn.to_system].add(conn.id)

    def _remove_from_index(self, conn: JumpBridgeConnection) -> None:
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

    def _get_system_id(self, system_name: str) -> int:
        """Look up system ID from universe data."""
        universe = load_universe()
        system = universe.systems.get(system_name)
        if system is None:
            return 0
        return system.id

    def _validate_system_for_bridge(self, system_name: str) -> str | None:
        """Validate a system is eligible for an Ansiblex bridge.

        Returns an error message if invalid, None if valid.
        Ansiblex bridges cannot be anchored in highsec or wormhole space.
        """
        universe = load_universe()
        system = universe.systems.get(system_name)
        if system is None:
            return f"Unknown system: {system_name}"
        if system.category == "highsec":
            return f"{system_name} is highsec (security {system.security:.1f}) - Ansiblex cannot be anchored"
        if system.category == "wh":
            return f"{system_name} is wormhole space - Ansiblex cannot be anchored"
        return None

    async def load_from_db(self) -> int:
        """Load connections from the database on startup.

        Returns:
            Number of connections loaded
        """
        session = await self._get_session()
        try:
            result = await session.execute(select(JumpBridgeConnectionDB))
            rows = result.scalars().all()

            self._connections.clear()
            self._by_system.clear()

            for row in rows:
                conn = _db_to_pydantic(row)
                self._connections[conn.id] = conn
                self._index_connection(conn)

            logger.info(f"Loaded {len(self._connections)} jump bridge connections from database")
            return len(self._connections)

        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def add_connection(
        self,
        data: JumpBridgeConnectionCreate,
        created_by: str | None = None,
    ) -> JumpBridgeConnection:
        """Add a new jump bridge connection.

        Args:
            data: Connection details
            created_by: Character name who added the connection

        Returns:
            Created JumpBridgeConnection

        Raises:
            ValueError: If validation fails
        """
        # Validate systems
        if data.from_system == data.to_system:
            raise ValueError("Cannot connect system to itself")

        for system_name in [data.from_system, data.to_system]:
            error = self._validate_system_for_bridge(system_name)
            if error:
                raise ValueError(error)

        # Check for duplicate (bidirectional — check both directions)
        for existing in self._connections.values():
            if (
                existing.from_system == data.from_system and existing.to_system == data.to_system
            ) or (
                existing.from_system == data.to_system and existing.to_system == data.from_system
            ):
                raise ValueError(
                    f"Bridge already exists: {data.from_system} \u00bb {data.to_system}"
                )

        from_system_id = self._get_system_id(data.from_system)
        to_system_id = self._get_system_id(data.to_system)

        conn = JumpBridgeConnection(
            id=self._generate_id(),
            from_system=data.from_system,
            from_system_id=from_system_id,
            to_system=data.to_system,
            to_system_id=to_system_id,
            owner_alliance=data.owner_alliance,
            status=JumpBridgeStatus.UNKNOWN,
            created_at=datetime.now(UTC),
            created_by=created_by,
            notes=data.notes,
        )

        # Persist to database
        db_row = _pydantic_to_db(conn)
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
            "Jump bridge connection added",
            extra={
                "connection_id": conn.id,
                "from": conn.from_system,
                "to": conn.to_system,
                "created_by": created_by,
            },
        )

        return conn

    async def update_connection(
        self,
        connection_id: str,
        data: JumpBridgeConnectionUpdate,
    ) -> JumpBridgeConnection | None:
        """Update an existing jump bridge connection.

        Args:
            connection_id: Connection ID to update
            data: Fields to update

        Returns:
            Updated connection or None if not found
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return None

        updates: dict[str, Any] = {}

        if data.status is not None:
            conn.status = data.status
            updates["status"] = data.status.value
        if data.owner_alliance is not None:
            conn.owner_alliance = data.owner_alliance
            updates["owner_alliance"] = data.owner_alliance
        if data.notes is not None:
            conn.notes = data.notes
            updates["notes"] = data.notes

        if updates:
            session = await self._get_session()
            try:
                await session.execute(
                    update(JumpBridgeConnectionDB)
                    .where(JumpBridgeConnectionDB.id == connection_id)
                    .values(**updates)
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

        logger.debug(f"Jump bridge connection updated: {connection_id}")
        return conn

    async def delete_connection(self, connection_id: str) -> bool:
        """Delete a jump bridge connection.

        Args:
            connection_id: Connection ID to delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return False

        session = await self._get_session()
        try:
            await session.execute(
                delete(JumpBridgeConnectionDB).where(JumpBridgeConnectionDB.id == connection_id)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

        self._remove_from_index(conn)
        del self._connections[connection_id]

        logger.info(f"Jump bridge connection deleted: {connection_id}")
        return True

    def get_connection(self, connection_id: str) -> JumpBridgeConnection | None:
        """Get a specific connection by ID."""
        return self._connections.get(connection_id)

    def get_all_connections(self) -> list[JumpBridgeConnection]:
        """Get all connections."""
        return list(self._connections.values())

    def get_connections_for_system(self, system_name: str) -> list[JumpBridgeConnection]:
        """Get all connections involving a specific system."""
        conn_ids = self._by_system.get(system_name, set())
        return [self._connections[cid] for cid in conn_ids if cid in self._connections]

    def get_active_bridges(self) -> list[JumpBridgeConnection]:
        """Get active bridge connections for routing integration.

        Returns connections that are not offline.
        """
        return [
            conn for conn in self._connections.values() if conn.status != JumpBridgeStatus.OFFLINE
        ]

    def parse_import_text(self, text: str) -> tuple[list[JumpBridgeConnectionCreate], list[str]]:
        """Parse bulk import text into bridge creation requests.

        Supported formats (one per line):
        - "System A \u00bb System B" (standard EVE format)
        - "System A <-> System B"
        - "System A --> System B"
        - "System A - System B"

        Lines starting with # are ignored as comments.
        Blank lines are skipped.

        Returns:
            Tuple of (parsed create requests, error messages)
        """
        universe = load_universe()
        creates: list[JumpBridgeConnectionCreate] = []
        errors: list[str] = []
        seen: set[tuple[str, str]] = set()

        # Also track existing bridges to avoid duplicates
        for existing in self._connections.values():
            key = tuple(sorted([existing.from_system, existing.to_system]))
            seen.add(key)

        for line_num, line in enumerate(text.strip().split("\n"), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Try each separator pattern
            sys1 = None
            sys2 = None
            for pattern in _SEP_PATTERNS:
                match = pattern.match(line)
                if match:
                    sys1 = match.group(1).strip()
                    sys2 = match.group(2).strip()
                    break

            if sys1 is None or sys2 is None or not sys1 or not sys2:
                errors.append(f"Line {line_num}: Could not parse '{line}'")
                continue

            # Validate systems exist
            if sys1 not in universe.systems:
                errors.append(f"Line {line_num}: Unknown system '{sys1}'")
                continue
            if sys2 not in universe.systems:
                errors.append(f"Line {line_num}: Unknown system '{sys2}'")
                continue

            # Validate not highsec/wh
            for sname in [sys1, sys2]:
                err = self._validate_system_for_bridge(sname)
                if err:
                    errors.append(f"Line {line_num}: {err}")
                    break
            else:
                # No validation errors — check duplicate
                key = tuple(sorted([sys1, sys2]))
                if key in seen:
                    continue  # silently skip duplicates

                seen.add(key)
                creates.append(
                    JumpBridgeConnectionCreate(
                        from_system=sys1,
                        to_system=sys2,
                    )
                )

        return creates, errors

    async def import_bridges(
        self,
        text: str,
        created_by: str | None = None,
    ) -> JumpBridgeImportResponse:
        """Bulk import jump bridges from text paste.

        Args:
            text: Raw text with one bridge per line
            created_by: Character name who performed the import

        Returns:
            Import result with counts, errors, and created bridges
        """
        creates, errors = self.parse_import_text(text)

        bridges: list[JumpBridgeConnection] = []
        skipped = 0

        for create in creates:
            try:
                conn = await self.add_connection(create, created_by=created_by)
                bridges.append(conn)
            except ValueError as e:
                # Duplicate or validation error during add
                skipped += 1
                errors.append(str(e))

        return JumpBridgeImportResponse(
            imported=len(bridges),
            skipped=skipped,
            errors=errors,
            bridges=bridges,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get jump bridge service statistics."""
        status_counts: dict[str, int] = {}
        for conn in self._connections.values():
            status_counts[conn.status.value] = status_counts.get(conn.status.value, 0) + 1

        return {
            "active_connections": len(self._connections),
            "systems_with_bridges": len(self._by_system),
            "total_added": self._total_added,
            "connections_by_status": status_counts,
        }

    async def clear_all(self) -> int:
        """Clear all connections (for testing/admin)."""
        count = len(self._connections)
        self._connections.clear()
        self._by_system.clear()

        session = await self._get_session()
        try:
            await session.execute(delete(JumpBridgeConnectionDB))
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

        logger.info(f"Cleared {count} jump bridge connections")
        return count


# Global instance
_jumpbridge_connection_service: JumpBridgeConnectionService | None = None


def get_jumpbridge_connection_service() -> JumpBridgeConnectionService:
    """Get or create the jump bridge connection service instance."""
    global _jumpbridge_connection_service
    if _jumpbridge_connection_service is None:
        _jumpbridge_connection_service = JumpBridgeConnectionService()
    return _jumpbridge_connection_service
