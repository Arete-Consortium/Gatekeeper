"""Lightweight page view analytics endpoint."""

import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory pageview storage with TTL
# Structure: {path: [(timestamp_monotonic, unix_timestamp), ...]}
_pageviews: dict[str, list[tuple[float, float]]] = defaultdict(list)
_TTL = 86400.0  # 24 hours

# Rate limiting for pageview submissions
_pageview_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 30  # max per minute per IP
_RATE_WINDOW = 60.0


def _is_rate_limited(ip: str) -> bool:
    """Check if an IP has exceeded the pageview rate limit."""
    now = time.monotonic()
    _pageview_rate_limits[ip] = [
        t for t in _pageview_rate_limits[ip] if now - t < _RATE_WINDOW
    ]
    if len(_pageview_rate_limits[ip]) >= _RATE_LIMIT:
        return True
    _pageview_rate_limits[ip].append(now)
    return False


def _prune_old_entries() -> None:
    """Remove pageview entries older than TTL."""
    now = time.monotonic()
    paths_to_remove: list[str] = []
    for path, entries in _pageviews.items():
        _pageviews[path] = [(mono, unix) for mono, unix in entries if now - mono < _TTL]
        if not _pageviews[path]:
            paths_to_remove.append(path)
    for path in paths_to_remove:
        del _pageviews[path]


class PageviewRequest(BaseModel):
    """Pageview tracking payload."""

    path: str = Field(..., max_length=500)
    referrer: str = Field("", max_length=2000)
    timestamp: str = Field("", max_length=100)


class PathStats(BaseModel):
    """Stats for a single path."""

    path: str
    views: int


class AnalyticsSummary(BaseModel):
    """Summary of pageview analytics for the last 24 hours."""

    total_views: int
    unique_paths: int
    paths: list[PathStats]


@router.post(
    "/pageview",
    status_code=204,
    summary="Track a page view",
    description="Fire-and-forget pageview tracking. No response body.",
)
async def track_pageview(pageview: PageviewRequest, request: Request) -> Response:
    """Record a pageview event."""
    client_ip = request.client.host if request.client else "unknown"

    if _is_rate_limited(client_ip):
        return Response(status_code=429)

    now_mono = time.monotonic()
    now_unix = time.time()
    _pageviews[pageview.path].append((now_mono, now_unix))

    logger.info(
        "Pageview",
        extra={
            "page_path": pageview.path,
            "referrer": pageview.referrer[:200] if pageview.referrer else "",
            "client_ip": client_ip,
        },
    )

    return Response(status_code=204)


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Get analytics summary",
    description="Returns pageview counts per path for the last 24 hours.",
)
async def get_analytics_summary() -> AnalyticsSummary:
    """Return basic pageview stats from the last 24 hours."""
    _prune_old_entries()

    paths: list[PathStats] = []
    total_views = 0

    for path, entries in sorted(_pageviews.items(), key=lambda x: len(x[1]), reverse=True):
        views = len(entries)
        total_views += views
        paths.append(PathStats(path=path, views=views))

    return AnalyticsSummary(
        total_views=total_views,
        unique_paths=len(paths),
        paths=paths,
    )
