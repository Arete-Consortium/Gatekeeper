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
