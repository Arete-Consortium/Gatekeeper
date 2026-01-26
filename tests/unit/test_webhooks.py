"""Unit tests for webhook service and API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.api.v1.webhooks import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    _mask_url,
    create_webhook,
    delete_webhook,
    get_webhook,
    list_webhooks,
    update_webhook,
)
from backend.app.services.webhooks import (
    KillAlert,
    WebhookSubscription,
    WebhookType,
    _format_discord_embed,
    _format_slack_message,
    _should_alert,
    add_subscription,
    clear_subscriptions,
    dispatch_alert,
    get_subscription,
    list_subscriptions,
    remove_subscription,
    send_webhook,
)


@pytest.fixture
def mock_universe():
    """Create a mock universe with test systems."""
    mock = MagicMock()
    mock.systems = {
        "Jita": MagicMock(id=30000142),
        "Amarr": MagicMock(id=30002187),
        "Tama": MagicMock(id=30002813),
    }
    return mock


@pytest.fixture
def sample_alert():
    """Create a sample kill alert."""
    return KillAlert(
        kill_id=12345,
        system_name="Tama",
        system_id=30002813,
        ship_type="Venture",
        victim_name="Test Pilot",
        victim_corp="Test Corp",
        attacker_count=5,
        total_value=50_000_000,
        is_pod=False,
        zkill_url="https://zkillboard.com/kill/12345/",
    )


@pytest.fixture
def sample_subscription():
    """Create a sample subscription."""
    return WebhookSubscription(
        id="test-sub-1",
        webhook_url="https://discord.com/api/webhooks/test",
        webhook_type=WebhookType.discord,
        systems=["Tama"],
        min_value=10_000_000,
        include_pods=False,
        enabled=True,
    )


class TestKillAlertModel:
    """Tests for KillAlert model."""

    def test_alert_defaults(self):
        """Test alert with minimal fields."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
        )

        assert alert.kill_id == 1
        assert alert.system_name == "Jita"
        assert alert.ship_type is None
        assert alert.attacker_count == 0
        assert alert.is_pod is False

    def test_alert_full(self, sample_alert):
        """Test alert with all fields."""
        assert sample_alert.kill_id == 12345
        assert sample_alert.ship_type == "Venture"
        assert sample_alert.total_value == 50_000_000


class TestFormatDiscordEmbed:
    """Tests for Discord embed formatting."""

    def test_format_basic_embed(self, sample_alert):
        """Test basic Discord embed."""
        result = _format_discord_embed(sample_alert)

        assert "embeds" in result
        embed = result["embeds"][0]
        assert "Kill: Test Pilot" in embed["title"]
        assert embed["color"] == 0x00FF00  # Green for ship

    def test_format_pod_embed(self, sample_alert):
        """Test pod kill embed (red color)."""
        sample_alert.is_pod = True
        result = _format_discord_embed(sample_alert)

        embed = result["embeds"][0]
        assert "Pod: Test Pilot" in embed["title"]
        assert embed["color"] == 0xFF0000  # Red for pod

    def test_format_embed_with_url(self, sample_alert):
        """Test embed includes zKill URL."""
        result = _format_discord_embed(sample_alert)

        embed = result["embeds"][0]
        assert embed["url"] == sample_alert.zkill_url

    def test_format_embed_value_billions(self, sample_alert):
        """Test value formatting in billions."""
        sample_alert.total_value = 2_500_000_000
        result = _format_discord_embed(sample_alert)

        embed = result["embeds"][0]
        value_field = next(f for f in embed["fields"] if f["name"] == "Value")
        assert "2.50B ISK" in value_field["value"]

    def test_format_embed_value_millions(self, sample_alert):
        """Test value formatting in millions."""
        result = _format_discord_embed(sample_alert)

        embed = result["embeds"][0]
        value_field = next(f for f in embed["fields"] if f["name"] == "Value")
        assert "50.00M ISK" in value_field["value"]


class TestFormatSlackMessage:
    """Tests for Slack message formatting."""

    def test_format_basic_message(self, sample_alert):
        """Test basic Slack message."""
        result = _format_slack_message(sample_alert)

        assert "text" in result
        assert "Test Pilot" in result["text"]
        assert "Tama" in result["text"]
        assert ":boom:" in result["text"]

    def test_format_pod_message(self, sample_alert):
        """Test pod kill message."""
        sample_alert.is_pod = True
        result = _format_slack_message(sample_alert)

        assert ":skull:" in result["text"]
        assert "Pod" in result["text"]

    def test_format_message_with_url(self, sample_alert):
        """Test message includes zKill link."""
        result = _format_slack_message(sample_alert)

        assert sample_alert.zkill_url in result["text"]


