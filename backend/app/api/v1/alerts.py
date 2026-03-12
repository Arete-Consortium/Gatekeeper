"""Alerts API v1 endpoints.

Provides endpoints for managing kill alert subscriptions via webhooks.
"""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from ...services.webhooks import (
    KillAlert,
    WebhookSubscription,
    WebhookType,
    add_subscription,
    dispatch_alert,
    get_subscription,
    list_subscriptions,
    remove_subscription,
)
from .dependencies import AuthenticatedCharacter, require_pro

router = APIRouter(prefix="/alerts", tags=["alerts"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateSubscriptionRequest(BaseModel):
    """Request to create a webhook subscription."""

    webhook_url: HttpUrl = Field(..., description="Discord or Slack webhook URL")
    webhook_type: str = Field("discord", description="Webhook type: discord or slack")
    name: str | None = Field(None, description="Friendly name for this subscription")
    systems: list[str] = Field(
        default_factory=list, description="System names to watch (empty = all)"
    )
    regions: list[int] = Field(
        default_factory=list, description="Region IDs to watch (empty = all)"
    )
    min_value: float | None = Field(None, description="Minimum ISK value for alerts")
    include_pods: bool = Field(False, description="Include pod kills")
    ship_types: list[str] = Field(
        default_factory=list, description="Ship types to filter (partial match)"
    )


class UpdateSubscriptionRequest(BaseModel):
    """Request to update a subscription."""

    name: str | None = None
    systems: list[str] | None = None
    regions: list[int] | None = None
    min_value: float | None = None
    include_pods: bool | None = None
    ship_types: list[str] | None = None
    enabled: bool | None = None


class SubscriptionResponse(BaseModel):
    """Response model for a subscription."""

    id: str
    name: str | None
    webhook_type: str
    systems: list[str]
    regions: list[int]
    min_value: float | None
    include_pods: bool
    ship_types: list[str]
    enabled: bool
    created_at: datetime

    @classmethod
    def from_subscription(cls, sub: WebhookSubscription) -> "SubscriptionResponse":
        """Create from WebhookSubscription."""
        return cls(
            id=sub.id,
            name=sub.name,
            webhook_type=sub.webhook_type.value,
            systems=sub.systems,
            regions=sub.regions,
            min_value=sub.min_value,
            include_pods=sub.include_pods,
            ship_types=sub.ship_types,
            enabled=sub.enabled,
            created_at=sub.created_at,
        )


class SubscriptionListResponse(BaseModel):
    """Response listing subscriptions."""

    total: int
    subscriptions: list[SubscriptionResponse]


class SendTestAlertRequest(BaseModel):
    """Request to send a test alert."""

    system_name: str = Field("Jita", description="System name for test")
    ship_type: str | None = Field("Caracal", description="Ship type")
    total_value: float | None = Field(100000000, description="ISK value")


class SendTestAlertResponse(BaseModel):
    """Response from test alert."""

    sent_count: int
    message: str


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    summary="Create subscription",
    description="Create a webhook subscription for kill alerts.",
)
async def create_subscription(
    request: CreateSubscriptionRequest,
    _character: AuthenticatedCharacter = Depends(require_pro),
) -> SubscriptionResponse:
    """
    Create a new webhook subscription.

    Supports Discord and Slack webhooks. Configure filters to receive
    alerts for specific systems, regions, ship types, or value thresholds.
    """
    try:
        webhook_type = WebhookType(request.webhook_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid webhook type: {request.webhook_type}. Valid: discord, slack",
        ) from None

    # Generate unique ID
    sub_id = secrets.token_urlsafe(8)

    subscription = WebhookSubscription(
        id=sub_id,
        webhook_url=str(request.webhook_url),
        webhook_type=webhook_type,
        name=request.name,
        systems=request.systems,
        regions=request.regions,
        min_value=request.min_value,
        include_pods=request.include_pods,
        ship_types=request.ship_types,
    )

    await add_subscription(subscription)
    return SubscriptionResponse.from_subscription(subscription)


@router.get(
    "/subscriptions",
    response_model=SubscriptionListResponse,
    summary="List subscriptions",
    description="List all webhook subscriptions.",
)
async def list_all_subscriptions() -> SubscriptionListResponse:
    """List all active webhook subscriptions."""
    subs = list_subscriptions()
    return SubscriptionListResponse(
        total=len(subs),
        subscriptions=[SubscriptionResponse.from_subscription(s) for s in subs],
    )


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get subscription",
    description="Get a specific subscription by ID.",
)
async def get_subscription_by_id(subscription_id: str) -> SubscriptionResponse:
    """Get a subscription by its ID."""
    sub = get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
    return SubscriptionResponse.from_subscription(sub)


@router.patch(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update subscription",
    description="Update a subscription's settings.",
)
async def update_subscription_by_id(
    subscription_id: str,
    request: UpdateSubscriptionRequest,
) -> SubscriptionResponse:
    """Update a subscription's configuration."""
    sub = get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")

    # Update fields
    if request.name is not None:
        sub.name = request.name
    if request.systems is not None:
        sub.systems = request.systems
    if request.regions is not None:
        sub.regions = request.regions
    if request.min_value is not None:
        sub.min_value = request.min_value
    if request.include_pods is not None:
        sub.include_pods = request.include_pods
    if request.ship_types is not None:
        sub.ship_types = request.ship_types
    if request.enabled is not None:
        sub.enabled = request.enabled

    return SubscriptionResponse.from_subscription(sub)


@router.delete(
    "/subscriptions/{subscription_id}",
    summary="Delete subscription",
    description="Delete a webhook subscription.",
)
async def delete_subscription_by_id(subscription_id: str) -> dict[str, str]:
    """Delete a subscription."""
    if not await remove_subscription(subscription_id):
        raise HTTPException(status_code=404, detail=f"Subscription not found: {subscription_id}")
    return {"status": "deleted", "id": subscription_id}


@router.post(
    "/test",
    response_model=SendTestAlertResponse,
    summary="Send test alert",
    description="Send a test kill alert to all enabled subscriptions.",
)
async def send_test_alert(request: SendTestAlertRequest) -> SendTestAlertResponse:
    """
    Send a test alert to verify webhook configuration.

    Creates a fake kill alert and dispatches it to all matching subscriptions.
    """
    alert = KillAlert(
        kill_id=0,
        system_name=request.system_name,
        system_id=30000142,  # Jita
        ship_type=request.ship_type,
        victim_name="Test Pilot",
        victim_corp="Test Corp",
        attacker_count=5,
        total_value=request.total_value,
        zkill_url="https://zkillboard.com/kill/0/",
    )

    sent_count = await dispatch_alert(alert)

    return SendTestAlertResponse(
        sent_count=sent_count,
        message=f"Test alert sent to {sent_count} subscription(s)",
    )


@router.get(
    "/stats",
    summary="Get alert stats",
    description="Get statistics about alert subscriptions.",
)
async def get_alert_stats() -> dict:
    """Get statistics about alert subscriptions."""
    subs = list_subscriptions()
    enabled = sum(1 for s in subs if s.enabled)
    by_type: dict[str, int] = {}
    for s in subs:
        by_type[s.webhook_type.value] = by_type.get(s.webhook_type.value, 0) + 1

    return {
        "total_subscriptions": len(subs),
        "enabled_subscriptions": enabled,
        "by_webhook_type": by_type,
    }
