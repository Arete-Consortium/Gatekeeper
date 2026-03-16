"""Admin endpoints for managing comp Pro subscriptions."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.database import get_db
from ...db.models import User

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
