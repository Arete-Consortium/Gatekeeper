"""Client error reporting endpoint."""

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory rate limiting: IP -> list of timestamps
_error_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 10  # max errors per minute per IP
_RATE_WINDOW = 60.0  # seconds


def _is_rate_limited(ip: str) -> bool:
    """Check if an IP has exceeded the error reporting rate limit."""
    now = time.monotonic()
    # Prune old entries
    _error_rate_limits[ip] = [t for t in _error_rate_limits[ip] if now - t < _RATE_WINDOW]
    if len(_error_rate_limits[ip]) >= _RATE_LIMIT:
        return True
    _error_rate_limits[ip].append(now)
    return False


class ClientErrorReport(BaseModel):
    """Client-side error report payload."""

    message: str = Field(..., max_length=2000)
    stack: str = Field("", max_length=10000)
    url: str = Field("", max_length=2000)
    timestamp: str = Field("", max_length=100)
    user_agent: str = Field("", max_length=500)


@router.post(
    "",
    status_code=204,
    summary="Report a client-side error",
    description="Fire-and-forget endpoint for frontend error reporting.",
)
async def report_error(report: ClientErrorReport, request: Request) -> Response:
    """Accept a client error report and log it."""
    client_ip = request.client.host if request.client else "unknown"

    if _is_rate_limited(client_ip):
        return Response(status_code=429)

    logger.error(
        "Client error report",
        extra={
            "client_ip": client_ip,
            "error_message": report.message,
            "error_stack": report.stack[:500],
            "error_url": report.url,
            "error_timestamp": report.timestamp,
            "user_agent": report.user_agent[:200],
        },
    )

    return Response(status_code=204)
