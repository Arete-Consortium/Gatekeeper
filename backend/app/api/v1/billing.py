"""Billing endpoints for Stripe subscription management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_db
from ...services import stripe_service
from .dependencies import AuthenticatedCharacter, get_current_character

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class CheckoutResponse(BaseModel):
    """Stripe checkout session URL."""

    checkout_url: str


class PortalResponse(BaseModel):
    """Stripe billing portal URL."""

    portal_url: str


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status."""

    tier: str
    status: str
    character_id: int | None = None
    character_name: str | None = None
    subscription_id: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool | None = None


class CheckoutRequest(BaseModel):
    """Checkout session request."""

    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    """Portal session request."""

    return_url: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/create-checkout",
    response_model=CheckoutResponse,
    summary="Create Stripe checkout session",
)
async def create_checkout(
    body: CheckoutRequest,
    character: AuthenticatedCharacter = Depends(get_current_character),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for Pro subscription upgrade."""
    if not stripe_service.is_configured():
        raise HTTPException(status_code=503, detail="Billing not configured")

    try:
        url = await stripe_service.create_checkout_session(
            db=db,
            character_id=character.character_id,
            character_name=character.character_name,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        return CheckoutResponse(checkout_url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post(
    "/create-portal",
    response_model=PortalResponse,
    summary="Create Stripe billing portal session",
)
async def create_portal(
    body: PortalRequest,
    character: AuthenticatedCharacter = Depends(get_current_character),
    db: AsyncSession = Depends(get_db),
) -> PortalResponse:
    """Create a Stripe Billing Portal session for subscription management."""
    if not stripe_service.is_configured():
        raise HTTPException(status_code=503, detail="Billing not configured")

    try:
        url = await stripe_service.create_portal_session(
            db=db,
            character_id=character.character_id,
            return_url=body.return_url,
        )
        return PortalResponse(portal_url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post(
    "/webhook",
    summary="Stripe webhook handler",
)
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events. Signature-verified, no auth required."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        result = await stripe_service.handle_webhook(payload, sig_header)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/status",
    response_model=SubscriptionStatusResponse,
    summary="Get subscription status",
)
async def get_billing_status(
    character: AuthenticatedCharacter = Depends(get_current_character),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionStatusResponse:
    """Get the current subscription status for the authenticated character."""
    status = await stripe_service.get_subscription_status(db, character.character_id)
    return SubscriptionStatusResponse(**status)
