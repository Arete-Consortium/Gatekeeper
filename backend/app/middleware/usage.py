"""Usage tracking middleware for admin analytics.

Tracks API endpoint hits and unique client IPs for DAU estimation.
Also detects feature usage from URL patterns.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from ..services.usage_tracker import track_endpoint, track_feature, track_request_ip

# Map URL path prefixes to feature names
_FEATURE_PATTERNS: list[tuple[str, str]] = [
    ("/api/v1/map/", "map_views"),
    ("/api/v1/route", "route_calculations"),
    ("/api/v1/intel/", "intel_lookups"),
    ("/ws/killfeed", "kill_feed_connections"),
]


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """Track endpoint usage and DAU for admin analytics."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path

        # Skip health/status/docs endpoints from tracking
        if path.startswith(("/docs", "/redoc", "/openapi", "/health", "/metrics")):
            return await call_next(request)

        # Track endpoint hit
        track_endpoint(path)

        # Track unique IP for DAU
        client_ip = request.client.host if request.client else "unknown"
        track_request_ip(client_ip)

        # Detect feature usage from path
        for prefix, feature in _FEATURE_PATTERNS:
            if path.startswith(prefix):
                track_feature(feature)
                break

        return await call_next(request)
