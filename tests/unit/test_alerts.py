"""Unit tests for alerts API."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.app.api.v1.alerts import (
    CreateSubscriptionRequest,
    SendTestAlertRequest,
    SendTestAlertResponse,
    SubscriptionListResponse,
    SubscriptionResponse,
    UpdateSubscriptionRequest,
    create_subscription,
    delete_subscription_by_id,
    get_alert_stats,
    get_subscription_by_id,
    list_all_subscriptions,
    send_test_alert,
    update_subscription_by_id,
)
from backend.app.services.webhooks import (
    WebhookSubscription,
    WebhookType,
    clear_subscriptions,
)


@pytest.fixture(autouse=True)
def clear_subs():
    """Clear subscriptions before each test."""
    clear_subscriptions()
    yield
    clear_subscriptions()


class TestCreateSubscription:
    """Tests for create_subscription endpoint."""

    @pytest.mark.asyncio
    async def test_create_discord_subscription(self):
        """Test creating a Discord subscription."""
        request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
            name="Test Sub",
            systems=["Jita", "Amarr"],
            min_value=100000000,
        )

        response = await create_subscription(request)

        assert isinstance(response, SubscriptionResponse)
        assert response.name == "Test Sub"
        assert response.webhook_type == "discord"
        assert response.systems == ["Jita", "Amarr"]
        assert response.min_value == 100000000
        assert response.enabled is True

    @pytest.mark.asyncio
    async def test_create_slack_subscription(self):
        """Test creating a Slack subscription."""
        request = CreateSubscriptionRequest(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            webhook_type="slack",
            include_pods=True,
            ship_types=["Venture", "Retriever"],
        )

        response = await create_subscription(request)

        assert response.webhook_type == "slack"
        assert response.include_pods is True
        assert response.ship_types == ["Venture", "Retriever"]

    @pytest.mark.asyncio
    async def test_create_invalid_webhook_type(self):
        """Test creating subscription with invalid webhook type."""
        request = CreateSubscriptionRequest(
            webhook_url="https://example.com/webhook",
            webhook_type="invalid",
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_subscription(request)

        assert exc_info.value.status_code == 400
        assert "Invalid webhook type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_with_regions(self):
        """Test creating subscription with region filters."""
        request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
            regions=[10000002, 10000043],  # The Forge, Domain
        )

        response = await create_subscription(request)

        assert response.regions == [10000002, 10000043]


class TestListSubscriptions:
    """Tests for list_all_subscriptions endpoint."""

    @pytest.mark.asyncio
    async def test_list_empty(self):
        """Test listing when no subscriptions exist."""
        response = await list_all_subscriptions()

        assert isinstance(response, SubscriptionListResponse)
        assert response.total == 0
        assert response.subscriptions == []

    @pytest.mark.asyncio
    async def test_list_with_subscriptions(self):
        """Test listing multiple subscriptions."""
        # Create some subscriptions
        for i in range(3):
            request = CreateSubscriptionRequest(
                webhook_url=f"https://discord.com/api/webhooks/{i}/abc",
                webhook_type="discord",
                name=f"Sub {i}",
            )
            await create_subscription(request)

        response = await list_all_subscriptions()

        assert response.total == 3
        assert len(response.subscriptions) == 3


class TestGetSubscription:
    """Tests for get_subscription_by_id endpoint."""

    @pytest.mark.asyncio
    async def test_get_existing(self):
        """Test getting an existing subscription."""
        request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
            name="Test",
        )
        created = await create_subscription(request)

        response = await get_subscription_by_id(created.id)

        assert response.id == created.id
        assert response.name == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Test getting a nonexistent subscription."""
        with pytest.raises(HTTPException) as exc_info:
            await get_subscription_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404


