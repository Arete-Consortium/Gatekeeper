"""Security middleware for headers and request context."""

import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (only in production/non-localhost)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy
        if settings.is_production:
            csp = (
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'"
            )
        else:
            # Allow unsafe-inline in development for debugging tools
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'"
            )
        response.headers["Content-Security-Policy"] = csp

        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Add request ID and timing information."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or use provided request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store in request state for logging
        request.state.request_id = request_id

        # Track response time
        start_time = time.perf_counter()

        response: Response = await call_next(request)

        # Calculate response time
        process_time = time.perf_counter() - start_time
        response_time_ms = round(process_time * 1000, 2)

        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{response_time_ms}ms"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size."""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length_str = request.headers.get("content-length")

        if content_length_str:
            content_length = int(content_length_str)
            if content_length > self.max_size:
                return Response(
                    content='{"error": "Request too large"}',
                    status_code=413,
                    media_type="application/json",
                )

        response: Response = await call_next(request)
        return response
