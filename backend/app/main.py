"""EVE Gatekeeper API - Main Application."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .api import routes_map, routes_systems
from .api.metrics import router as metrics_router
from .api.v1 import router as v1_router
from .api.v1.status import set_start_time
from .core.config import settings
from .logging import LoggingMiddleware, configure_logging
from .middleware import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    setup_rate_limiting,
)
from .middleware.security import RequestSizeLimitMiddleware

# Configure structured logging
configure_logging()

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description="EVE Online navigation, routing, and intel visualization API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {"name": "health", "description": "Health check endpoints"},
            {"name": "systems", "description": "System information and risk data"},
            {"name": "routing", "description": "Route calculation and map configuration"},
            {"name": "status", "description": "API status and diagnostics"},
        ],
    )

    # ==========================================================================
    # Middleware (order matters - first added = outermost)
    # ==========================================================================

    # Request size limit (10MB)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=10 * 1024 * 1024)

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request context (request ID, timing)
    app.add_middleware(RequestContextMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Requested-With",
            "X-Session-ID",
        ],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    # GZip compression for responses > 1KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Rate limiting
    setup_rate_limiting(app)

    # Logging context middleware
    app.add_middleware(LoggingMiddleware)

    # ==========================================================================
    # Routers
    # ==========================================================================

    # Metrics endpoint (at root level)
    app.include_router(metrics_router)

    # API v1 routes (new versioned API)
    app.include_router(v1_router)

    # Legacy routes (for backward compatibility)
    app.include_router(routes_systems.router, prefix="/systems", tags=["systems"])
    app.include_router(routes_map.router, prefix="/map", tags=["routing"])

    return app


app = create_app()

# Store startup time for uptime calculation
_startup_time: datetime = datetime.now(UTC)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application on startup."""
    global _startup_time
    _startup_time = datetime.now(UTC)
    set_start_time(_startup_time)

    logger.info(
        "Application starting",
        extra={"version": settings.API_VERSION, "project": settings.PROJECT_NAME},
    )

    # Start zKillboard listener for real-time kill feed
    from .services.zkill_listener import get_zkill_listener

    listener = get_zkill_listener()
    await listener.start()

    # Start universe data monitor
    from .services.universe_refresher import get_universe_refresher

    refresher = get_universe_refresher()
    await refresher.start()

    # Start kill history service
    from .services.kill_history import get_kill_history

    kill_history = get_kill_history()
    await kill_history.start()

    # Start Redis pub/sub for multi-instance deployments
    from .services.redis_pubsub import get_redis_pubsub

    pubsub = get_redis_pubsub()
    await pubsub.start()

    # Initialize default webhook subscriptions from env vars
    from .services.webhooks import init_default_subscriptions

    init_default_subscriptions()

    # Load persisted wormhole connections from database
    from .services.wormhole import get_wormhole_service

    wh_service = get_wormhole_service()
    try:
        loaded = await wh_service.load_from_db()
        logger.info(f"Loaded {loaded} wormhole connections from database")
    except Exception:
        logger.warning("Failed to load wormhole connections from database", exc_info=True)

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on application shutdown."""
    logger.info("Application shutting down")

    # Stop zKillboard listener
    from .services.zkill_listener import get_zkill_listener

    listener = get_zkill_listener()
    await listener.stop()

    # Stop universe data monitor
    from .services.universe_refresher import get_universe_refresher

    refresher = get_universe_refresher()
    await refresher.stop()

    # Stop kill history service
    from .services.kill_history import get_kill_history

    kill_history = get_kill_history()
    await kill_history.stop()

    # Stop Redis pub/sub
    from .services.redis_pubsub import get_redis_pubsub

    pubsub = get_redis_pubsub()
    await pubsub.stop()

    # Close database connections
    from .db.database import close_db

    await close_db()

    logger.info("Application shutdown complete")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint for container orchestration.

    Returns health status with component checks.
    """
    uptime = (datetime.now(UTC) - _startup_time).total_seconds()

    # Check database connectivity
    database_status = "ok"
    try:
        from .services.data_loader import load_universe

        universe = load_universe()
        if not universe.systems:
            database_status = "warning"
            logger.warning("Health check: database returned no systems")
    except Exception as e:
        database_status = "error"
        logger.error("Health check: database error", extra={"error": str(e)})

    # Check cache status (actual connectivity)
    cache_status = "memory"
    if settings.REDIS_URL:
        try:
            from .services.cache import get_cache

            cache = await get_cache()
            if hasattr(cache, "ping") and await cache.ping():
                cache_status = "redis"
            elif hasattr(cache, "_redis"):
                cache_status = "redis_degraded"
            else:
                cache_status = "memory"
        except Exception:
            cache_status = "memory"

    # Check ESI connectivity
    esi_status = "unknown"
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ESI_BASE_URL}/status/")
            if response.status_code == 200:
                esi_status = "ok"
            else:
                esi_status = "degraded"
    except httpx.TimeoutException:
        esi_status = "timeout"
    except Exception:
        esi_status = "error"

    # Overall status
    overall_status = "healthy"
    if database_status == "error":
        overall_status = "unhealthy"
    elif database_status == "warning":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": settings.API_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "uptime_seconds": uptime,
        "checks": {
            "database": database_status,
            "cache": cache_status,
            "esi": esi_status,
        },
    }


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.API_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
        "status": "/api/v1/status",
    }
