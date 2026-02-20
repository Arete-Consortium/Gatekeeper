"""Status API v1 endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from ...core.config import settings

router = APIRouter()

# Track start time for uptime calculation
_start_time: datetime = datetime.now(UTC)


def set_start_time(start: datetime) -> None:
    """Set the application start time (called from main.py)."""
    global _start_time
    _start_time = start


@router.get(
    "/",
    summary="Get API status",
    description="Returns detailed status information about the API.",
)
async def get_status() -> dict[str, Any]:
    """
    Get detailed API status including version, uptime, and component health.

    This endpoint provides more detail than /health and is intended for
    monitoring dashboards and admin interfaces.
    """
    now = datetime.now(UTC)
    uptime = (now - _start_time).total_seconds()

    # Check database connectivity
    database_status = "ok"
    try:
        from ...services.data_loader import load_universe

        universe = load_universe()
        system_count = len(universe.systems)
    except Exception:
        database_status = "error"
        system_count = 0

    # Check cache status (actual connectivity)
    cache_status = "memory"
    try:
        from ...services.cache import get_cache

        cache = await get_cache()
        if hasattr(cache, "ping") and await cache.ping():
            cache_status = "redis"
        elif hasattr(cache, "_redis"):
            cache_status = "redis_degraded"
        else:
            cache_status = "memory"
    except Exception:
        cache_status = "error"

    return {
        "status": "operational",
        "version": settings.API_VERSION,
        "name": settings.PROJECT_NAME,
        "timestamp": now.isoformat(),
        "uptime_seconds": uptime,
        "uptime_formatted": format_uptime(uptime),
        "environment": {
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL,
        },
        "checks": {
            "database": database_status,
            "cache": cache_status,
            "systems_loaded": system_count,
        },
        "features": {
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
            "api_key_auth": settings.API_KEY_ENABLED,
            "metrics": settings.METRICS_ENABLED,
        },
    }


def format_uptime(seconds: float) -> str:
    """Format uptime seconds into a human-readable string."""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


@router.get(
    "/websocket-health",
    summary="Get WebSocket connection health",
    description="Returns health status for WebSocket connections including zKillboard listener.",
)
async def get_websocket_health() -> dict[str, Any]:
    """
    Get health status for WebSocket connections.

    This endpoint provides detailed health information about WebSocket connections:
    - zKillboard listener status (connection state, retry attempts, uptime)
    - Active client connections
    - Connection statistics and metrics
    """
    from ...services.connection_manager import connection_manager
    from ...services.zkill_listener import get_zkill_listener

    zkill_listener = get_zkill_listener()

    return {
        "zkill_listener": zkill_listener.get_health_status(),
        "client_connections": connection_manager.get_stats(),
    }


@router.get(
    "/universe",
    summary="Get universe data status",
    description="Returns status information about the universe data file.",
)
async def get_universe_status() -> dict[str, Any]:
    """
    Get status information about the universe data.

    Returns data freshness, file info, and monitoring status.
    """
    from ...services.universe_refresher import get_universe_refresher

    refresher = get_universe_refresher()
    return refresher.get_status()


@router.post(
    "/universe/invalidate",
    summary="Invalidate universe cache",
    description="Clears the universe data cache to force reload on next access.",
)
async def invalidate_universe_cache() -> dict[str, Any]:
    """
    Invalidate the universe data cache.

    Forces the next API request to reload universe data from disk.
    Use after updating universe.json with new data.
    """
    from ...services.universe_refresher import get_universe_refresher

    refresher = get_universe_refresher()
    refresher.invalidate_cache()
    return {"status": "invalidated", "new_status": refresher.get_status()}


@router.get(
    "/cache/stats",
    summary="Get cache statistics",
    description="Returns cache hit/miss metrics and storage information.",
)
async def get_cache_stats() -> dict[str, Any]:
    """
    Get cache statistics including hit rates and storage metrics.

    Returns cache type (memory/redis), hit/miss counts, and hit ratio.
    """
    from ...services.cache import get_cache

    cache = await get_cache()
    stats = cache.get_stats()

    # Add derived metrics
    total_requests = stats.get("hits", 0) + stats.get("misses", 0)

    return {
        "cache_type": stats.get("type", "unknown"),
        "hits": stats.get("hits", 0),
        "misses": stats.get("misses", 0),
        "total_requests": total_requests,
        "hit_ratio": stats.get("hit_ratio", 0),
        "hit_percentage": round(stats.get("hit_ratio", 0) * 100, 2),
        "entries": stats.get("entries", None),  # Only for memory cache
    }


@router.get(
    "/kills",
    summary="Get recent kills",
    description="Returns recent kills from the kill history with optional filtering.",
)
async def get_recent_kills(
    limit: int = 100,
    system_id: int | None = None,
    region_id: int | None = None,
    min_value: float | None = None,
) -> dict[str, Any]:
    """
    Get recent kills from the kill history.

    Supports filtering by system, region, and minimum ISK value.
    Returns newest kills first, up to the specified limit.
    """
    from ...services.kill_history import get_kill_history

    history = get_kill_history()
    kills = history.get_recent(
        limit=min(limit, 500),  # Cap at 500 to prevent abuse
        system_id=system_id,
        region_id=region_id,
        min_value=min_value,
    )

    return {
        "count": len(kills),
        "kills": kills,
        "filters": {
            "limit": limit,
            "system_id": system_id,
            "region_id": region_id,
            "min_value": min_value,
        },
    }


@router.get(
    "/kills/stats",
    summary="Get kill history statistics",
    description="Returns statistics about the kill history storage.",
)
async def get_kill_history_stats() -> dict[str, Any]:
    """Get kill history statistics including storage usage and aging metrics."""
    from ...services.kill_history import get_kill_history

    history = get_kill_history()
    return history.get_stats()


@router.get(
    "/pubsub",
    summary="Get Redis pub/sub status",
    description="Returns status of the Redis pub/sub service for multi-instance deployments.",
)
async def get_pubsub_status() -> dict[str, Any]:
    """Get Redis pub/sub status for multi-instance kill event broadcasting."""
    from ...services.redis_pubsub import get_redis_pubsub

    pubsub = get_redis_pubsub()
    return pubsub.get_stats()


@router.get(
    "/version",
    summary="Get version info for website",
    description="Returns comprehensive version and project info for website display.",
)
async def get_version() -> dict[str, Any]:
    """
    Get comprehensive version information for website display.

    This endpoint returns all version information across components,
    feature lists, and metadata suitable for an About page or footer.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.2.0",
        "tagline": "EVE Online navigation, routing, and intel visualization platform",
        "description": (
            "A comprehensive toolkit for EVE Online pilots featuring real-time map "
            "visualization, risk-aware routing, capital jump planning, and live kill "
            "feed streaming."
        ),
        "author": "AreteDriver",
        "license": "MIT",
        "repository": "https://github.com/Arete-Consortium/EVE_Gatekeeper",
        "components": {
            "api": {
                "name": "EVE Gatekeeper API",
                "version": settings.API_VERSION,
                "framework": "FastAPI",
                "python": ">=3.11",
            },
            "desktop": {
                "name": "EVE Gatekeeper Desktop",
                "version": "1.3.0",
                "framework": "Electron",
                "platforms": ["Windows", "macOS", "Linux"],
            },
            "mobile": {
                "name": "EVE Gatekeeper Mobile",
                "version": "1.0.0",
                "framework": "React Native (Expo)",
                "platforms": ["iOS", "Android", "Web"],
            },
        },
        "features": [
            "Risk-aware pathfinding with multiple safety profiles",
            "Real-time kill feed via zKillboard WebSocket",
            "Capital jump route planning",
            "Ansiblex jump bridge management",
            "Ship-type risk profiles (hauler, frigate, cruiser, etc.)",
            "Discord and Slack webhook alerts",
            "EVE Online ESI API integration",
            "Interactive map visualization",
        ],
        "links": {
            "documentation": "/docs",
            "api": "/api/v1",
            "health": "/health",
            "status": "/api/v1/status",
        },
        "tech_stack": {
            "backend": ["FastAPI", "Python 3.11+", "SQLite/PostgreSQL", "Redis"],
            "frontend": ["React Native", "Expo", "TypeScript"],
            "desktop": ["Electron"],
            "deployment": ["Docker", "Docker Compose"],
        },
    }