class TestShouldAlert:
    """Tests for alert filtering."""

    def test_should_alert_matching_system(self, sample_subscription, sample_alert):
        """Test alert matches when system matches."""
        assert _should_alert(sample_subscription, sample_alert) is True

    def test_should_alert_non_matching_system(self, sample_subscription, sample_alert):
        """Test alert doesn't match wrong system."""
        sample_alert.system_name = "Jita"
        assert _should_alert(sample_subscription, sample_alert) is False

    def test_should_alert_all_systems(self, sample_subscription, sample_alert):
        """Test alert matches when watching all systems."""
        sample_subscription.systems = []  # Empty = all systems
        sample_alert.system_name = "Jita"
        assert _should_alert(sample_subscription, sample_alert) is True

    def test_should_alert_disabled(self, sample_subscription, sample_alert):
        """Test disabled subscription doesn't alert."""
        sample_subscription.enabled = False
        assert _should_alert(sample_subscription, sample_alert) is False

    def test_should_alert_pod_excluded(self, sample_subscription, sample_alert):
        """Test pod excluded when include_pods is False."""
        sample_alert.is_pod = True
        assert _should_alert(sample_subscription, sample_alert) is False

    def test_should_alert_pod_included(self, sample_subscription, sample_alert):
        """Test pod included when include_pods is True."""
        sample_subscription.include_pods = True
        sample_alert.is_pod = True
        assert _should_alert(sample_subscription, sample_alert) is True

    def test_should_alert_below_min_value(self, sample_subscription, sample_alert):
        """Test alert excluded when below min value."""
        sample_subscription.min_value = 100_000_000
        assert _should_alert(sample_subscription, sample_alert) is False

    def test_should_alert_above_min_value(self, sample_subscription, sample_alert):
        """Test alert included when above min value."""
        sample_subscription.min_value = 10_000_000
        assert _should_alert(sample_subscription, sample_alert) is True


