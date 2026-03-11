"""Rate limiting middleware using slowapi.

Supports per-user rate limiting for authenticated requests (via character_id),
IP-based rate limiting for unauthenticated requests, and per-endpoint rate
limits based on path pattern matching.

Endpoint tiers:
- Health/status: high limit (monitoring probes)
- Map config/data: moderate (cached, heavy responses)
- Route calculation: low (CPU intensive)
- Auth endpoints: lowest (brute force protection)
- Write endpoints (POST/PUT/DELETE): low
- WebSocket: exempt (persistent connections)
- Default: moderate
"""

import json
import logging
import re

from fastapi import FastAPI, Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from ..core.config import settings
from ..services.jwt_service import validate_jwt

logger = logging.getLogger(__name__)

# Path patterns for per-endpoint rate limiting.
# Order matters: first match wins. Compiled at module load for performance.
# Each entry: (compiled_regex, settings_attr_name)
ENDPOINT_RATE_LIMIT_PATTERNS: list[tuple[re.Pattern, str]] = [
    # WebSocket — exempt (persistent connections, no rate limit applied)
    (re.compile(r"^/api/v1/ws/"), "WEBSOCKET"),
    # Health & status
    (re.compile(r"^/health$"), "RATE_LIMIT_HEALTH"),
    (re.compile(r"^/$"), "RATE_LIMIT_HEALTH"),
    (re.compile(r"^/api/v1/status"), "RATE_LIMIT_HEALTH"),
    # Auth endpoints — brute force protection
    (re.compile(r"^/api/v1/auth/"), "RATE_LIMIT_AUTH"),
    (re.compile(r"^/callback"), "RATE_LIMIT_AUTH"),
    (re.compile(r"^/api/v1/billing/"), "RATE_LIMIT_AUTH"),
    # Route calculation — CPU intensive
    (re.compile(r"^/api/v1/route/"), "RATE_LIMIT_ROUTE"),
    (re.compile(r"^/api/v1/jump/"), "RATE_LIMIT_ROUTE"),
    (re.compile(r"^/api/v1/pochven/route"), "RATE_LIMIT_ROUTE"),
    # Map config/data — cached, heavy responses
    (re.compile(r"^/api/v1/map/"), "RATE_LIMIT_MAP"),
    (re.compile(r"^/map/"), "RATE_LIMIT_MAP"),
    (re.compile(r"^/api/v1/thera/"), "RATE_LIMIT_MAP"),
    (re.compile(r"^/api/v1/pochven/"), "RATE_LIMIT_MAP"),
    (re.compile(r"^/api/v1/systems/"), "RATE_LIMIT_MAP"),
]


def get_endpoint_rate_limit(request: Request) -> int:
    """
    Determine the per-endpoint rate limit for a request.

    Matches the request path against endpoint patterns and returns the
    appropriate rate limit. Write methods (POST/PUT/DELETE/PATCH) get
    the write limit unless a more specific pattern matches first.

    Args:
        request: The incoming HTTP request.

    Returns:
        Rate limit in requests per minute for this endpoint.
    """
    path = request.url.path

    # Check path patterns (first match wins)
    for pattern, attr_name in ENDPOINT_RATE_LIMIT_PATTERNS:
        if pattern.match(path):
            if attr_name == "WEBSOCKET":
                return 0  # 0 = no limit
            return getattr(settings, attr_name)

    # Write endpoints get a lower limit unless matched above
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        return settings.RATE_LIMIT_WRITE

    # Default
    return settings.RATE_LIMIT_DEFAULT


def extract_character_from_request(request: Request) -> tuple[int | None, str]:
    """
    Extract character_id and subscription tier from an authenticated request.

    Checks (in order):
    1. JWT Bearer token in Authorization header
    2. character_id query parameter

    Returns:
        Tuple of (character_id, tier). tier defaults to "free".
    """
    # Try Bearer token first
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        payload, error = validate_jwt(token, verify_fingerprint=None)
        if payload and not error:
            return payload.sub, getattr(payload, "tier", "free")

    # Fall back to query parameter
    character_id = request.query_params.get("character_id")
    if character_id:
        try:
            return int(character_id), "free"
        except ValueError:
            pass

    return None, "free"


def get_request_identifier(request: Request) -> str:
    """
    Get a unique identifier for the request.

    Priority:
    1. Character ID (for authenticated users) - uses per-user rate limit
    2. API key (if enabled) - uses API key rate limit
    3. IP address (fallback) - uses default rate limit

    Returns:
        String identifier for rate limiting bucket.
    """
    # Check for authenticated user (character_id)
    character_id, tier = extract_character_from_request(request)
    if character_id is not None:
        if tier == "pro":
            return f"user:pro:{character_id}"
        return f"user:{character_id}"

    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key and settings.API_KEY_ENABLED:
        return f"apikey:{api_key}"  # nosemgrep: directly-returned-format-string

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_rate_limit_for_identifier(identifier: str) -> str:
    """
    Get the appropriate rate limit based on identifier type.

    Args:
        identifier: The rate limit bucket identifier (user:X, apikey:X, ip:X)

    Returns:
        Rate limit string (e.g., "200/minute")
    """
    if identifier.startswith("user:"):
        if identifier.startswith("user:pro:"):
            return f"{settings.RATE_LIMIT_PER_MINUTE_PRO}/minute"
        return f"{settings.RATE_LIMIT_PER_MINUTE_USER}/minute"
    elif identifier.startswith("apikey:"):
        return f"{settings.RATE_LIMIT_PER_MINUTE_APIKEY}/minute"
    else:
        # IP-based (unauthenticated)
        return f"{settings.RATE_LIMIT_PER_MINUTE}/minute"


