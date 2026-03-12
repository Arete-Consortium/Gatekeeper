"""Kill history service for storing and aging kill data.

Provides a rolling window of recent kills with configurable retention.
Kills are automatically aged out based on time and maximum entry count.
Persists to PostgreSQL — loads on startup, write-through on add.
"""

import asyncio
import logging
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select

from ..core.config import settings
from ..db.database import get_session_factory
from ..db.models import KillHistoryRecord

logger = logging.getLogger(__name__)


class KillHistory:
    """Stores recent kill data with automatic aging.

    Features:
    - Time-based expiration (configurable max age)
    - Size-based limits (configurable max entries)
    - Background cleanup task
    - Per-system and per-region indexing for efficient queries
    - PostgreSQL persistence (write-through, loaded on startup)
    """

    def __init__(
        self,
        max_age_hours: int | None = None,
        max_entries: int | None = None,
        cleanup_interval_minutes: int | None = None,
    ):
        self._max_age_hours = max_age_hours or settings.KILL_HISTORY_MAX_AGE_HOURS
        self._max_entries = max_entries or settings.KILL_HISTORY_MAX_ENTRIES
        self._cleanup_interval = (
            cleanup_interval_minutes or settings.KILL_HISTORY_CLEANUP_INTERVAL_MINUTES
        )

        # Main storage - OrderedDict to maintain insertion order
        self._kills: OrderedDict[int, dict[str, Any]] = OrderedDict()

        # Indexes for efficient queries
        self._by_system: dict[int, set[int]] = {}  # system_id -> set of kill_ids
        self._by_region: dict[int, set[int]] = {}  # region_id -> set of kill_ids

        # Background task
        self._running = False
        self._cleanup_task: asyncio.Task | None = None

        # Stats
        self._total_received = 0
        self._total_expired = 0
        self._total_evicted = 0

    @property
    def count(self) -> int:
        """Get the number of stored kills."""
        return len(self._kills)

    @property
    def max_age_hours(self) -> int:
        """Get the configured max age in hours."""
        return self._max_age_hours

    @property
    def max_entries(self) -> int:
        """Get the configured max entries."""
        return self._max_entries

    async def start(self) -> None:
        """Start the background cleanup task and load persisted kills."""
        if self._running:
            logger.warning("Kill history already running")
            return

        self._running = True
        if settings.KILL_HISTORY_ENABLED:
            await self._load_from_db()
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info(
                "Kill history started",
                extra={
                    "max_age_hours": self._max_age_hours,
                    "max_entries": self._max_entries,
                    "cleanup_interval_minutes": self._cleanup_interval,
                    "loaded_kills": self.count,
                },
            )
        else:
            logger.info("Kill history disabled by configuration")

    async def stop(self) -> None:
        """Stop the background cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("Kill history stopped")

    async def _load_from_db(self) -> None:
        """Load recent kills from database into in-memory cache."""
        try:
            cutoff = datetime.now(UTC) - timedelta(hours=self._max_age_hours)
            factory = get_session_factory()
            async with factory() as session:
                result = await session.execute(
                    select(KillHistoryRecord)
                    .where(KillHistoryRecord.received_at >= cutoff)
                    .order_by(KillHistoryRecord.received_at.asc())
                    .limit(self._max_entries)
                )
                rows = result.scalars().all()
                for row in rows:
                    kill_data = row.data
                    kill_id = row.kill_id
                    self._kills[kill_id] = kill_data
                    # Rebuild indexes
                    system_id = kill_data.get("solar_system_id")
                    if system_id:
                        self._by_system.setdefault(system_id, set()).add(kill_id)
                    region_id = kill_data.get("region_id")
                    if region_id:
                        self._by_region.setdefault(region_id, set()).add(kill_id)
                logger.info(f"Loaded {len(rows)} kills from database")
        except Exception as e:
            logger.warning(f"Could not load kill history from DB: {e}")

    async def _persist_kill(self, kill_id: int, kill_data: dict[str, Any]) -> None:
        """Persist a single kill to the database."""
        try:
            received_str = kill_data.get("received_at", datetime.now(UTC).isoformat())
            received_at = datetime.fromisoformat(received_str.replace("Z", "+00:00"))

            record = KillHistoryRecord(
                kill_id=kill_id,
                system_id=kill_data.get("solar_system_id", 0),
                region_id=kill_data.get("region_id"),
                total_value=kill_data.get("total_value"),
                is_pod=kill_data.get("is_pod", False),
                received_at=received_at,
                data=kill_data,
            )
            factory = get_session_factory()
            async with factory() as session:
                await session.merge(record)
                await session.commit()
        except Exception as e:
            logger.debug(f"Could not persist kill {kill_id}: {e}")

    async def _delete_expired_from_db(self, cutoff: datetime) -> int:
        """Delete expired kills from the database."""
        try:
            factory = get_session_factory()
            async with factory() as session:
                result = await session.execute(
                    delete(KillHistoryRecord).where(KillHistoryRecord.received_at < cutoff)
                )
                await session.commit()
                return result.rowcount  # type: ignore[return-value]
        except Exception as e:
            logger.debug(f"Could not delete expired kills from DB: {e}")
            return 0

    def add_kill(self, kill_data: dict[str, Any]) -> bool:
        """Add a kill to the history.

        Args:
            kill_data: Kill data dict with at least 'kill_id', 'solar_system_id',
                      and optionally 'region_id' and 'received_at'.

        Returns:
            True if added, False if duplicate or disabled.
        """
        if not settings.KILL_HISTORY_ENABLED:
            return False

        kill_id = kill_data.get("kill_id")
        if kill_id is None:
            logger.warning("Kill data missing kill_id, skipping")
            return False

        # Skip duplicates
        if kill_id in self._kills:
            return False

        # Ensure received_at timestamp
        if "received_at" not in kill_data:
            kill_data["received_at"] = datetime.now(UTC).isoformat()

        # Store the kill
        self._kills[kill_id] = kill_data
        self._total_received += 1

        # Update indexes
        system_id = kill_data.get("solar_system_id")
        if system_id:
            if system_id not in self._by_system:
                self._by_system[system_id] = set()
            self._by_system[system_id].add(kill_id)

        region_id = kill_data.get("region_id")
        if region_id:
            if region_id not in self._by_region:
                self._by_region[region_id] = set()
            self._by_region[region_id].add(kill_id)

        # Enforce size limit (evict oldest)
        while len(self._kills) > self._max_entries:
            self._evict_oldest()

        # Fire-and-forget DB persistence
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._persist_kill(kill_id, kill_data))
        except RuntimeError:
            pass  # No event loop — skip persistence (e.g., testing)

        return True

    def _evict_oldest(self) -> None:
        """Evict the oldest kill to enforce size limit."""
        if not self._kills:
            return

        # Get oldest (first item in OrderedDict)
        oldest_id = next(iter(self._kills))
        self._remove_kill(oldest_id)
        self._total_evicted += 1

    def _remove_kill(self, kill_id: int) -> None:
        """Remove a kill from storage and indexes."""
        if kill_id not in self._kills:
            return

        kill_data = self._kills[kill_id]

        # Remove from indexes
        system_id = kill_data.get("solar_system_id")
        if system_id and system_id in self._by_system:
            self._by_system[system_id].discard(kill_id)
            if not self._by_system[system_id]:
                del self._by_system[system_id]

        region_id = kill_data.get("region_id")
        if region_id and region_id in self._by_region:
            self._by_region[region_id].discard(kill_id)
            if not self._by_region[region_id]:
                del self._by_region[region_id]

        # Remove from main storage
        del self._kills[kill_id]

    def cleanup_expired(self) -> int:
        """Remove kills older than max_age_hours.

        Returns:
            Number of kills removed.
        """
        if not self._kills:
            return 0

        cutoff = datetime.now(UTC) - timedelta(hours=self._max_age_hours)
        expired: list[int] = []

        for kill_id, kill_data in self._kills.items():
            received_at_str = kill_data.get("received_at")
            if not received_at_str:
                continue

            try:
                received_at = datetime.fromisoformat(received_at_str.replace("Z", "+00:00"))
                if received_at < cutoff:
                    expired.append(kill_id)
            except (ValueError, TypeError):
                continue

        for kill_id in expired:
            self._remove_kill(kill_id)
            self._total_expired += 1

        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired kills")
            # Also clean DB
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._delete_expired_from_db(cutoff))
            except RuntimeError:
                pass

        return len(expired)

    async def _cleanup_loop(self) -> None:
        """Background loop for periodic cleanup."""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval * 60)
                if self._running:
                    removed = self.cleanup_expired()
                    if removed > 0:
                        logger.info(
                            "Kill history cleanup completed",
                            extra={"removed": removed, "remaining": self.count},
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in kill history cleanup: {e}")
                await asyncio.sleep(60)

    def get_recent(
        self,
        limit: int = 100,
        system_id: int | None = None,
        region_id: int | None = None,
        min_value: float | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent kills with optional filtering.

        Args:
            limit: Maximum number of kills to return.
            system_id: Filter by solar system ID.
            region_id: Filter by region ID.
            min_value: Minimum ISK value filter.

        Returns:
            List of kill data dicts, newest first.
        """
        # Determine which kill IDs to consider
        if system_id is not None:
            kill_ids = self._by_system.get(system_id, set())
        elif region_id is not None:
            kill_ids = self._by_region.get(region_id, set())
        else:
            kill_ids = set(self._kills.keys())

        # Filter and collect
        results: list[dict[str, Any]] = []
        for kill_id in reversed(list(self._kills.keys())):
            if kill_id not in kill_ids:
                continue

            kill_data = self._kills[kill_id]

            # Value filter
            if min_value is not None:
                value = kill_data.get("total_value") or 0
                if value < min_value:
                    continue

            results.append(kill_data)
            if len(results) >= limit:
                break

        return results

    def get_system_kills(self, system_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent kills for a specific system."""
        return self.get_recent(limit=limit, system_id=system_id)

    def get_region_kills(self, region_id: int, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent kills for a specific region."""
        return self.get_recent(limit=limit, region_id=region_id)

    def get_stats(self) -> dict[str, Any]:
        """Get kill history statistics."""
        return {
            "enabled": settings.KILL_HISTORY_ENABLED,
            "total_stored": self.count,
            "max_entries": self._max_entries,
            "max_age_hours": self._max_age_hours,
            "systems_tracked": len(self._by_system),
            "regions_tracked": len(self._by_region),
            "total_received": self._total_received,
            "total_expired": self._total_expired,
            "total_evicted": self._total_evicted,
            "cleanup_interval_minutes": self._cleanup_interval,
        }

    def clear(self) -> int:
        """Clear all stored kills.

        Returns:
            Number of kills cleared.
        """
        count = len(self._kills)
        self._kills.clear()
        self._by_system.clear()
        self._by_region.clear()
        logger.info(f"Kill history cleared: {count} kills removed")
        return count


# Global instance
_kill_history: KillHistory | None = None


def get_kill_history() -> KillHistory:
    """Get or create the kill history instance."""
    global _kill_history
    if _kill_history is None:
        _kill_history = KillHistory()
    return _kill_history
