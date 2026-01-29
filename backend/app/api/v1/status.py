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
        "repository": "https://github.com/AreteDriver/EVE_Gatekeeper",
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