class TestSendWebhook:
    """Tests for send_webhook function."""

    @pytest.mark.asyncio
    async def test_send_webhook_success(self, sample_alert):
        """Test successful webhook send."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.services.webhooks.httpx.AsyncClient", return_value=mock_client):
            result = await send_webhook(
                "https://discord.com/api/webhooks/test",
                WebhookType.discord,
                sample_alert,
            )

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_webhook_timeout(self, sample_alert):
        """Test webhook timeout handling."""
        import httpx

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.services.webhooks.httpx.AsyncClient", return_value=mock_client):
            result = await send_webhook(
                "https://discord.com/api/webhooks/test",
                WebhookType.discord,
                sample_alert,
            )

        assert result is False


class TestSubscriptionManagement:
    """Tests for subscription management functions."""

    def setup_method(self):
        """Clear subscriptions before each test."""
        clear_subscriptions()

    def test_add_subscription(self, sample_subscription):
        """Test adding a subscription."""
        add_subscription(sample_subscription)

        assert len(list_subscriptions()) == 1
        assert get_subscription("test-sub-1") == sample_subscription

    def test_remove_subscription(self, sample_subscription):
        """Test removing a subscription."""
        add_subscription(sample_subscription)
        result = remove_subscription("test-sub-1")

        assert result is True
        assert len(list_subscriptions()) == 0

    def test_remove_nonexistent_subscription(self):
        """Test removing nonexistent subscription."""
        result = remove_subscription("nonexistent")
        assert result is False

    def test_list_subscriptions(self, sample_subscription):
        """Test listing subscriptions."""
        add_subscription(sample_subscription)
        sub2 = WebhookSubscription(
            id="test-sub-2",
            webhook_url="https://hooks.slack.com/test",
            webhook_type=WebhookType.slack,
        )
        add_subscription(sub2)

        subs = list_subscriptions()
        assert len(subs) == 2


class TestDispatchAlert:
    """Tests for dispatch_alert function."""

    def setup_method(self):
        """Clear subscriptions before each test."""
        clear_subscriptions()

    @pytest.mark.asyncio
    async def test_dispatch_no_subscriptions(self, sample_alert):
        """Test dispatch with no subscriptions."""
        count = await dispatch_alert(sample_alert)
        assert count == 0

    @pytest.mark.asyncio
    async def test_dispatch_matching_subscription(self, sample_alert, sample_subscription):
        """Test dispatch to matching subscription."""
        add_subscription(sample_subscription)

        with patch(
            "backend.app.services.webhooks.send_webhook",
            new_callable=AsyncMock,
            return_value=True,
        ):
            count = await dispatch_alert(sample_alert)

        assert count == 1


class TestWebhookAPI:
    """Tests for webhook API endpoints."""

    def setup_method(self):
        """Clear subscriptions before each test."""
        clear_subscriptions()

    def test_list_webhooks_empty(self):
        """Test listing webhooks when empty."""
        response = list_webhooks()
        assert response.total == 0
        assert response.webhooks == []

    def test_create_webhook(self, mock_universe, sample_subscription):
        """Test creating a webhook."""
        add_subscription(sample_subscription)

        request = WebhookCreateRequest(
            webhook_url="https://discord.com/api/webhooks/new",
            webhook_type=WebhookType.discord,
            systems=["Jita"],
            min_value=1_000_000,
            include_pods=True,
        )

        with patch("backend.app.api.v1.webhooks.load_universe", return_value=mock_universe):
            response = create_webhook(request)

        assert response.webhook_type == WebhookType.discord
        assert response.systems == ["Jita"]
        assert response.min_value == 1_000_000
        assert response.include_pods is True

    def test_create_webhook_invalid_system(self, mock_universe):
        """Test creating webhook with invalid system."""
        request = WebhookCreateRequest(
            webhook_url="https://discord.com/api/webhooks/new",
            webhook_type=WebhookType.discord,
            systems=["FakeSystem"],
        )

        with (
            patch("backend.app.api.v1.webhooks.load_universe", return_value=mock_universe),
            pytest.raises(Exception) as exc_info,
        ):
            create_webhook(request)

        assert "Unknown system: FakeSystem" in str(exc_info.value.detail)

    def test_get_webhook(self, sample_subscription):
        """Test getting a webhook."""
        add_subscription(sample_subscription)

        response = get_webhook("test-sub-1")
        assert response.id == "test-sub-1"

    def test_get_webhook_not_found(self):
        """Test getting nonexistent webhook."""
        with pytest.raises(Exception) as exc_info:
            get_webhook("nonexistent")

        assert "Webhook not found" in str(exc_info.value.detail)

    def test_update_webhook(self, mock_universe, sample_subscription):
        """Test updating a webhook."""
        add_subscription(sample_subscription)

        request = WebhookUpdateRequest(
            systems=["Jita", "Amarr"],
            enabled=False,
        )

        with patch("backend.app.api.v1.webhooks.load_universe", return_value=mock_universe):
            response = update_webhook("test-sub-1", request)

        assert response.systems == ["Jita", "Amarr"]
        assert response.enabled is False

    def test_delete_webhook(self, sample_subscription):
        """Test deleting a webhook."""
        add_subscription(sample_subscription)

        delete_webhook("test-sub-1")

        assert len(list_subscriptions()) == 0

    def test_delete_webhook_not_found(self):
        """Test deleting nonexistent webhook."""
        with pytest.raises(Exception) as exc_info:
            delete_webhook("nonexistent")

        assert "Webhook not found" in str(exc_info.value.detail)


class TestMaskUrl:
    """Tests for URL masking."""

    def test_mask_long_url(self):
        """Test masking long URL."""
        url = "https://discord.com/api/webhooks/1234567890/abcdefghij"
        masked = _mask_url(url)

        assert "1234567890" not in masked
        assert "..." in masked

    def test_mask_short_url(self):
        """Test masking short URL."""
        url = "https://example.com"
        masked = _mask_url(url)

        assert "..." in masked


class TestFormatDiscordEmbedEdgeCases:
    """Additional edge case tests for Discord embed formatting."""

    def test_format_embed_value_thousands(self):
        """Test value formatting under 1M ISK."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            total_value=500_000,  # Under 1M
        )
        result = _format_discord_embed(alert)

        embed = result["embeds"][0]
        value_field = next(f for f in embed["fields"] if f["name"] == "Value")
        assert "500,000 ISK" in value_field["value"]

    def test_format_embed_no_optional_fields(self):
        """Test embed without optional fields (ship_type, value, corp)."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            # No ship_type, total_value, victim_corp
        )
        result = _format_discord_embed(alert)

        embed = result["embeds"][0]
        field_names = [f["name"] for f in embed["fields"]]
        assert "Ship" not in field_names
        assert "Value" not in field_names
        assert "Corp" not in field_names

    def test_format_embed_no_zkill_url(self):
        """Test embed without zKill URL."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            zkill_url=None,
        )
        result = _format_discord_embed(alert)

        embed = result["embeds"][0]
        assert "url" not in embed

    def test_format_embed_unknown_victim(self):
        """Test embed with no victim name."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            victim_name=None,
        )
        result = _format_discord_embed(alert)

        embed = result["embeds"][0]
        assert "Unknown" in embed["title"]


class TestFormatSlackMessageEdgeCases:
    """Additional edge case tests for Slack message formatting."""

    def test_format_slack_value_billions(self):
        """Test Slack message with value in billions."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            total_value=2_500_000_000,
        )
        result = _format_slack_message(alert)

        assert "2.50B ISK" in result["text"]

    def test_format_slack_value_millions(self):
        """Test Slack message with value in millions."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            total_value=50_000_000,
        )
        result = _format_slack_message(alert)

        assert "50.00M ISK" in result["text"]

    def test_format_slack_value_under_million(self):
        """Test Slack message with value under 1M (no formatting)."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            total_value=500_000,  # Under 1M
        )
        result = _format_slack_message(alert)

        # Under 1M, no value string is added
        assert "ISK" not in result["text"]

    def test_format_slack_no_zkill_url(self):
        """Test Slack message without zKill URL."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            zkill_url=None,
        )
        result = _format_slack_message(alert)

        assert "zkillboard" not in result["text"].lower()

    def test_format_slack_no_ship_type(self):
        """Test Slack message without ship type."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
            ship_type=None,
        )
        result = _format_slack_message(alert)

        assert " in " not in result["text"].replace("in *Jita*", "")


