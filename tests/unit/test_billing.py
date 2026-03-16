"""Unit tests for billing endpoints, Stripe service, and Pro tier gating."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.api.v1.dependencies import (
    AuthenticatedCharacter,
    require_pro,
)

# =============================================================================
# AuthenticatedCharacter — subscription_tier field
# =============================================================================


class TestAuthenticatedCharacterTier:
    """Tests for subscription_tier field on AuthenticatedCharacter."""

    def test_default_tier_is_free(self):
        char = AuthenticatedCharacter(
            character_id=12345,
            character_name="Test Pilot",
            access_token="tok",
            scopes=[],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert char.subscription_tier == "free"

    def test_pro_tier(self):
        char = AuthenticatedCharacter(
            character_id=12345,
            character_name="Test Pilot",
            access_token="tok",
            scopes=[],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            subscription_tier="pro",
        )
        assert char.subscription_tier == "pro"


# =============================================================================
# require_pro dependency
# =============================================================================


class TestRequirePro:
    """Tests for the require_pro dependency."""

    @pytest.mark.asyncio
    async def test_require_pro_allows_pro_user(self):
        char = AuthenticatedCharacter(
            character_id=1,
            character_name="Pro Pilot",
            access_token="tok",
            scopes=[],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            subscription_tier="pro",
        )
        result = await require_pro(character=char)
        assert result.character_id == 1
        assert result.subscription_tier == "pro"

    @pytest.mark.asyncio
    async def test_require_pro_rejects_free_user(self):
        from fastapi import HTTPException

        char = AuthenticatedCharacter(
            character_id=1,
            character_name="Free Pilot",
            access_token="tok",
            scopes=[],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            subscription_tier="free",
        )
        with pytest.raises(HTTPException) as exc_info:
            await require_pro(character=char)
        assert exc_info.value.status_code == 402
        assert "Pro subscription required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_pro_rejects_empty_tier(self):
        from fastapi import HTTPException

        char = AuthenticatedCharacter(
            character_id=1,
            character_name="Unknown",
            access_token="tok",
            scopes=[],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            subscription_tier="",
        )
        with pytest.raises(HTTPException) as exc_info:
            await require_pro(character=char)
        assert exc_info.value.status_code == 402


# =============================================================================
# Stripe service — unit tests (mocked Stripe API)
# =============================================================================


class TestStripeServiceIsConfigured:
    """Tests for stripe_service.is_configured."""

    def test_not_configured_without_key(self):
        from backend.app.services import stripe_service

        with patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", None):
            assert stripe_service.is_configured() is False

    def test_configured_with_key(self):
        from backend.app.services import stripe_service

        with patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test_123"):
            with patch.object(stripe_service.stripe, "api_key", "sk_test_123"):
                assert stripe_service.is_configured() is True


class TestStripeServiceCheckout:
    """Tests for create_checkout_session."""

    @pytest.mark.asyncio
    async def test_checkout_not_configured(self):
        from backend.app.services import stripe_service

        db = AsyncMock()
        with patch.object(stripe_service, "is_configured", return_value=False):
            with pytest.raises(ValueError, match="not configured"):
                await stripe_service.create_checkout_session(
                    db=db,
                    character_id=1,
                    character_name="Test",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )

    @pytest.mark.asyncio
    async def test_checkout_no_price_id(self):
        from backend.app.services import stripe_service

        db = AsyncMock()
        with (
            patch.object(stripe_service, "is_configured", return_value=True),
            patch.object(stripe_service.settings, "STRIPE_PRO_MONTHLY_PRICE_ID", None),
        ):
            with pytest.raises(ValueError, match="STRIPE_PRO_MONTHLY_PRICE_ID"):
                await stripe_service.create_checkout_session(
                    db=db,
                    character_id=1,
                    character_name="Test",
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                )

    @pytest.mark.asyncio
    async def test_checkout_success(self):
        from backend.app.services import stripe_service

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/session_123"

        with (
            patch.object(stripe_service, "is_configured", return_value=True),
            patch.object(stripe_service.settings, "STRIPE_PRO_MONTHLY_PRICE_ID", "price_test"),
            patch.object(stripe_service, "get_or_create_customer", return_value="cus_123"),
            patch.object(
                stripe_service.stripe.checkout.Session,
                "create",
                return_value=mock_session,
            ),
        ):
            url = await stripe_service.create_checkout_session(
                db=db,
                character_id=1,
                character_name="Test",
                success_url="https://example.com/success",
                cancel_url="https://example.com/cancel",
            )
            assert url == "https://checkout.stripe.com/session_123"


class TestStripeServicePortal:
    """Tests for create_portal_session."""

    @pytest.mark.asyncio
    async def test_portal_not_configured(self):
        from backend.app.services import stripe_service

        db = AsyncMock()
        with patch.object(stripe_service, "is_configured", return_value=False):
            with pytest.raises(ValueError, match="not configured"):
                await stripe_service.create_portal_session(
                    db=db, character_id=1, return_url="https://example.com"
                )

    @pytest.mark.asyncio
    async def test_portal_no_customer(self):
        from backend.app.services import stripe_service

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with patch.object(stripe_service, "is_configured", return_value=True):
            with pytest.raises(ValueError, match="No Stripe customer"):
                await stripe_service.create_portal_session(
                    db=db, character_id=1, return_url="https://example.com"
                )

    @pytest.mark.asyncio
    async def test_portal_success(self):
        from backend.app.services import stripe_service

        mock_user = MagicMock()
        mock_user.stripe_customer_id = "cus_123"

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = mock_result

        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/portal_123"

        with (
            patch.object(stripe_service, "is_configured", return_value=True),
            patch.object(
                stripe_service.stripe.billing_portal.Session,
                "create",
                return_value=mock_session,
            ),
        ):
            url = await stripe_service.create_portal_session(
                db=db, character_id=1, return_url="https://example.com"
            )
            assert url == "https://billing.stripe.com/portal_123"


# =============================================================================
# Webhook handling
# =============================================================================


class TestStripeWebhook:
    """Tests for handle_webhook."""

    @pytest.mark.asyncio
    async def test_webhook_no_secret(self):
        from backend.app.services import stripe_service

        with patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", ""):
            with pytest.raises(ValueError, match="secret not configured"):
                await stripe_service.handle_webhook(b"payload", "sig")

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self):
        from backend.app.services import stripe_service

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(
                stripe_service.stripe.Webhook,
                "construct_event",
                side_effect=stripe_service.stripe.error.SignatureVerificationError(
                    "bad sig", "sig"
                ),
            ),
        ):
            with pytest.raises(ValueError, match="Invalid webhook signature"):
                await stripe_service.handle_webhook(b"payload", "bad_sig")

    @pytest.mark.asyncio
    async def test_webhook_checkout_completed(self):
        from backend.app.services import stripe_service

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"character_id": "12345"},
                    "customer": "cus_test",
                    "subscription": "sub_test",
                }
            },
        }

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(stripe_service.stripe.Webhook, "construct_event", return_value=event),
            patch(
                "backend.app.db.database.get_session_factory",
                return_value=mock_factory,
            ),
        ):
            result = await stripe_service.handle_webhook(b"payload", "sig")
            assert result["processed"] is True
            assert result["character_id"] == 12345
            assert result["tier"] == "pro"

    @pytest.mark.asyncio
    async def test_webhook_subscription_deleted(self):
        from backend.app.services import stripe_service

        event = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test",
                    "metadata": {"character_id": "12345"},
                }
            },
        }

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(stripe_service.stripe.Webhook, "construct_event", return_value=event),
            patch(
                "backend.app.db.database.get_session_factory",
                return_value=mock_factory,
            ),
        ):
            result = await stripe_service.handle_webhook(b"payload", "sig")
            assert result["processed"] is True
            assert result["tier"] == "free"

    @pytest.mark.asyncio
    async def test_webhook_subscription_updated_active(self):
        from backend.app.services import stripe_service

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test",
                    "status": "active",
                    "metadata": {"character_id": "12345"},
                }
            },
        }

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(stripe_service.stripe.Webhook, "construct_event", return_value=event),
            patch(
                "backend.app.db.database.get_session_factory",
                return_value=mock_factory,
            ),
        ):
            result = await stripe_service.handle_webhook(b"payload", "sig")
            assert result["processed"] is True
            assert result["tier"] == "pro"

    @pytest.mark.asyncio
    async def test_webhook_subscription_updated_past_due(self):
        from backend.app.services import stripe_service

        event = {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test",
                    "status": "past_due",
                    "metadata": {"character_id": "12345"},
                }
            },
        }

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(stripe_service.stripe.Webhook, "construct_event", return_value=event),
            patch(
                "backend.app.db.database.get_session_factory",
                return_value=mock_factory,
            ),
        ):
            result = await stripe_service.handle_webhook(b"payload", "sig")
            assert result["tier"] == "free"

    @pytest.mark.asyncio
    async def test_webhook_payment_failed(self):
        from backend.app.services import stripe_service

        event = {
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "attempt_count": 2,
                }
            },
        }

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(stripe_service.stripe.Webhook, "construct_event", return_value=event),
        ):
            result = await stripe_service.handle_webhook(b"payload", "sig")
            assert result["processed"] is True
            assert result["attempt_count"] == 2

    @pytest.mark.asyncio
    async def test_webhook_unhandled_event(self):
        from backend.app.services import stripe_service

        event = {
            "type": "some.unknown.event",
            "data": {"object": {}},
        }

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(stripe_service.stripe.Webhook, "construct_event", return_value=event),
        ):
            result = await stripe_service.handle_webhook(b"payload", "sig")
            assert result["processed"] is False
            assert result["reason"] == "unhandled_event"

    @pytest.mark.asyncio
    async def test_webhook_checkout_no_character_id(self):
        from backend.app.services import stripe_service

        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {},
                    "customer": "cus_test",
                    "subscription": "sub_test",
                }
            },
        }

        with (
            patch.object(stripe_service.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test"),
            patch.object(stripe_service.settings, "STRIPE_SECRET_KEY", "sk_test"),
            patch.object(stripe_service.stripe.Webhook, "construct_event", return_value=event),
        ):
            result = await stripe_service.handle_webhook(b"payload", "sig")
            assert result["processed"] is False
            assert result["reason"] == "no_character_id"


# =============================================================================
# Subscription status
# =============================================================================


class TestStripeSubscriptionStatus:
    """Tests for get_subscription_status."""

    @pytest.mark.asyncio
    async def test_status_no_user(self):
        from backend.app.services import stripe_service

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        status = await stripe_service.get_subscription_status(db, character_id=1)
        assert status["tier"] == "free"
        assert status["status"] == "no_account"

    @pytest.mark.asyncio
    async def test_status_free_user_no_stripe(self):
        from backend.app.services import stripe_service

        mock_user = MagicMock()
        mock_user.subscription_tier = "free"
        mock_user.character_id = 1
        mock_user.character_name = "Test"
        mock_user.stripe_customer_id = None

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = mock_result

        status = await stripe_service.get_subscription_status(db, character_id=1)
        assert status["tier"] == "free"
        assert status["status"] == "local_only"

    @pytest.mark.asyncio
    async def test_status_pro_user_with_stripe(self):
        from backend.app.services import stripe_service

        mock_user = MagicMock()
        mock_user.subscription_tier = "pro"
        mock_user.character_id = 1
        mock_user.character_name = "Pro Test"
        mock_user.stripe_customer_id = "cus_123"

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = mock_result

        mock_sub = MagicMock()
        mock_sub.status = "active"
        mock_sub.id = "sub_123"
        mock_sub.current_period_end = 1700000000
        mock_sub.cancel_at_period_end = False

        mock_subs = MagicMock()
        mock_subs.data = [mock_sub]

        with (
            patch.object(stripe_service, "is_configured", return_value=True),
            patch.object(stripe_service.stripe.Subscription, "list", return_value=mock_subs),
        ):
            status = await stripe_service.get_subscription_status(db, character_id=1)
            assert status["tier"] == "pro"
            assert status["status"] == "active"
            assert status["subscription_id"] == "sub_123"

    @pytest.mark.asyncio
    async def test_status_no_active_subscription(self):
        from backend.app.services import stripe_service

        mock_user = MagicMock()
        mock_user.subscription_tier = "free"
        mock_user.character_id = 1
        mock_user.character_name = "Test"
        mock_user.stripe_customer_id = "cus_123"

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        db.execute.return_value = mock_result

        mock_subs = MagicMock()
        mock_subs.data = []

        with (
            patch.object(stripe_service, "is_configured", return_value=True),
            patch.object(stripe_service.stripe.Subscription, "list", return_value=mock_subs),
        ):
            status = await stripe_service.get_subscription_status(db, character_id=1)
            assert status["status"] == "none"


# =============================================================================
# User model
# =============================================================================


class TestUserModel:
    """Tests for User SQLAlchemy model."""

    def test_user_model_defaults(self):
        from backend.app.db.models import User

        # SQLAlchemy column defaults apply at INSERT, not construction.
        # Test explicit construction matches expected schema.
        user = User(character_id=12345, character_name="Test", subscription_tier="free")
        assert user.subscription_tier == "free"
        assert user.stripe_customer_id is None
        assert user.stripe_subscription_id is None

    def test_user_repr(self):
        from backend.app.db.models import User

        user = User(character_id=12345, character_name="Test", subscription_tier="pro")
        assert "12345" in repr(user)
        assert "pro" in repr(user)


# =============================================================================
# Payment failed handler
# =============================================================================


class TestPaymentFailedHandler:
    """Tests for _handle_payment_failed."""

    def test_payment_failed_returns_info(self):
        from backend.app.services.stripe_service import _handle_payment_failed

        result = _handle_payment_failed(
            {
                "customer": "cus_123",
                "subscription": "sub_456",
                "attempt_count": 3,
            }
        )
        assert result["processed"] is True
        assert result["customer_id"] == "cus_123"
        assert result["attempt_count"] == 3

    def test_payment_failed_defaults(self):
        from backend.app.services.stripe_service import _handle_payment_failed

        result = _handle_payment_failed({})
        assert result["attempt_count"] == 0


# =============================================================================
# Config settings
# =============================================================================


class TestStripeConfig:
    """Tests for Stripe-related config settings."""

    def test_stripe_settings_defaults(self):
        from backend.app.core.config import Settings

        s = Settings(SECRET_KEY="x" * 32, DEBUG=True)
        assert s.STRIPE_SECRET_KEY is None
        assert s.STRIPE_WEBHOOK_SECRET is None
        assert s.STRIPE_PRO_MONTHLY_PRICE_ID is None

    def test_rate_limit_pro_setting(self):
        from backend.app.core.config import Settings

        s = Settings(SECRET_KEY="x" * 32, DEBUG=True)
        assert s.RATE_LIMIT_PER_MINUTE_USER == 100
        assert s.RATE_LIMIT_PER_MINUTE_PRO == 300


# =============================================================================
# Rate limit tier awareness
# =============================================================================


class TestRateLimitTierAwareness:
    """Tests for tier-aware rate limiting."""

    def test_free_user_identifier(self):
        from backend.app.middleware.rate_limit import get_rate_limit_for_identifier

        limit = get_rate_limit_for_identifier("user:12345")
        assert "100" in limit

    def test_pro_user_identifier(self):
        from backend.app.middleware.rate_limit import get_rate_limit_for_identifier

        limit = get_rate_limit_for_identifier("user:pro:12345")
        assert "300" in limit

    def test_apikey_identifier(self):
        from backend.app.middleware.rate_limit import get_rate_limit_for_identifier

        limit = get_rate_limit_for_identifier("apikey:abc123")
        assert "300" in limit

    def test_ip_identifier(self):
        from backend.app.core.config import settings
        from backend.app.middleware.rate_limit import get_rate_limit_for_identifier

        limit = get_rate_limit_for_identifier("ip:1.2.3.4")
        assert limit == f"{settings.RATE_LIMIT_PER_MINUTE}/minute"
