"""Stripe payment service for subscription management."""

import logging
from datetime import UTC, datetime

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models import Subscription

logger = logging.getLogger(__name__)

# Plans configuration
PLANS = {
    "monthly": {
        "name": "Monthly",
        "price": 2.99,
        "interval": "month",
        "price_id_setting": "STRIPE_MONTHLY_PRICE_ID",
    },
    "annual": {
        "name": "Annual",
        "price": 29.99,
        "interval": "year",
        "price_id_setting": "STRIPE_ANNUAL_PRICE_ID",
    },
}


def _configure_stripe() -> None:
    """Configure the Stripe API key."""
    if not settings.STRIPE_SECRET_KEY:
        raise ValueError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY


async def get_or_create_customer(
    db: AsyncSession, character_id: int, character_name: str
) -> str:
    """Get existing Stripe customer or create a new one."""
    _configure_stripe()

    # Check for existing subscription record with a customer ID
    result = await db.execute(
        select(Subscription).where(Subscription.character_id == character_id).limit(1)
    )
    existing = result.scalar_one_or_none()

    if existing and existing.stripe_customer_id:
        return existing.stripe_customer_id

    # Create new Stripe customer
    customer = stripe.Customer.create(
        metadata={
            "character_id": str(character_id),
            "character_name": character_name,
        },
    )
    logger.info(
        "Created Stripe customer",
        extra={"character_id": character_id, "customer_id": customer.id},
    )
    return customer.id


async def create_checkout_session(
    db: AsyncSession,
    character_id: int,
    character_name: str,
    plan: str,
) -> str:
    """Create a Stripe Checkout session and return the URL."""
    _configure_stripe()

    if plan not in PLANS:
        raise ValueError(f"Invalid plan: {plan}. Must be 'monthly' or 'annual'")

    price_id = getattr(settings, PLANS[plan]["price_id_setting"])
    if not price_id:
        raise ValueError(f"Stripe price ID not configured for {plan} plan")

    customer_id = await get_or_create_customer(db, character_id, character_name)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        metadata={
            "character_id": str(character_id),
            "plan": plan,
        },
        subscription_data={
            "metadata": {
                "character_id": str(character_id),
                "plan": plan,
            },
        },
    )

    logger.info(
        "Created checkout session",
        extra={"character_id": character_id, "plan": plan, "session_id": session.id},
    )
    return session.url


async def create_portal_session(db: AsyncSession, character_id: int) -> str:
    """Create a Stripe Customer Portal session for managing subscriptions."""
    _configure_stripe()

    result = await db.execute(
        select(Subscription).where(Subscription.character_id == character_id).limit(1)
    )
    sub = result.scalar_one_or_none()

    if not sub or not sub.stripe_customer_id:
        raise ValueError("No subscription found for this character")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=settings.STRIPE_SUCCESS_URL.replace("?subscription=success", ""),
    )
    return session.url


async def get_subscription_status(
    db: AsyncSession, character_id: int
) -> dict | None:
    """Get the current subscription status for a character."""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.character_id == character_id)
        .where(Subscription.status.in_(["active", "past_due", "canceled"]))
        .limit(1)
    )
    sub = result.scalar_one_or_none()

    if not sub:
        return None

    return {
        "plan": sub.plan,
        "status": sub.status,
        "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
    }


async def handle_webhook_event(db: AsyncSession, event: stripe.Event) -> None:
    """Process Stripe webhook events to keep subscription state in sync."""
    event_type = event.type
    data = event.data.object

    logger.info("Processing Stripe webhook", extra={"event_type": event_type})

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)
    elif event_type in (
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        await _handle_subscription_change(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)


async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    """Handle successful checkout - create or update subscription record."""
    character_id = int(session.get("metadata", {}).get("character_id", 0))
    plan = session.get("metadata", {}).get("plan", "monthly")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not character_id or not customer_id:
        logger.warning("Checkout completed but missing character_id or customer_id")
        return

    # Check for existing record
    result = await db.execute(
        select(Subscription).where(Subscription.character_id == character_id).limit(1)
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.stripe_customer_id = customer_id
        sub.stripe_subscription_id = subscription_id
        sub.plan = plan
        sub.status = "active"
        sub.updated_at = datetime.now(UTC)
    else:
        sub = Subscription(
            character_id=character_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            plan=plan,
            status="active",
        )
        db.add(sub)

    await db.flush()
    logger.info(
        "Subscription activated via checkout",
        extra={"character_id": character_id, "plan": plan},
    )


async def _handle_subscription_change(db: AsyncSession, subscription: dict) -> None:
    """Handle subscription updates or cancellation."""
    subscription_id = subscription.get("id")
    status = subscription.get("status")
    cancel_at_period_end = subscription.get("cancel_at_period_end", False)

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()

    if not sub:
        logger.warning(
            "Subscription change for unknown subscription",
            extra={"subscription_id": subscription_id},
        )
        return

    # Map Stripe status to our status
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "inactive",
        "incomplete_expired": "inactive",
    }
    sub.status = status_map.get(status, "inactive")
    sub.cancel_at_period_end = cancel_at_period_end

    # Update period dates
    period_start = subscription.get("current_period_start")
    period_end = subscription.get("current_period_end")
    if period_start:
        sub.current_period_start = datetime.fromtimestamp(period_start, tz=UTC)
    if period_end:
        sub.current_period_end = datetime.fromtimestamp(period_end, tz=UTC)

    sub.updated_at = datetime.now(UTC)
    await db.flush()

    logger.info(
        "Subscription updated",
        extra={
            "subscription_id": subscription_id,
            "status": sub.status,
            "cancel_at_period_end": cancel_at_period_end,
        },
    )


async def _handle_payment_failed(db: AsyncSession, invoice: dict) -> None:
    """Handle failed payment."""
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == subscription_id
        )
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.status = "past_due"
        sub.updated_at = datetime.now(UTC)
        await db.flush()

        logger.warning(
            "Payment failed for subscription",
            extra={"subscription_id": subscription_id, "character_id": sub.character_id},
        )
