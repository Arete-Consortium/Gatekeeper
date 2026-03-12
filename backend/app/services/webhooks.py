"""Webhook service for Discord and Slack notifications.

Subscriptions are stored in PostgreSQL and cached in-memory for fast dispatch.
"""

import asyncio
import logging
from datetime import UTC, datetime
from enum import StrEnum

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..core.config import settings
from ..db.database import get_session_factory
from ..db.models import WebhookSubscriptionDB

logger = logging.getLogger(__name__)


class WebhookType(StrEnum):
    """Supported webhook types."""

    discord = "discord"
    slack = "slack"


class KillAlert(BaseModel):
    """Kill event for alerting."""

    kill_id: int
    system_name: str
    system_id: int
    region_id: int | None = None
    region_name: str | None = None
    ship_type: str | None = None
    ship_type_id: int | None = None
    victim_name: str | None = None
    victim_corp: str | None = None
    victim_alliance: str | None = None
    attacker_count: int = 0
    total_value: float | None = None
    is_pod: bool = False
    is_npc: bool = False
    kill_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    zkill_url: str | None = None


class WebhookSubscription(BaseModel):
    """Webhook subscription for kill alerts."""

    id: str
    webhook_url: str
    webhook_type: WebhookType
    systems: list[str] = Field(default_factory=list)  # Empty = all systems
    regions: list[int] = Field(default_factory=list)  # Region IDs to watch
    min_value: float | None = None  # Minimum ISK value
    include_pods: bool = False
    ship_types: list[str] = Field(default_factory=list)  # Ship types to watch
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    name: str | None = None  # Optional friendly name


# In-memory cache of subscriptions (loaded from DB on startup)
_subscriptions: dict[str, WebhookSubscription] = {}


def _db_row_to_subscription(row: WebhookSubscriptionDB) -> WebhookSubscription:
    """Convert DB row to Pydantic model."""
    return WebhookSubscription(
        id=row.id,
        webhook_url=row.webhook_url,
        webhook_type=WebhookType(row.webhook_type),
        systems=row.systems or [],
        regions=row.regions or [],
        min_value=row.min_value,
        include_pods=row.include_pods,
        ship_types=row.ship_types or [],
        enabled=row.enabled,
        created_at=row.created_at,
        name=row.name,
    )


def _subscription_to_db(sub: WebhookSubscription) -> WebhookSubscriptionDB:
    """Convert Pydantic model to DB row."""
    return WebhookSubscriptionDB(
        id=sub.id,
        webhook_url=sub.webhook_url,
        webhook_type=sub.webhook_type.value,
        name=sub.name,
        systems=list(sub.systems),
        regions=list(sub.regions),
        min_value=sub.min_value,
        include_pods=sub.include_pods,
        ship_types=list(sub.ship_types),
        enabled=sub.enabled,
        created_at=sub.created_at,
    )


async def load_subscriptions_from_db() -> None:
    """Load all subscriptions from database into in-memory cache."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(select(WebhookSubscriptionDB))
            rows = result.scalars().all()
            for row in rows:
                sub = _db_row_to_subscription(row)
                _subscriptions[sub.id] = sub
            logger.info(f"Loaded {len(rows)} webhook subscriptions from database")
    except Exception as e:
        logger.warning(f"Could not load webhook subscriptions from DB: {e}")


async def _save_subscription_to_db(sub: WebhookSubscription) -> None:
    """Persist a subscription to database."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            db_row = _subscription_to_db(sub)
            await session.merge(db_row)
            await session.commit()
    except Exception as e:
        logger.warning(f"Could not save webhook subscription {sub.id} to DB: {e}")