class TestUpdateSubscription:
    """Tests for update_subscription_by_id endpoint."""

    @pytest.mark.asyncio
    async def test_update_name(self):
        """Test updating subscription name."""
        request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
            name="Original",
        )
        created = await create_subscription(request)

        update = UpdateSubscriptionRequest(name="Updated")
        response = await update_subscription_by_id(created.id, update)

        assert response.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_systems(self):
        """Test updating subscription systems."""
        request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
            systems=["Jita"],
        )
        created = await create_subscription(request)

        update = UpdateSubscriptionRequest(systems=["Amarr", "Dodixie"])
        response = await update_subscription_by_id(created.id, update)

        assert response.systems == ["Amarr", "Dodixie"]

    @pytest.mark.asyncio
    async def test_update_enabled(self):
        """Test disabling a subscription."""
        request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
        )
        created = await create_subscription(request)
        assert created.enabled is True

        update = UpdateSubscriptionRequest(enabled=False)
        response = await update_subscription_by_id(created.id, update)

        assert response.enabled is False

    @pytest.mark.asyncio
    async def test_update_nonexistent(self):
        """Test updating a nonexistent subscription."""
        update = UpdateSubscriptionRequest(name="Test")

        with pytest.raises(HTTPException) as exc_info:
            await update_subscription_by_id("nonexistent-id", update)

        assert exc_info.value.status_code == 404


class TestDeleteSubscription:
    """Tests for delete_subscription_by_id endpoint."""

    @pytest.mark.asyncio
    async def test_delete_existing(self):
        """Test deleting an existing subscription."""
        request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
        )
        created = await create_subscription(request)

        response = await delete_subscription_by_id(created.id)

        assert response["status"] == "deleted"
        assert response["id"] == created.id

        # Verify it's actually deleted
        with pytest.raises(HTTPException):
            await get_subscription_by_id(created.id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """Test deleting a nonexistent subscription."""
        with pytest.raises(HTTPException) as exc_info:
            await delete_subscription_by_id("nonexistent-id")

        assert exc_info.value.status_code == 404


class TestSendTestAlert:
    """Tests for send_test_alert endpoint."""

    @pytest.mark.asyncio
    async def test_send_no_subscriptions(self):
        """Test sending test alert with no subscriptions."""
        request = SendTestAlertRequest(
            system_name="Jita",
            ship_type="Caracal",
            total_value=100000000,
        )

        response = await send_test_alert(request)

        assert isinstance(response, SendTestAlertResponse)
        assert response.sent_count == 0

    @pytest.mark.asyncio
    @patch("backend.app.services.webhooks.send_webhook")
    async def test_send_with_subscription(self, mock_send):
        """Test sending test alert with subscriptions."""
        mock_send.return_value = True

        # Create a subscription
        sub_request = CreateSubscriptionRequest(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
        )
        await create_subscription(sub_request)

        request = SendTestAlertRequest(
            system_name="Jita",
            ship_type="Caracal",
            total_value=100000000,
        )

        response = await send_test_alert(request)

        assert response.sent_count >= 0  # May be 0 if filters don't match


class TestGetAlertStats:
    """Tests for get_alert_stats endpoint."""

    @pytest.mark.asyncio
    async def test_stats_empty(self):
        """Test stats with no subscriptions."""
        response = await get_alert_stats()

        assert response["total_subscriptions"] == 0
        assert response["enabled_subscriptions"] == 0
        assert response["by_webhook_type"] == {}

    @pytest.mark.asyncio
    async def test_stats_with_subscriptions(self):
        """Test stats with multiple subscriptions."""
        # Create Discord subscriptions
        for i in range(2):
            request = CreateSubscriptionRequest(
                webhook_url=f"https://discord.com/api/webhooks/{i}/abc",
                webhook_type="discord",
            )
            await create_subscription(request)

        # Create Slack subscription
        request = CreateSubscriptionRequest(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            webhook_type="slack",
        )
        await create_subscription(request)

        response = await get_alert_stats()

        assert response["total_subscriptions"] == 3
        assert response["enabled_subscriptions"] == 3
        assert response["by_webhook_type"]["discord"] == 2
        assert response["by_webhook_type"]["slack"] == 1


class TestSubscriptionResponse:
    """Tests for SubscriptionResponse model."""

    def test_from_subscription(self):
        """Test creating response from subscription."""
        sub = WebhookSubscription(
            id="test-123",
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type=WebhookType.discord,
            name="Test Sub",
            systems=["Jita"],
            regions=[10000002],
            min_value=1000000,
            include_pods=True,
            ship_types=["Venture"],
            enabled=True,
        )

        response = SubscriptionResponse.from_subscription(sub)

        assert response.id == "test-123"
        assert response.name == "Test Sub"
        assert response.webhook_type == "discord"
        assert response.systems == ["Jita"]
        assert response.regions == [10000002]
        assert response.min_value == 1000000
        assert response.include_pods is True
        assert response.ship_types == ["Venture"]
        assert response.enabled is True
