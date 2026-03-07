"""Stripe Billing Service for EVE Gatekeeper Pro subscriptions.

Handles:
- Checkout session creation for Pro upgrades
- Billing portal session for subscription management
- Webhook handling for subscription lifecycle events
- Subscription status queries
"""

import logging
from datetime import UTC, datetime
from typing import Any

import stripe
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models import User

logger = logging.getLogger(__name__)


def _configure_stripe() -> None:
    """Set Stripe API key from settings."""
    if settings.STRIPE_SECRET_KEY:
        stripe.api_key = settings.STRIPE_SECRET_KEY


def is_configured() -> bool:
    """Check if Stripe is properly configured."""
    _configure_stripe()
    return bool(stripe.api_key)


async def get_or_create_customer(
    db: AsyncSession,
    character_id: int,
    character_name: str,
) -> str:
    """Get existing Stripe customer ID or create a new customer.

    Returns:
        Stripe Customer ID
    """
    result = await db.execute(select(User).where(User.character_id == character_id))
    user = result.scalar_one_or_none()

    if user and user.stripe_customer_id:
        return user.stripe_customer_id

    # Create new Stripe customer
    customer = stripe.Customer.create(
        metadata={
            "character_id": str(character_id),
            "character_name": character_name,
        },
    )

    # Store customer ID
    if user:
        user.stripe_customer_id = customer.id
        await db.flush()

    return customer.id


async def create_checkout_session(
    db: AsyncSession,
    character_id: int,
    character_name: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session for Pro subscription.

    Returns:
        Checkout session URL for redirecting the user.

    Raises:
        ValueError: If Stripe is not configured or price ID missing.
        stripe.error.StripeError: If Stripe API call fails.
    """
    if not is_configured():
        raise ValueError("Stripe is not configured. Set STRIPE_SECRET_KEY.")

    if not settings.STRIPE_PRO_MONTHLY_PRICE_ID:
        raise ValueError("STRIPE_PRO_MONTHLY_PRICE_ID not configured.")

    customer_id = await get_or_create_customer(db, character_id, character_name)

    metadata = {"character_id": str(character_id)}

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[
            {
                "price": settings.STRIPE_PRO_MONTHLY_PRICE_ID,
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
        subscription_data={
            "metadata": metadata,
        },
    )

    logger.info("Created checkout session for character %d", character_id)
    if not session.url:
        raise ValueError("Stripe checkout session did not return a URL")
    return session.url


async def create_portal_session(
    db: AsyncSession,
    character_id: int,
    return_url: str,
) -> str:
    """Create a Stripe Billing Portal session.

    Returns:
        Billing portal URL.

    Raises:
        ValueError: If Stripe is not configured or user has no customer ID.
    """
    if not is_configured():
        raise ValueError("Stripe is not configured. Set STRIPE_SECRET_KEY.")

    result = await db.execute(select(User).where(User.character_id == character_id))
    user = result.scalar_one_or_none()

    if not user or not user.stripe_customer_id:
        raise ValueError("No Stripe customer found for this character.")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )

    logger.info("Created portal session for character %d", character_id)
    return session.url


async def handle_webhook(payload: bytes, sig_header: str) -> dict[str, Any]:
    """Handle Stripe webhook events.

    Processes:
    - checkout.session.completed: User completed checkout
    - customer.subscription.updated: Subscription status changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_failed: Payment failure (logged, not actioned)

    Returns:
        Dict with event type and processing status.

    Raises:
        ValueError: If webhook signature verification fails.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ValueError("Webhook secret not configured.")

    _configure_stripe()

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.error("Webhook signature verification failed")
        raise ValueError("Invalid webhook signature") from None

    event_type = event["type"]
    data = event["data"]["object"]

    logger.info("Processing webhook event: %s", event_type)

    if event_type == "checkout.session.completed":
        return await _handle_checkout_completed(data)
    elif event_type == "customer.subscription.updated":
        return await _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        return await _handle_subscription_deleted(data)
    elif event_type == "invoice.payment_failed":
        return _handle_payment_failed(data)
    else:
        return {"event_type": event_type, "processed": False, "reason": "unhandled_event"}


async def get_subscription_status(
    db: AsyncSession,
    character_id: int,
) -> dict[str, Any]:
    """Get subscription status for a character.

    Returns:
        Dict with tier, status, and Stripe subscription details.
    """
    result = await db.execute(select(User).where(User.character_id == character_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"tier": "free", "status": "no_account"}

    base = {
        "tier": user.subscription_tier,
        "character_id": user.character_id,
        "character_name": user.character_name,
    }

    if not user.stripe_customer_id or not is_configured():
        return {**base, "status": "local_only"}

    # Fetch live status from Stripe
    try:
        subscriptions = stripe.Subscription.list(
            customer=user.stripe_customer_id, status="all", limit=1
        )

        if not subscriptions.data:
            return {**base, "status": "none"}

        sub = subscriptions.data[0]
        return {
            **base,
            "status": sub.status,
            "subscription_id": sub.id,
            "current_period_end": datetime.fromtimestamp(
                sub.current_period_end,  # type: ignore[attr-defined]
                tz=UTC,
            ).isoformat(),
            "cancel_at_period_end": sub.cancel_at_period_end,
        }
    except stripe.error.StripeError as e:
        logger.error("Failed to get subscription status: %s", e)
        return {**base, "status": "error"}


# ---------------------------------------------------------------------------
# Internal webhook handlers
# ---------------------------------------------------------------------------


async def _handle_checkout_completed(data: dict) -> dict[str, Any]:
    """Handle checkout.session.completed — upgrade user to Pro."""
    character_id_str = data.get("metadata", {}).get("character_id")
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")

    if not character_id_str:
        logger.warning("Checkout completed without character_id in metadata")
        return {
            "event_type": "checkout.session.completed",
            "processed": False,
            "reason": "no_character_id",
        }

    character_id = int(character_id_str)

    from ..db.database import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            update(User)
            .where(User.character_id == character_id)
            .values(
                subscription_tier="pro",
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                updated_at=datetime.now(UTC),
            )
        )
        await session.execute(stmt)
        await session.commit()

    logger.info("Character %d upgraded to Pro via checkout", character_id)
    return {
        "event_type": "checkout.session.completed",
        "processed": True,
        "character_id": character_id,
        "tier": "pro",
    }


async def _handle_subscription_updated(data: dict) -> dict[str, Any]:
    """Handle customer.subscription.updated — sync tier with Stripe status."""
    subscription_id = data.get("id")
    status = data.get("status")
    character_id_str = data.get("metadata", {}).get("character_id")

    tier = "pro" if status in ("active", "trialing") else "free"

    if not character_id_str:
        logger.warning("Subscription %s updated but no character_id found", subscription_id)
        return {
            "event_type": "customer.subscription.updated",
            "processed": False,
            "reason": "no_character_id",
        }

    character_id = int(character_id_str)

    from ..db.database import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            update(User)
            .where(User.character_id == character_id)
            .values(subscription_tier=tier, updated_at=datetime.now(UTC))
        )
        await session.execute(stmt)
        await session.commit()

    logger.info("Character %d subscription updated: status=%s, tier=%s", character_id, status, tier)
    return {
        "event_type": "customer.subscription.updated",
        "processed": True,
        "character_id": character_id,
        "status": status,
        "tier": tier,
    }