class TestSendWebhookEdgeCases:
    """Additional edge case tests for send_webhook."""

    @pytest.mark.asyncio
    async def test_send_webhook_slack(self):
        """Test sending webhook with Slack type."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
        )

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.services.webhooks.httpx.AsyncClient", return_value=mock_client):
            result = await send_webhook(
                "https://hooks.slack.com/services/test",
                WebhookType.slack,
                alert,
            )

        assert result is True
        # Verify Slack payload format was used
        call_kwargs = mock_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "text" in payload  # Slack format has 'text', Discord has 'embeds'

    @pytest.mark.asyncio
    async def test_send_webhook_http_error(self):
        """Test webhook HTTP error handling."""
        import httpx

        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate limited",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.services.webhooks.httpx.AsyncClient", return_value=mock_client):
            result = await send_webhook(
                "https://discord.com/api/webhooks/test",
                WebhookType.discord,
                alert,
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_webhook_generic_exception(self):
        """Test webhook generic exception handling."""
        alert = KillAlert(
            kill_id=1,
            system_name="Jita",
            system_id=30000142,
        )

        mock_client = AsyncMock()
        mock_client.post.side_effect = ValueError("Something went wrong")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.services.webhooks.httpx.AsyncClient", return_value=mock_client):
            result = await send_webhook(
                "https://discord.com/api/webhooks/test",
                WebhookType.discord,
                alert,
            )

        assert result is False


class TestInitDefaultSubscriptions:
    """Tests for init_default_subscriptions function."""

    def setup_method(self):
        """Clear subscriptions before each test."""
        clear_subscriptions()

    def test_init_discord_webhook(self):
        """Test initializing Discord webhook from settings."""
        from backend.app.services.webhooks import init_default_subscriptions

        with patch("backend.app.services.webhooks.settings") as mock_settings:
            mock_settings.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/default"
            mock_settings.SLACK_WEBHOOK_URL = None

            init_default_subscriptions()

        subs = list_subscriptions()
        assert len(subs) == 1
        assert subs[0].id == "default-discord"
        assert subs[0].webhook_type == WebhookType.discord

    def test_init_slack_webhook(self):
        """Test initializing Slack webhook from settings."""
        from backend.app.services.webhooks import init_default_subscriptions

        with patch("backend.app.services.webhooks.settings") as mock_settings:
            mock_settings.DISCORD_WEBHOOK_URL = None
            mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/default"

            init_default_subscriptions()

        subs = list_subscriptions()
        assert len(subs) == 1
        assert subs[0].id == "default-slack"
        assert subs[0].webhook_type == WebhookType.slack

    def test_init_both_webhooks(self):
        """Test initializing both Discord and Slack webhooks."""
        from backend.app.services.webhooks import init_default_subscriptions

        with patch("backend.app.services.webhooks.settings") as mock_settings:
            mock_settings.DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/default"
            mock_settings.SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/default"

            init_default_subscriptions()

        subs = list_subscriptions()
        assert len(subs) == 2
        ids = [s.id for s in subs]
        assert "default-discord" in ids
        assert "default-slack" in ids

    def test_init_no_webhooks(self):
        """Test initialization with no webhooks configured."""
        from backend.app.services.webhooks import init_default_subscriptions

        with patch("backend.app.services.webhooks.settings") as mock_settings:
            mock_settings.DISCORD_WEBHOOK_URL = None
            mock_settings.SLACK_WEBHOOK_URL = None

            init_default_subscriptions()

        subs = list_subscriptions()
        assert len(subs) == 0