def _dynamic_default_limit(request_identifier: str) -> str:
    """Dynamic default limit that returns the per-identifier limit string.

    Used as slowapi's default_limits callable so each identifier type
    gets the right global cap. Per-endpoint limits are enforced separately
    via the PerEndpointRateLimitMiddleware.
    """
    return get_rate_limit_for_identifier(request_identifier)


# Create the limiter instance with default (IP-based) limits
# Per-user limits are applied dynamically via decorators
limiter = Limiter(
    key_func=get_request_identifier,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True,
)


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Handle rate limit exceeded errors."""
    detail = getattr(exc, "detail", None)
    retry_after = detail.split("per")[0].strip() if detail else "60"

    # Determine which limit was exceeded based on the identifier
    identifier = get_request_identifier(request)
    if identifier.startswith("user:pro:"):
        limit = settings.RATE_LIMIT_PER_MINUTE_PRO
        user_type = "pro"
    elif identifier.startswith("user:"):
        limit = settings.RATE_LIMIT_PER_MINUTE_USER
        user_type = "authenticated"
    elif identifier.startswith("apikey:"):
        limit = settings.RATE_LIMIT_PER_MINUTE_APIKEY
        user_type = "api_key"
    else:
        limit = settings.RATE_LIMIT_PER_MINUTE
        user_type = "anonymous"

    # Use the per-endpoint limit if it's lower than the per-identifier limit
    endpoint_limit = get_endpoint_rate_limit(request)
    if endpoint_limit > 0 and endpoint_limit < limit:
        limit = endpoint_limit

    logger.warning(
        "Rate limit exceeded",
        extra={
            "identifier": identifier,
            "user_type": user_type,
            "limit": limit,
            "path": request.url.path,
        },
    )

    response_body = json.dumps(
        {
            "error": "Rate limit exceeded",
            "detail": "Too many requests",
            "user_type": user_type,
        }
    )

    return Response(
        content=response_body,
        status_code=429,
        media_type="application/json",
        headers={
            "Retry-After": retry_after,
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-User-Type": user_type,
        },
    )


class PerEndpointRateLimitMiddleware:
    """ASGI middleware that enforces per-endpoint rate limits.

    Uses an in-memory sliding window counter keyed by (identifier, endpoint_tier).
    This runs alongside SlowAPI's global per-identifier limits, providing a
    second layer of rate limiting based on endpoint sensitivity.

    WebSocket paths are exempt (persistent connections).
    """

    def __init__(self, app):
        self.app = app
        # In-memory counters: key -> list of timestamps
        self._counters: dict[str, list[float]] = {}
        self._window = 60.0  # 1 minute window

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time

        request = Request(scope)
        endpoint_limit = get_endpoint_rate_limit(request)

        # 0 means no limit (WebSocket exempt)
        if endpoint_limit == 0:
            await self.app(scope, receive, send)
            return

        # Build bucket key: identifier + endpoint limit tier
        identifier = get_request_identifier(request)
        path = request.url.path
        bucket_key = f"{identifier}:{_get_endpoint_tier(path, request.method)}"

        now = time.time()
        window_start = now - self._window

        # Clean old entries and count current window
        timestamps = self._counters.get(bucket_key, [])
        timestamps = [t for t in timestamps if t > window_start]

        if len(timestamps) >= endpoint_limit:
            # Rate limited
            retry_after = str(int(self._window - (now - timestamps[0])) + 1)
            response_body = json.dumps(
                {
                    "error": "Rate limit exceeded",
                    "detail": "Too many requests to this endpoint",
                }
            )
            response = Response(
                content=response_body,
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": retry_after,
                    "X-RateLimit-Limit": str(endpoint_limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
            await response(scope, receive, send)
            return

        # Record this request
        timestamps.append(now)
        self._counters[bucket_key] = timestamps

        # Add rate limit headers via a wrapper
        remaining = endpoint_limit - len(timestamps)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-ratelimit-limit-endpoint", str(endpoint_limit).encode()))
                headers.append((b"x-ratelimit-remaining-endpoint", str(remaining).encode()))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _get_endpoint_tier(path: str, method: str) -> str:
    """Map a request path + method to a rate limit tier name for bucket keying."""
    for pattern, attr_name in ENDPOINT_RATE_LIMIT_PATTERNS:
        if pattern.match(path):
            return attr_name
    if method in ("POST", "PUT", "DELETE", "PATCH"):
        return "RATE_LIMIT_WRITE"
    return "RATE_LIMIT_DEFAULT"


def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting for the FastAPI application."""
    if not settings.RATE_LIMIT_ENABLED:
        logger.debug("Rate limiting disabled")
        return

    # Add the limiter to app state
    app.state.limiter = limiter

    # Add per-endpoint rate limiting middleware (inner — runs first)
    app.add_middleware(PerEndpointRateLimitMiddleware)

    # Add the SlowAPI middleware (outer — global per-identifier limits)
    app.add_middleware(SlowAPIMiddleware)

    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    logger.info(
        "Rate limiting enabled",
        extra={
            "default_limit": settings.RATE_LIMIT_DEFAULT,
            "health_limit": settings.RATE_LIMIT_HEALTH,
            "map_limit": settings.RATE_LIMIT_MAP,
            "route_limit": settings.RATE_LIMIT_ROUTE,
            "auth_limit": settings.RATE_LIMIT_AUTH,
            "write_limit": settings.RATE_LIMIT_WRITE,
            "user_limit": settings.RATE_LIMIT_PER_MINUTE_USER,
            "pro_limit": settings.RATE_LIMIT_PER_MINUTE_PRO,
        },
    )
