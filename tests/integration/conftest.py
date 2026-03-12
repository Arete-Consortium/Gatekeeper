"""Fixtures for integration tests.

Overrides auth dependencies so integration tests focus on business logic.
Pro tier gating is tested separately in unit tests (test_billing.py).
"""

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.api.v1.dependencies import AuthenticatedCharacter, require_pro


@pytest.fixture(autouse=True)
def override_pro_dependency(app):
    """Override require_pro dependency to bypass auth for integration tests."""

    async def mock_require_pro():
        return AuthenticatedCharacter(
            character_id=12345,
            character_name="Integration Test Pilot",
            access_token="test_token",
            scopes=["esi-location.read_location.v1"],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            auth_method="bearer",
            subscription_tier="pro",
        )

    app.dependency_overrides[require_pro] = mock_require_pro
    yield
    app.dependency_overrides.pop(require_pro, None)


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear module-level caches before each integration test.

    Prevents test pollution from unit tests that patch data_loader functions
    at the source module, which can leave stale lru_cache entries or
    corrupted singleton state.
    """
    from backend.app.services.data_loader import load_risk_config, load_universe

    # Clear lru_cache to ensure fresh data if a prior test polluted it
    load_universe.cache_clear()
    load_risk_config.cache_clear()

    yield

    # Clear again on teardown so subsequent test files start clean
    load_universe.cache_clear()
    load_risk_config.cache_clear()
