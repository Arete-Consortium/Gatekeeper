"""Webhook management API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from ...services.data_loader import load_universe
from ...services.webhooks import (
    KillAlert,
    WebhookSubscription,
    WebhookType,
    add_subscription,
    get_subscription,
    list_subscriptions,
    remove_subscription,
    send_webhook,
)

router = APIRouter()


class WebhookCreateRequest(BaseModel):
    """Request to create a webhook subscription."""

    webhook_url: HttpUrl = Field(..., description="Discord or Slack webhook URL")
    webhook_type: WebhookType = Field(..., description="Type of webhook (discord/slack)")
    systems: list[str] = Field(default_factory=list, description="Systems to watch (empty = all)")
    min_value: float | None = Field(None, ge=0, description="Minimum ISK value to alert")
    include_pods: bool = Field(False, description="Include pod kills")


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook subscription."""

    systems: list[str] | None = None
    min_value: float | None = None
    include_pods: bool | None = None
    enabled: bool | None = None


class WebhookResponse(BaseModel):
    """Response for a webhook subscription."""

    id: str
    webhook_type: WebhookType
    systems: list[str]
    min_value: float | None
    include_pods: bool
    enabled: bool
    created_at: datetime

    # Don't expose the actual URL for security
    webhook_url_preview: str = Field(description="Masked webhook URL")


class WebhookListResponse(BaseModel):
    """Response for listing webhooks."""

    total: int
    webhooks: list[WebhookResponse]


class WebhookTestRequest(BaseModel):
    """Request to test a webhook."""

    webhook_url: HttpUrl
    webhook_type: WebhookType


class WebhookTestResponse(BaseModel):
    """Response for webhook test."""

    success: bool
    message: str


def _mask_url(url: str) -> str:
    """Mask webhook URL for security."""
    if len(url) > 30:
        return url[:20] + "..." + url[-10:]
    return url[:10] + "..."


def _subscription_to_response(sub: WebhookSubscription) -> WebhookResponse:
    """Convert subscription to response model."""
    return WebhookResponse(
        id=sub.id,
        webhook_type=sub.webhook_type,
        systems=sub.systems,
        min_value=sub.min_value,
        include_pods=sub.include_pods,
        enabled=sub.enabled,
        created_at=sub.created_at,
        webhook_url_preview=_mask_url(sub.webhook_url),
    )


@router.get(
    "/",
    response_model=WebhookListResponse,
    summary="List webhook subscriptions",
    description="Returns all configured webhook subscriptions.",
)
def list_webhooks() -> WebhookListResponse:
    """List all webhook subscriptions."""
    subs = list_subscriptions()
    return WebhookListResponse(
        total=len(subs),
        webhooks=[_subscription_to_response(s) for s in subs],
    )


@router.post(
    "/",
    response_model=WebhookResponse,
    status_code=201,
    summary="Create webhook subscription",
    description="Create a new webhook subscription for kill alerts.",
)
async def create_webhook(request: WebhookCreateRequest) -> WebhookResponse:
    """Create a new webhook subscription."""
    universe = load_universe()

    # Validate systems
    for system in request.systems:
        if system not in universe.systems:
            raise HTTPException(status_code=400, detail=f"Unknown system: {system}")

    subscription = WebhookSubscription(
        id=str(uuid.uuid4()),
        webhook_url=str(request.webhook_url),
        webhook_type=request.webhook_type,
        systems=request.systems,
        min_value=request.min_value,
        include_pods=request.include_pods,
    )

    await add_subscription(subscription)
    return _subscription_to_response(subscription)


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook subscription",
    description="Get a specific webhook subscription.",
)
def get_webhook(webhook_id: str) -> WebhookResponse:
    """Get a webhook subscription by ID."""
    sub = get_subscription(webhook_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return _subscription_to_response(sub)


@router.patch(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update webhook subscription",
    description="Update a webhook subscription.",
)
def update_webhook(webhook_id: str, request: WebhookUpdateRequest) -> WebhookResponse:
    """Update a webhook subscription."""
    sub = get_subscription(webhook_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")

    universe = load_universe()

    # Validate systems if provided
    if request.systems is not None:
        for system in request.systems:
            if system not in universe.systems:
                raise HTTPException(status_code=400, detail=f"Unknown system: {system}")
        sub.systems = request.systems

    if request.min_value is not None:
        sub.min_value = request.min_value

    if request.include_pods is not None:
        sub.include_pods = request.include_pods

    if request.enabled is not None:
        sub.enabled = request.enabled

    return _subscription_to_response(sub)


@router.delete(
    "/{webhook_id}",
    status_code=204,
    summary="Delete webhook subscription",
    description="Delete a webhook subscription.",
)
async def delete_webhook(webhook_id: str) -> None:
    """Delete a webhook subscription."""
    if not await remove_subscription(webhook_id):
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post(
    "/test",
    response_model=WebhookTestResponse,
    summary="Test webhook",
    description="Send a test message to a webhook URL.",
)
async def send_test_message(request: WebhookTestRequest) -> WebhookTestResponse:
    """Send a test message to verify webhook works."""
    test_alert = KillAlert(
        kill_id=0,
        system_name="Jita",
        system_id=30000142,
        ship_type="Test Ship",
        victim_name="Test Victim",
        victim_corp="Test Corporation",
        attacker_count=5,
        total_value=100_000_000,
        is_pod=False,
        zkill_url="https://zkillboard.com/kill/0/",
    )

    success = await send_webhook(str(request.webhook_url), request.webhook_type, test_alert)

    if success:
        return WebhookTestResponse(success=True, message="Test message sent successfully")
    else:
        return WebhookTestResponse(success=False, message="Failed to send test message")
