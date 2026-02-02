"""Universe data refresh service.

Monitors universe data freshness and provides refresh capabilities.
Universe data (systems, gates) comes from EVE's Static Data Export (SDE)
and changes infrequently (only with game updates).
"""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from ..core.config import settings

logger = logging.getLogger(__name__)


class UniverseRefresher:
    """Monitors and manages universe data freshness.

    The universe data (systems, gates, regions) is static data from EVE's SDE.
    It only changes when CCP releases game updates. This service:
    - Monitors data file modification time
    - Warns if data appears stale
    - Provides methods to invalidate cached data
    - Tracks refresh metadata
    """

    def __init__(self):
        self._running: bool = False
        self._task: asyncio.Task | None = None
        self._last_check: datetime | None = None
        self._data_mtime: datetime | None = None
        self._stale_warned = False

    @property
    def is_running(self) -> bool:
        """Check if the monitor is running."""
        return self._running

    @property
    def data_file(self) -> Path:
        """Get the universe data file path."""
        return settings.UNIVERSE_FILE

    @property
    def data_age_hours(self) -> float | None:
        """Get the age of the data file in hours."""
        if not self._data_mtime:
            self._update_mtime()
        if self._data_mtime:
            delta = datetime.now(UTC) - self._data_mtime
            return delta.total_seconds() / 3600
        return None

    def _update_mtime(self) -> None:
        """Update the cached modification time."""
        try:
            if self.data_file.exists():
                mtime = self.data_file.stat().st_mtime
                self._data_mtime = datetime.fromtimestamp(mtime, tz=UTC)
        except OSError as e:
            logger.warning(f"Could not stat universe file: {e}")

    async def start(self) -> None:
        """Start the universe data monitor."""
        if self._running:
            logger.warning("Universe refresher already running")
            return

        self._running = True
        self._update_mtime()

        # Log initial status
        age = self.data_age_hours
        if age is not None:
            logger.info(
                "Universe refresher started",
                extra={
                    "data_file": str(self.data_file),
                    "data_age_hours": round(age, 1),
                    "last_modified": self._data_mtime.isoformat() if self._data_mtime else None,
                },
            )

            # Check if data is stale on startup
            if settings.UNIVERSE_REFRESH_ON_STARTUP:
                await self._check_freshness()

        # Start background monitoring if enabled
        if settings.UNIVERSE_REFRESH_ENABLED:
            self._task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop the universe data monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Universe refresher stopped")

    async def _monitor_loop(self) -> None:
        """Background loop to periodically check data freshness."""
        check_interval = 3600  # Check every hour
        while self._running:
            try:
                await asyncio.sleep(check_interval)
                if self._running:
                    await self._check_freshness()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in universe monitor loop: {e}")
                await asyncio.sleep(60)  # Brief pause before retry

    async def _check_freshness(self) -> None:
        """Check if universe data needs refresh."""
        self._update_mtime()
        self._last_check = datetime.now(UTC)

        age = self.data_age_hours
        threshold = settings.UNIVERSE_REFRESH_INTERVAL_HOURS * 24  # Convert to hours

        if age is not None and age > threshold and not self._stale_warned:
            logger.warning(
                "Universe data may be stale",
                extra={
                    "age_days": round(age / 24, 1),
                    "threshold_days": settings.UNIVERSE_REFRESH_INTERVAL_HOURS,
                    "recommendation": "Run scripts/generate_universe.py with fresh SDE data",
                },
            )
            self._stale_warned = True

    def invalidate_cache(self) -> None:
        """Invalidate the universe data cache.

        Call this after updating universe.json to ensure
        fresh data is loaded on next access.
        """
        from .data_loader import load_risk_config, load_universe

        load_universe.cache_clear()
        load_risk_config.cache_clear()
        self._data_mtime = None
        self._stale_warned = False
        self._update_mtime()
        logger.info(
            "Universe cache invalidated",
            extra={"new_mtime": self._data_mtime.isoformat() if self._data_mtime else None},
        )

    def get_status(self) -> dict:
        """Get the current status of universe data."""
        self._update_mtime()
        age = self.data_age_hours

        # Determine freshness status
        if age is None:
            status = "unknown"
        elif age < 24 * 7:  # Less than 1 week
            status = "fresh"
        elif age < 24 * 30:  # Less than 1 month
            status = "ok"
        elif age < 24 * 90:  # Less than 3 months
            status = "stale"
        else:
            status = "very_stale"

        return {
            "file": str(self.data_file),
            "exists": self.data_file.exists(),
            "last_modified": self._data_mtime.isoformat() if self._data_mtime else None,
            "age_hours": round(age, 1) if age else None,
            "age_days": round(age / 24, 1) if age else None,
            "status": status,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "monitoring_enabled": settings.UNIVERSE_REFRESH_ENABLED,
        }


# Global instance
_refresher: UniverseRefresher | None = None


def get_universe_refresher() -> UniverseRefresher:
    """Get or create the universe refresher instance."""
    global _refresher
    if _refresher is None:
        _refresher = UniverseRefresher()
    return _refresher
