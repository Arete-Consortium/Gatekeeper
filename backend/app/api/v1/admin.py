"""Admin endpoints for managing comp Pro subscriptions and analytics."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.database import get_db
from ...db.models import User
from ...services.usage_tracker import get_dau_estimate, get_feature_usage, get_top_endpoints

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def verify_admin_secret(
    x_admin_secret: str = Header(..., description="Admin secret key"),
) -> str:
    """Verify the admin secret header."""
    if not settings.ADMIN_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints not configured",
        )
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    return x_admin_secret


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class GrantProRequest(BaseModel):
    """Grant comp Pro to a character."""

    character_name: str
    character_id: int
    duration_days: int = 730  # 2 years default
    reason: str = "Bug testing reward"


class RevokeProRequest(BaseModel):
    """Revoke comp Pro from a character."""

    character_id: int


class CompStatusResponse(BaseModel):
    """Comp status for a character."""

    character_id: int
    character_name: str
    subscription_tier: str
    comp_expires_at: str | None = None
    comp_reason: str | None = None


class EndpointHit(BaseModel):
    """A single endpoint hit count."""

    endpoint: str
    count: int


class FeatureUsage(BaseModel):
    """Feature usage counters."""

    map_views: int = 0
    route_calculations: int = 0
    intel_lookups: int = 0
    kill_feed_connections: int = 0


class AdminAnalyticsResponse(BaseModel):
    """Admin analytics dashboard data."""

    active_subscribers: int
    mrr: float
    comp_users: int
    total_users: int
    dau_estimate: int
    popular_endpoints: list[EndpointHit]
    feature_usage: FeatureUsage


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/grant-pro",
    response_model=CompStatusResponse,
    summary="Grant comp Pro subscription",
)
async def grant_pro(
    body: GrantProRequest,
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
) -> CompStatusResponse:
    """Grant a complimentary Pro subscription to a character."""
    result = await db.execute(select(User).where(User.character_id == body.character_id))
    user = result.scalar_one_or_none()

    if not user:
        # Create the user record
        user = User(
            character_id=body.character_id,
            character_name=body.character_name,
            subscription_tier="pro",
            comp_expires_at=datetime.now(UTC) + timedelta(days=body.duration_days),
            comp_reason=body.reason,
        )
        db.add(user)
    else:
        user.subscription_tier = "pro"
        user.comp_expires_at = datetime.now(UTC) + timedelta(days=body.duration_days)
        user.comp_reason = body.reason

    await db.commit()
    await db.refresh(user)

    logger.info(
        "Granted comp Pro to %s (%d) for %d days: %s",
        body.character_name,
        body.character_id,
        body.duration_days,
        body.reason,
    )

    return CompStatusResponse(
        character_id=user.character_id,
        character_name=user.character_name,
        subscription_tier=user.subscription_tier,
        comp_expires_at=user.comp_expires_at.isoformat() if user.comp_expires_at else None,
        comp_reason=user.comp_reason,
    )


@router.post(
    "/revoke-pro",
    response_model=CompStatusResponse,
    summary="Revoke comp Pro subscription",
)
async def revoke_pro(
    body: RevokeProRequest,
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
) -> CompStatusResponse:
    """Revoke a complimentary Pro subscription."""
    result = await db.execute(select(User).where(User.character_id == body.character_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Only revoke if it's a comp (don't touch Stripe subs)
    if user.stripe_subscription_id:
        raise HTTPException(
            status_code=400,
            detail="User has an active Stripe subscription. Manage via Stripe dashboard.",
        )

    user.subscription_tier = "free"
    user.comp_expires_at = None
    user.comp_reason = None

    await db.commit()
    await db.refresh(user)

    logger.info("Revoked comp Pro from %s (%d)", user.character_name, user.character_id)

    return CompStatusResponse(
        character_id=user.character_id,
        character_name=user.character_name,
        subscription_tier=user.subscription_tier,
        comp_expires_at=None,
        comp_reason=None,
    )


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

PRO_MONTHLY_PRICE = 3.0  # $3/month


@router.get(
    "/analytics",
    response_model=AdminAnalyticsResponse,
    summary="Admin analytics dashboard data",
)
async def get_admin_analytics(
    _: str = Depends(verify_admin_secret),
    db: AsyncSession = Depends(get_db),
) -> AdminAnalyticsResponse:
    """Return analytics data: MRR, subscribers, DAU, feature usage, popular endpoints."""
    now = datetime.now(UTC)

    # Count active Stripe subscribers (have subscription ID)
    result = await db.execute(
        select(func.count()).where(
            User.stripe_subscription_id.isnot(None),
            User.subscription_tier == "pro",
        )
    )
    active_subscribers = result.scalar_one()

    # Count active comp users (tier=pro, no stripe sub, not expired)
    result = await db.execute(
        select(func.count()).where(
            User.subscription_tier == "pro",
            User.stripe_subscription_id.is_(None),
            (User.comp_expires_at.is_(None) | (User.comp_expires_at > now)),
        )
    )
    comp_users = result.scalar_one()

    # Total registered users
    result = await db.execute(select(func.count()).select_from(User))
    total_users = result.scalar_one()

    # MRR = active paying subscribers * $3
    mrr = active_subscribers * PRO_MONTHLY_PRICE

    # DAU estimate from in-memory IP tracker
    dau = get_dau_estimate()

    # Popular endpoints from in-memory tracker
    top_endpoints = get_top_endpoints(10)
    popular = [
        EndpointHit(endpoint=str(e["endpoint"]), count=int(e["count"])) for e in top_endpoints
    ]

    # Feature usage from in-memory counters
    usage = get_feature_usage()
    feature_usage = FeatureUsage(
        map_views=usage.get("map_views", 0),
        route_calculations=usage.get("route_calculations", 0),
        intel_lookups=usage.get("intel_lookups", 0),
        kill_feed_connections=usage.get("kill_feed_connections", 0),
    )

    logger.info("Admin analytics queried: %d subs, $%.2f MRR, %d DAU", active_subscribers, mrr, dau)

    return AdminAnalyticsResponse(
        active_subscribers=active_subscribers,
        mrr=mrr,
        comp_users=comp_users,
        total_users=total_users,
        dau_estimate=dau,
        popular_endpoints=popular,
        feature_usage=feature_usage,
    )