async def _handle_subscription_deleted(data: dict) -> dict[str, Any]:
    """Handle customer.subscription.deleted — downgrade to free."""
    subscription_id = data.get("id")
    character_id_str = data.get("metadata", {}).get("character_id")

    if not character_id_str:
        logger.warning("Subscription %s deleted but no character_id found", subscription_id)
        return {
            "event_type": "customer.subscription.deleted",
            "processed": False,
            "reason": "no_character_id",
        }

    character_id = int(character_id_str)

    from ..db.database import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            update(User)
            .where(User.character_id == character_id)
            .values(
                subscription_tier="free",
                stripe_subscription_id=None,
                updated_at=datetime.now(UTC),
            )
        )
        await session.execute(stmt)
        await session.commit()

    logger.info("Character %d subscription cancelled, downgraded to free", character_id)
    return {
        "event_type": "customer.subscription.deleted",
        "processed": True,
        "character_id": character_id,
        "tier": "free",
    }


def _handle_payment_failed(data: dict) -> dict[str, Any]:
    """Handle invoice.payment_failed — log but don't downgrade (Stripe retries)."""
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    attempt_count = data.get("attempt_count", 0)

    logger.warning(
        "Payment failed for customer %s, subscription %s, attempt %d",
        customer_id,
        subscription_id,
        attempt_count,
    )

    return {
        "event_type": "invoice.payment_failed",
        "processed": True,
        "customer_id": customer_id,
        "attempt_count": attempt_count,
    }
