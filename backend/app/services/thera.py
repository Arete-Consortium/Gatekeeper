"""Thera wormhole connection service via EVE-Scout API."""

import time
from typing import cast

import httpx

from ..models.thera import TheraConnection
from .data_loader import load_universe

EVE_SCOUT_URL = "https://api.eve-scout.com/v2/public/signatures"
CACHE_TTL_SECONDS = 300  # 5 minutes

# In-memory cache
_cache: dict[str, list[TheraConnection] | float | str | None] = {
    "connections": [],
    "timestamp": 0.0,
    "last_error": None,
}


def clear_thera_cache() -> None:
    """Clear the Thera connection cache (for testing)."""
    _cache["connections"] = []
    _cache["timestamp"] = 0.0
    _cache["last_error"] = None


def fetch_thera_connections() -> list[TheraConnection]:
    """Fetch Thera connections from EVE-Scout API.

    Returns raw connection list (no filtering).
    Results are cached for CACHE_TTL_SECONDS.
    """
    now = time.time()
    cache_age = now - cast(float, _cache["timestamp"])

    if cache_age < CACHE_TTL_SECONDS and _cache["connections"]:
        return list(cast(list[TheraConnection], _cache["connections"]))

    try:
        resp = httpx.get(EVE_SCOUT_URL, timeout=10.0)
        resp.raise_for_status()
        raw = resp.json()

        connections = [TheraConnection(**entry) for entry in raw]
        _cache["connections"] = connections
        _cache["timestamp"] = now
        _cache["last_error"] = None
        return connections

    except (httpx.HTTPError, httpx.TimeoutException, ValueError, KeyError) as e:
        _cache["last_error"] = str(e)
        # Return stale cache if available
        if _cache["connections"]:
            return list(cast(list[TheraConnection], _cache["connections"]))
        return []


def get_active_thera() -> list[TheraConnection]:
    """Get active, valid Thera connections.

    Filters out:
    - Completed connections
    - Expired connections (remaining_hours <= 0)
    - Connections with unknown systems
    """
    universe = load_universe()
    connections = fetch_thera_connections()

    active = []
    for conn in connections:
        if conn.completed:
            continue
        if conn.remaining_hours <= 0:
            continue
        if conn.in_system_name not in universe.systems:
            continue
        if conn.out_system_name not in universe.systems:
            continue
        active.append(conn)

    return active


def get_thera_cache_age() -> float | None:
    """Return cache age in seconds, or None if never fetched."""
    ts = cast(float, _cache["timestamp"])
    if ts == 0.0:
        return None
    return time.time() - ts


def get_thera_last_error() -> str | None:
    """Return the last error message, if any."""
    return cast(str | None, _cache["last_error"])
