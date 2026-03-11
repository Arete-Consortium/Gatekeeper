"""Cached FW system data for pirate insurgency security suppression.

Fetches ESI /fw/systems/ and caches for 5 minutes. Provides a lookup
to determine if a system is occupied by a pirate faction, which causes
effective security suppression (lowsec → nullsec).

Pirate faction IDs:
  500010 - Guristas Pirates
  500011 - Angel Cartel
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

ESI_BASE = "https://esi.evetech.net/latest"

# Pirate faction IDs that cause security suppression
PIRATE_FACTION_IDS = frozenset({500010, 500011})

# Cache TTL in seconds
FW_CACHE_TTL = 300  # 5 minutes


@dataclass
class FWCacheEntry:
    """Cached FW system data."""

    # system_id -> occupier_faction_id
    occupier_by_system: dict[int, int] = field(default_factory=dict)
    # Set of system IDs currently pirate-occupied
    pirate_occupied: set[int] = field(default_factory=set)
    last_fetched: float = 0.0


_cache = FWCacheEntry()


def _is_stale() -> bool:
    return time.monotonic() - _cache.last_fetched > FW_CACHE_TTL


async def refresh_fw_cache() -> None:
    """Fetch fresh FW data from ESI and update cache."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{ESI_BASE}/fw/systems/")
            resp.raise_for_status()
            fw_data = resp.json()
    except httpx.HTTPError:
        logger.warning("Failed to refresh FW cache from ESI")
        return

    occupier_map: dict[int, int] = {}
    pirate_set: set[int] = set()

    for entry in fw_data:
        sid = entry.get("solar_system_id")
        occupier = entry.get("occupier_faction_id")
        if not sid or not occupier:
            continue
        occupier_map[sid] = occupier
        if occupier in PIRATE_FACTION_IDS:
            pirate_set.add(sid)

    _cache.occupier_by_system = occupier_map
    _cache.pirate_occupied = pirate_set
    _cache.last_fetched = time.monotonic()

    if pirate_set:
        logger.info("FW cache refreshed: %d pirate-occupied systems", len(pirate_set))


def is_pirate_occupied_sync(system_id: int) -> bool:
    """Check if a system is pirate-occupied (sync, uses cached data).

    Returns False if cache is empty/stale — fail-open to avoid
    blocking routing when ESI is down.
    """
    return system_id in _cache.pirate_occupied


async def ensure_fw_cache() -> None:
    """Refresh cache if stale. Call from async context (e.g., app startup or request)."""
    if _is_stale():
        await refresh_fw_cache()


def get_pirate_occupied_systems() -> set[int]:
    """Return the current set of pirate-occupied system IDs."""
    return _cache.pirate_occupied.copy()


_refresh_task: asyncio.Task | None = None


async def _refresh_loop() -> None:
    """Background loop to keep FW cache fresh."""
    while True:
        await asyncio.sleep(FW_CACHE_TTL)
        try:
            await refresh_fw_cache()
        except Exception:
            logger.exception("FW cache refresh loop error")


async def start_fw_cache_refresh() -> None:
    """Start the background refresh loop. Call once at app startup."""
    global _refresh_task
    await refresh_fw_cache()
    _refresh_task = asyncio.create_task(_refresh_loop())
