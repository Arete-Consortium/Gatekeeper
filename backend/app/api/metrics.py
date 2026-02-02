"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from ..core.config import settings

router = APIRouter()

# =============================================================================
# HTTP Metrics
# =============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

# =============================================================================
# Cache Metrics
# =============================================================================

CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

# Route-specific cache metrics
ROUTE_CACHE_HITS = Counter(
    "route_cache_hits_total",
    "Route calculation cache hits",
    ["profile"],
)

ROUTE_CACHE_MISSES = Counter(
    "route_cache_misses_total",
    "Route calculation cache misses",
    ["profile"],
)

# Risk-specific cache metrics
RISK_CACHE_HITS = Counter(
    "risk_cache_hits_total",
    "Risk assessment cache hits",
)

RISK_CACHE_MISSES = Counter(
    "risk_cache_misses_total",
    "Risk assessment cache misses",
)

# =============================================================================
# ESI Metrics
# =============================================================================

ESI_REQUESTS_TOTAL = Counter(
    "esi_requests_total",
    "Total ESI API requests",
    ["endpoint", "status"],
)

# =============================================================================
# WebSocket Metrics
# =============================================================================

WEBSOCKET_CONNECTIONS = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
)

# =============================================================================
# Application Metrics
# =============================================================================

ROUTE_CALCULATIONS = Counter(
    "route_calculations_total",
    "Total route calculations",
    ["profile"],
)

RISK_CALCULATIONS = Counter(
    "risk_calculations_total",
    "Total risk score calculations",
)

ZKILL_EVENTS = Counter(
    "zkill_events_total",
    "Total zKillboard events received",
    ["event_type"],
)

# =============================================================================
# Info Metric
# =============================================================================

INFO = Gauge(
    "eve_gatekeeper_info",
    "Application information",
    ["version"],
)
INFO.labels(version=settings.API_VERSION).set(1)

# =============================================================================
# Service Degradation Gauge
# =============================================================================

SERVICE_DEGRADATION = Gauge(
    "service_degradation_state",
    "Service degradation state: 0=healthy, 1=degraded, 2=unhealthy",
    ["component"],
)

# Initialize components to healthy state
for component in ["database", "cache", "zkill", "esi"]:
    SERVICE_DEGRADATION.labels(component=component).set(0)


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    """
    if not settings.METRICS_ENABLED:
        return Response(content="Metrics disabled", status_code=404)

    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST,
    )


# =============================================================================
# Helper Functions for Recording Metrics
# =============================================================================


def record_http_request(method: str, path: str, status: int, duration: float) -> None:
    """Record an HTTP request."""
    # Normalize path to avoid high cardinality
    normalized_path = normalize_path(path)
    HTTP_REQUESTS_TOTAL.labels(method=method, path=normalized_path, status=status).inc()
    HTTP_REQUEST_DURATION.labels(method=method, path=normalized_path).observe(duration)


def normalize_path(path: str) -> str:
    """Normalize path to reduce cardinality (replace IDs with placeholders)."""
    import re

    # Replace numeric IDs
    path = re.sub(r"/\d+", "/{id}", path)
    # Replace UUIDs
    path = re.sub(
        r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "/{uuid}",
        path,
        flags=re.IGNORECASE,
    )
    return path


def record_cache_hit(cache_type: str = "memory") -> None:
    """Record a cache hit."""
    CACHE_HITS.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str = "memory") -> None:
    """Record a cache miss."""
    CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_esi_request(endpoint: str, status: int) -> None:
    """Record an ESI API request."""
    ESI_REQUESTS_TOTAL.labels(endpoint=endpoint, status=status).inc()


def record_route_calculation(profile: str) -> None:
    """Record a route calculation."""
    ROUTE_CALCULATIONS.labels(profile=profile).inc()


def record_risk_calculation() -> None:
    """Record a risk calculation."""
    RISK_CALCULATIONS.inc()


def record_zkill_event(event_type: str = "kill") -> None:
    """Record a zKillboard event."""
    ZKILL_EVENTS.labels(event_type=event_type).inc()


def set_websocket_connections(count: int) -> None:
    """Set the current number of WebSocket connections."""
    WEBSOCKET_CONNECTIONS.set(count)


def record_route_cache_hit(profile: str) -> None:
    """Record a route cache hit."""
    ROUTE_CACHE_HITS.labels(profile=profile).inc()


def record_route_cache_miss(profile: str) -> None:
    """Record a route cache miss."""
    ROUTE_CACHE_MISSES.labels(profile=profile).inc()


def record_risk_cache_hit() -> None:
    """Record a risk cache hit."""
    RISK_CACHE_HITS.inc()


def record_risk_cache_miss() -> None:
    """Record a risk cache miss."""
    RISK_CACHE_MISSES.inc()


def set_service_health(component: str, state: int) -> None:
    """
    Set the health state for a service component.

    Args:
        component: Component name (database, cache, zkill, esi)
        state: Health state (0=healthy, 1=degraded, 2=unhealthy)
    """
    SERVICE_DEGRADATION.labels(component=component).set(state)


def mark_healthy(component: str) -> None:
    """Mark a component as healthy."""
    set_service_health(component, 0)


def mark_degraded(component: str) -> None:
    """Mark a component as degraded."""
    set_service_health(component, 1)


def mark_unhealthy(component: str) -> None:
    """Mark a component as unhealthy."""
    set_service_health(component, 2)
