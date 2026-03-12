"""Lightweight page view analytics endpoint.

Pageviews are persisted to PostgreSQL for survival across restarts.
In-memory rate limiting prevents abuse.
"""

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from ...db.database import get_session_factory
from ...db.models import PageviewRecord

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting for pageview submissions (in-memory only)
_pageview_rate_limits: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 30  # max per minute per IP
_RATE_WINDOW = 60.0
_TTL_HOURS = 24


def _is_rate_limited(ip: str) -> bool:
    """Check if an IP has exceeded the pageview rate limit."""
    now = time.monotonic()
    _pageview_rate_limits[ip] = [t for t in _pageview_rate_limits[ip] if now - t < _RATE_WINDOW]
    if len(_pageview_rate_limits[ip]) >= _RATE_LIMIT:
        return True
    _pageview_rate_limits[ip].append(now)
    return False


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

    # Persist to DB
    try:
        factory = get_session_factory()
        async with factory() as session:
            record = PageviewRecord(
                path=pageview.path,
                client_ip=client_ip,
                viewed_at=datetime.now(UTC),
            )
            session.add(record)
            await session.commit()
    except Exception as e:
        logger.debug(f"Could not persist pageview: {e}")

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
    cutoff = datetime.now(UTC) - timedelta(hours=_TTL_HOURS)

    try:
        factory = get_session_factory()
        async with factory() as session:
            # Clean up old entries
            await session.execute(delete(PageviewRecord).where(PageviewRecord.viewed_at < cutoff))

            # Aggregate by path
            result = await session.execute(
                select(
                    PageviewRecord.path,
                    func.count(PageviewRecord.id).label("views"),
                )
                .where(PageviewRecord.viewed_at >= cutoff)
                .group_by(PageviewRecord.path)
                .order_by(func.count(PageviewRecord.id).desc())
            )
            rows = result.all()
            await session.commit()

        paths = [PathStats(path=row.path, views=row.views) for row in rows]
        total_views = sum(p.views for p in paths)

        return AnalyticsSummary(
            total_views=total_views,
            unique_paths=len(paths),
            paths=paths,
        )
    except Exception as e:
        logger.warning(f"Could not query analytics from DB: {e}")
        return AnalyticsSummary(total_views=0, unique_paths=0, paths=[])
