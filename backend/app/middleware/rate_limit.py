"""Rate limiting middleware using slowapi.

Supports per-user rate limiting for authenticated requests (via character_id)
and IP-based rate limiting for unauthenticated requests.
"""

import json
import logging

from fastapi import FastAPI, Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from ..core.config import settings
from ..services.jwt_service import validate_jwt

logger = logging.getLogger(__name__)


def extract_character_id_from_request(request: Request) -> int | None:
    """
    Extract character_id from an authenticated request.

    Checks (in order):
    1. JWT Bearer token in Authorization header
    2. character_id query parameter

    Returns:
        Character ID if found and valid, None otherwise.
    """
    # Try Bearer token first
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        payload, error = validate_jwt(token, verify_fingerprint=None)
        if payload and not error:
            return payload.sub  # character_id is stored as 'sub' in JWT

    # Fall back to query parameter
    character_id = request.query_params.get("character_id")
    if character_id:
        try:
            return int(character_id)
        except ValueError:
            pass

    return None


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
    character_id = extract_character_id_from_request(request)
    if character_id is not None:
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
        return f"{settings.RATE_LIMIT_PER_MINUTE_USER}/minute"
    elif identifier.startswith("apikey:"):
        return f"{settings.RATE_LIMIT_PER_MINUTE_APIKEY}/minute"
    else:
        # IP-based (unauthenticated)
        return f"{settings.RATE_LIMIT_PER_MINUTE}/minute"


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
    if identifier.startswith("user:"):
        limit = settings.RATE_LIMIT_PER_MINUTE_USER
        user_type = "authenticated"
    elif identifier.startswith("apikey:"):
        limit = settings.RATE_LIMIT_PER_MINUTE_APIKEY
        user_type = "api_key"
    else:
        limit = settings.RATE_LIMIT_PER_MINUTE
        user_type = "anonymous"

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


def setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting for the FastAPI application."""
    if not settings.RATE_LIMIT_ENABLED:
        logger.debug("Rate limiting disabled")
        return

    # Add the limiter to app state
    app.state.limiter = limiter

    # Add the SlowAPI middleware
    app.add_middleware(SlowAPIMiddleware)

    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    logger.info(
        "Rate limiting enabled",
        extra={
            "default_limit": settings.RATE_LIMIT_PER_MINUTE,
            "user_limit": settings.RATE_LIMIT_PER_MINUTE_USER,
            "apikey_limit": settings.RATE_LIMIT_PER_MINUTE_APIKEY,
        },
    )
