"""Tests for admin comp Pro and analytics endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.config import settings
from backend.app.db.database import close_db, init_db
from backend.app.services import usage_tracker


@pytest.fixture(autouse=True)
def _set_admin_secret():
    """Set a test admin secret for all tests."""
    original = settings.ADMIN_SECRET
    settings.ADMIN_SECRET = "test-admin-secret-12345"
    yield
    settings.ADMIN_SECRET = original


ADMIN_HEADERS = {"X-Admin-Secret": "test-admin-secret-12345"}


@pytest.fixture(autouse=True)
async def _ensure_tables():
    """Create DB tables before tests that need them, reset engine after."""
    await close_db()  # Reset any stale engine
    await init_db()
    yield
    await close_db()  # Clean up engine so next test gets fresh one


@pytest.mark.asyncio()
async def test_grant_pro_creates_new_user(app):
    """Grant Pro to a character that doesn't exist creates a user record."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/grant-pro",
            json={
                "character_name": "TestPilot",
                "character_id": 99999999,
                "duration_days": 730,
                "reason": "Bug testing reward",
            },
            headers=ADMIN_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["character_id"] == 99999999
    assert data["character_name"] == "TestPilot"
    assert data["subscription_tier"] == "pro"
    assert data["comp_reason"] == "Bug testing reward"
    assert data["comp_expires_at"] is not None


@pytest.mark.asyncio()
async def test_grant_pro_rejects_bad_secret(app):
    """Grant Pro rejects requests with wrong admin secret."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/grant-pro",
            json={
                "character_name": "Hacker",
                "character_id": 1,
            },
            headers={"X-Admin-Secret": "wrong-secret"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio()
async def test_grant_pro_rejects_missing_secret(app):
    """Grant Pro rejects requests with no admin secret header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/grant-pro",
            json={
                "character_name": "Hacker",
                "character_id": 1,
            },
        )
    assert resp.status_code == 422  # Missing required header


@pytest.mark.asyncio()
async def test_grant_pro_unconfigured(app):
    """Grant Pro returns 503 when ADMIN_SECRET is not set."""
    settings.ADMIN_SECRET = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/grant-pro",
            json={
                "character_name": "Test",
                "character_id": 1,
            },
            headers={"X-Admin-Secret": "anything"},
        )
    assert resp.status_code == 503


@pytest.mark.asyncio()
async def test_revoke_pro_not_found(app):
    """Revoke Pro returns 404 for unknown character."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/revoke-pro",
            json={"character_id": 11111111},
            headers=ADMIN_HEADERS,
        )
    assert resp.status_code == 404


@pytest.mark.asyncio()
async def test_grant_then_revoke(app):
    """Full lifecycle: grant Pro then revoke it."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Grant
        resp = await client.post(
            "/api/v1/admin/grant-pro",
            json={
                "character_name": "LifecyclePilot",
                "character_id": 77777777,
                "duration_days": 30,
                "reason": "Testing lifecycle",
            },
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        assert resp.json()["subscription_tier"] == "pro"

        # Revoke
        resp = await client.post(
            "/api/v1/admin/revoke-pro",
            json={"character_id": 77777777},
            headers=ADMIN_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subscription_tier"] == "free"
        assert data["comp_expires_at"] is None
        assert data["comp_reason"] is None


@pytest.mark.asyncio()
async def test_grant_pro_default_duration(app):
    """Grant Pro uses 730 days (2 years) as default duration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/admin/grant-pro",
            json={
                "character_name": "DefaultDuration",
                "character_id": 55555555,
            },
            headers=ADMIN_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["subscription_tier"] == "pro"
    assert data["comp_reason"] == "Bug testing reward"  # default reason


# ---------------------------------------------------------------------------
# Analytics endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_analytics_returns_data(app):
    """Analytics endpoint returns expected fields with valid admin secret."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/analytics",
            headers=ADMIN_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "active_subscribers" in data
    assert "mrr" in data
    assert "comp_users" in data
    assert "total_users" in data
    assert "dau_estimate" in data
    assert "popular_endpoints" in data
    assert "feature_usage" in data
    assert isinstance(data["mrr"], (int, float))
    assert isinstance(data["popular_endpoints"], list)
    assert "map_views" in data["feature_usage"]
    assert "route_calculations" in data["feature_usage"]
    assert "intel_lookups" in data["feature_usage"]
    assert "kill_feed_connections" in data["feature_usage"]


@pytest.mark.asyncio()
async def test_analytics_rejects_bad_secret(app):
    """Analytics rejects requests with wrong admin secret."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/analytics",
            headers={"X-Admin-Secret": "wrong-secret"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio()
async def test_analytics_reflects_comp_users(app):
    """Analytics counts comp users after granting Pro."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Grant a comp user
        await client.post(
            "/api/v1/admin/grant-pro",
            json={
                "character_name": "AnalyticsTestPilot",
                "character_id": 88888888,
                "duration_days": 30,
                "reason": "Analytics test",
            },
            headers=ADMIN_HEADERS,
        )

        # Check analytics
        resp = await client.get(
            "/api/v1/admin/analytics",
            headers=ADMIN_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["comp_users"] >= 1
    assert data["total_users"] >= 1


@pytest.mark.asyncio()
async def test_analytics_feature_usage_tracking(app):
    """Feature usage counters are reflected in analytics response."""
    # Track some features
    usage_tracker.track_feature("map_views")
    usage_tracker.track_feature("map_views")
    usage_tracker.track_feature("route_calculations")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/analytics",
            headers=ADMIN_HEADERS,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["feature_usage"]["map_views"] >= 2
    assert data["feature_usage"]["route_calculations"] >= 1