async def _delete_subscription_from_db(subscription_id: str) -> None:
    """Delete a subscription from database."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(WebhookSubscriptionDB).where(WebhookSubscriptionDB.id == subscription_id)
            )
            row = result.scalar_one_or_none()
            if row:
                await session.delete(row)
                await session.commit()
    except Exception as e:
        logger.warning(f"Could not delete webhook subscription {subscription_id} from DB: {e}")


def _format_discord_embed(alert: KillAlert) -> dict:
    """Format kill alert as Discord embed."""
    color = 0xFF0000 if alert.is_pod else 0x00FF00  # Red for pods, green for ships

    value_str = ""
    if alert.total_value:
        if alert.total_value >= 1_000_000_000:
            value_str = f"{alert.total_value / 1_000_000_000:.2f}B ISK"
        elif alert.total_value >= 1_000_000:
            value_str = f"{alert.total_value / 1_000_000:.2f}M ISK"
        else:
            value_str = f"{alert.total_value:,.0f} ISK"

    fields = [
        {"name": "System", "value": alert.system_name, "inline": True},
        {"name": "Attackers", "value": str(alert.attacker_count), "inline": True},
    ]

    if alert.ship_type:
        fields.append({"name": "Ship", "value": alert.ship_type, "inline": True})

    if value_str:
        fields.append({"name": "Value", "value": value_str, "inline": True})

    if alert.victim_corp:
        fields.append({"name": "Corp", "value": alert.victim_corp, "inline": True})

    title = f"{'Pod' if alert.is_pod else 'Kill'}: {alert.victim_name or 'Unknown'}"

    embed = {
        "title": title,
        "color": color,
        "fields": fields,
        "timestamp": alert.kill_time.isoformat(),
        "footer": {"text": "EVE Gatekeeper"},
    }

    if alert.zkill_url:
        embed["url"] = alert.zkill_url

    return {"embeds": [embed]}


def _format_slack_message(alert: KillAlert) -> dict:
    """Format kill alert as Slack message."""
    value_str = ""
    if alert.total_value:
        if alert.total_value >= 1_000_000_000:
            value_str = f" ({alert.total_value / 1_000_000_000:.2f}B ISK)"
        elif alert.total_value >= 1_000_000:
            value_str = f" ({alert.total_value / 1_000_000:.2f}M ISK)"

    icon = ":skull:" if alert.is_pod else ":boom:"
    ship_info = f" in {alert.ship_type}" if alert.ship_type else ""

    text = (
        f"{icon} *{'Pod' if alert.is_pod else 'Kill'}*: "
        f"{alert.victim_name or 'Unknown'}{ship_info} "
        f"in *{alert.system_name}*{value_str}"
    )

    if alert.zkill_url:
        text += f"\n<{alert.zkill_url}|View on zKillboard>"

    return {
        "text": text,
        "unfurl_links": False,
    }


async def send_webhook(
    url: str,
    webhook_type: WebhookType,
    alert: KillAlert,
) -> bool:
    """Send alert to a webhook. Returns True if successful."""
    try:
        if webhook_type == WebhookType.discord:
            payload = _format_discord_embed(alert)
        else:
            payload = _format_slack_message(alert)

        async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.debug(f"Webhook sent successfully to {webhook_type.value}")
            return True

    except httpx.TimeoutException:
        logger.warning(f"Webhook timeout for {webhook_type.value}")
        return False
    except httpx.HTTPStatusError as e:
        logger.warning(f"Webhook HTTP error for {webhook_type.value}: {e.response.status_code}")
        return False
    except Exception as e:
        logger.exception(f"Webhook error for {webhook_type.value}: {e}")
        return False


def _should_alert(subscription: WebhookSubscription, alert: KillAlert) -> bool:
    """Check if alert matches subscription criteria."""
    if not subscription.enabled:
        return False

    # System/region filtering: if any location filter is set, at least one must match
    if subscription.systems or subscription.regions:
        system_ok = alert.system_name in subscription.systems if subscription.systems else False
        region_ok = (
            (alert.region_id is not None and alert.region_id in subscription.regions)
            if subscription.regions
            else False
        )
        if not (system_ok or region_ok):
            return False

    # Pod filter
    if alert.is_pod and not subscription.include_pods:
        return False

    # Value filter
    if subscription.min_value and (alert.total_value or 0) < subscription.min_value:
        return False

    # Ship type filter
    if subscription.ship_types and alert.ship_type:
        ship_match = any(st.lower() in alert.ship_type.lower() for st in subscription.ship_types)
        if not ship_match:
            return False

    return True


async def dispatch_alert(alert: KillAlert) -> int:
    """Dispatch alert to all matching subscriptions. Returns count of successful sends."""
    tasks = []

    for subscription in _subscriptions.values():
        if _should_alert(subscription, alert):
            tasks.append(send_webhook(subscription.webhook_url, subscription.webhook_type, alert))

    if not tasks:
        return 0

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return sum(1 for r in results if r is True)


# Subscription management (write-through: update in-memory + persist to DB)


async def add_subscription(subscription: WebhookSubscription) -> None:
    """Add a webhook subscription (persisted to DB)."""
    _subscriptions[subscription.id] = subscription
    await _save_subscription_to_db(subscription)
    logger.info(f"Added webhook subscription: {subscription.id}")


async def remove_subscription(subscription_id: str) -> bool:
    """Remove a webhook subscription. Returns True if found and removed."""
    if subscription_id in _subscriptions:
        del _subscriptions[subscription_id]
        await _delete_subscription_from_db(subscription_id)
        logger.info(f"Removed webhook subscription: {subscription_id}")
        return True
    return False


def get_subscription(subscription_id: str) -> WebhookSubscription | None:
    """Get a subscription by ID."""
    return _subscriptions.get(subscription_id)


def list_subscriptions() -> list[WebhookSubscription]:
    """List all subscriptions."""
    return list(_subscriptions.values())


def clear_subscriptions() -> None:
    """Clear all subscriptions (for testing)."""
    _subscriptions.clear()


# Initialize default subscriptions from settings
async def init_default_subscriptions() -> None:
    """Load persisted subscriptions from DB, then add env-based defaults."""
    await load_subscriptions_from_db()

    if settings.DISCORD_WEBHOOK_URL and "default-discord" not in _subscriptions:
        await add_subscription(
            WebhookSubscription(
                id="default-discord",
                webhook_url=settings.DISCORD_WEBHOOK_URL,
                webhook_type=WebhookType.discord,
                systems=[],
                include_pods=True,
            )
        )

    if settings.SLACK_WEBHOOK_URL and "default-slack" not in _subscriptions:
        await add_subscription(
            WebhookSubscription(
                id="default-slack",
                webhook_url=settings.SLACK_WEBHOOK_URL,
                webhook_type=WebhookType.slack,
                systems=[],
                include_pods=True,
            )
        )
