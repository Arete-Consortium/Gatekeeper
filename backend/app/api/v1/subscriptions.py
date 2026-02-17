"""Subscription management API endpoints."""

import logging

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...db.database import get_db
from ...services.stripe_service import (
    PLANS,
    create_checkout_session,
    create_portal_session,
    get_subscription_status,
    handle_webhook_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# ==================== Request/Response Models ====================


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    character_id: int
    character_name: str
    plan: str  # "monthly" or "annual"


class CheckoutResponse(BaseModel):
    """Checkout session URL."""

    checkout_url: str


class PortalRequest(BaseModel):
    """Request to create a customer portal session."""

    character_id: int


class PortalResponse(BaseModel):
    """Portal session URL."""

    portal_url: str


class PlanInfo(BaseModel):
    """Subscription plan details."""

    id: str
    name: str
    price: float
    interval: str


class PlansResponse(BaseModel):
    """Available subscription plans."""

    plans: list[PlanInfo]
    publishable_key: str | None


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status."""

    subscribed: bool
    plan: str | None = None
    status: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False


# ==================== Endpoints ====================


@router.get("/plans", response_model=PlansResponse)
async def get_plans():
    """Get available subscription plans and Stripe publishable key."""
    plans = [
        PlanInfo(
            id=plan_id,
            name=plan["name"],
            price=plan["price"],
            interval=plan["interval"],
        )
        for plan_id, plan in PLANS.items()
    ]
    return PlansResponse(
        plans=plans,
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for subscribing."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payment system not configured")

    try:
        url = await create_checkout_session(
            db=db,
            character_id=request.character_id,
            character_name=request.character_name,
            plan=request.plan,
        )
        return CheckoutResponse(checkout_url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.StripeError as e:
        logger.error("Stripe error during checkout", extra={"error": str(e)})
        raise HTTPException(status_code=502, detail="Payment provider error")


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    request: PortalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing subscription."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payment system not configured")

    try:
        url = await create_portal_session(db=db, character_id=request.character_id)
        return PortalResponse(portal_url=url)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except stripe.StripeError as e:
        logger.error("Stripe error creating portal", extra={"error": str(e)})
        raise HTTPException(status_code=502, detail="Payment provider error")


@router.get("/status/{character_id}", response_model=SubscriptionStatusResponse)
async def get_status(
    character_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get subscription status for a character."""
    sub = await get_subscription_status(db=db, character_id=character_id)

    if not sub:
        return SubscriptionStatusResponse(subscribed=False)

    return SubscriptionStatusResponse(
        subscribed=sub["status"] == "active",
        plan=sub["plan"],
        status=sub["status"],
        current_period_start=sub["current_period_start"],
        current_period_end=sub["current_period_end"],
        cancel_at_period_end=sub["cancel_at_period_end"],
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook not configured")

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    await handle_webhook_event(db=db, event=event)
    return {"status": "ok"}
