"""Unit tests for authentication routes."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.api.v1.auth import (
    AuthStatus,
    CharacterInfo,
    LoginResponse,
    TokenResponse,
    cleanup_expired_states,
    generate_state,
    validate_state,
    _oauth_states,
)
from backend.app.services.token_store import MemoryTokenStore


class TestOAuthStateManagement:
    """Tests for OAuth state generation and validation."""

    def setup_method(self):
        """Clear state storage before each test."""
        _oauth_states.clear()

    def test_generate_state_creates_unique_states(self):
        """Test that generate_state creates unique values."""
        state1 = generate_state()
        state2 = generate_state()

        assert state1 != state2
        assert len(state1) > 20  # Should be reasonably long

    def test_generate_state_stores_expiration(self):
        """Test that state is stored with expiration time."""
        state = generate_state()

        assert state in _oauth_states
        assert _oauth_states[state] > datetime.now(UTC)

    def test_validate_state_accepts_valid_state(self):
        """Test that valid state is accepted."""
        state = generate_state()

        result = validate_state(state)

        assert result is True
        # State should be consumed (removed)
        assert state not in _oauth_states

    def test_validate_state_rejects_invalid_state(self):
        """Test that invalid state is rejected."""
        result = validate_state("nonexistent_state")

        assert result is False

    def test_validate_state_rejects_expired_state(self):
        """Test that expired state is rejected."""
        state = "expired_state"
        _oauth_states[state] = datetime.now(UTC) - timedelta(minutes=1)

        result = validate_state(state)

        assert result is False

    def test_cleanup_expired_states(self):
        """Test that expired states are cleaned up."""
        # Add some states
        valid_state = generate_state()
        expired_state = "expired_state"
        _oauth_states[expired_state] = datetime.now(UTC) - timedelta(minutes=1)

        cleanup_expired_states()

        assert valid_state in _oauth_states
        assert expired_state not in _oauth_states


class TestAuthModels:
    """Tests for authentication response models."""

    def test_character_info_creation(self):
        """Test CharacterInfo model creation."""
        info = CharacterInfo(
            character_id=12345,
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert info.character_id == 12345
        assert info.character_name == "Test Pilot"
        assert info.authenticated is True

    def test_character_info_unauthenticated(self):
        """Test CharacterInfo with authenticated=False."""
        info = CharacterInfo(
            character_id=12345,
            character_name="Test Pilot",
            scopes=[],
            expires_at=datetime.now(UTC),
            authenticated=False,
        )

        assert info.authenticated is False

    def test_auth_status_authenticated(self):
        """Test AuthStatus when authenticated."""
        status = AuthStatus(
            authenticated=True,
            character=CharacterInfo(
                character_id=12345,
                character_name="Test",
                scopes=[],
                expires_at=datetime.now(UTC),
            ),
        )

        assert status.authenticated is True
        assert status.character is not None

    def test_auth_status_not_authenticated(self):
        """Test AuthStatus when not authenticated."""
        status = AuthStatus(authenticated=False)

        assert status.authenticated is False
        assert status.character is None

    def test_login_response(self):
        """Test LoginResponse model."""
        response = LoginResponse(
            auth_url="https://login.eveonline.com/...",
            state="abc123",
        )

        assert "login.eveonline.com" in response.auth_url
        assert response.state == "abc123"

    def test_token_response(self):
        """Test TokenResponse model."""
        response = TokenResponse(
            access_token="access_token_123",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            character_id=12345,
        )

        assert response.access_token == "access_token_123"
        assert response.character_id == 12345


class TestAuthEndpoints:
    """Integration tests for auth endpoints."""

    def test_login_without_esi_config(self, test_client):
        """Test login returns 503 when ESI not configured."""
        with patch("backend.app.api.v1.auth.settings") as mock_settings:
            mock_settings.ESI_CLIENT_ID = None

            response = test_client.get("/api/v1/auth/login")

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"].lower()

    def test_login_with_esi_config(self, test_client):
        """Test login returns auth URL when ESI is configured."""
        with patch("backend.app.api.v1.auth.settings") as mock_settings:
            mock_settings.ESI_CLIENT_ID = "test_client_id"
            mock_settings.ESI_CALLBACK_URL = "http://localhost:8000/callback"

            response = test_client.get("/api/v1/auth/login")

            assert response.status_code == 200
            data = response.json()
            assert "auth_url" in data
            assert "state" in data
            assert "login.eveonline.com" in data["auth_url"]
            assert "test_client_id" in data["auth_url"]

    def test_login_with_custom_scopes(self, test_client):
        """Test login with custom scopes."""
        with patch("backend.app.api.v1.auth.settings") as mock_settings:
            mock_settings.ESI_CLIENT_ID = "test_client_id"
            mock_settings.ESI_CALLBACK_URL = "http://localhost:8000/callback"

            response = test_client.get(
                "/api/v1/auth/login",
                params={"scopes": "esi-location.read_location.v1"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "esi-location.read_location.v1" in data["auth_url"]

    def test_callback_invalid_state(self, test_client):
        """Test callback rejects invalid state."""
        response = test_client.get(
            "/api/v1/auth/callback",
            params={"code": "test_code", "state": "invalid_state"},
        )

        assert response.status_code == 400
        assert "state" in response.json()["detail"].lower()

    def test_me_not_found(self, test_client):
        """Test /me returns unauthenticated for unknown character."""
        response = test_client.get(
            "/api/v1/auth/me",
            params={"character_id": 99999},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    def test_characters_empty(self, test_client):
        """Test /characters returns empty list when no tokens."""
        response = test_client.get("/api/v1/auth/characters")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_logout_not_found(self, test_client):
        """Test logout returns 404 for unknown character."""
        response = test_client.post(
            "/api/v1/auth/logout",
            params={"character_id": 99999},
        )

        assert response.status_code == 404

    def test_clear_tokens(self, test_client):
        """Test clearing all tokens."""
        response = test_client.delete("/api/v1/auth/tokens")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"

    def test_refresh_without_esi_config(self, test_client):
        """Test refresh returns 503 when ESI not configured."""
        with patch("backend.app.api.v1.auth.settings") as mock_settings:
            mock_settings.ESI_CLIENT_ID = None
            mock_settings.ESI_SECRET_KEY = None

            response = test_client.post(
                "/api/v1/auth/refresh",
                params={"character_id": 12345},
            )

            assert response.status_code == 503

    def test_refresh_no_token(self, test_client):
        """Test refresh returns 404 when no token stored."""
        with patch("backend.app.api.v1.auth.settings") as mock_settings:
            mock_settings.ESI_CLIENT_ID = "test_id"
            mock_settings.ESI_SECRET_KEY = "test_secret"

            response = test_client.post(
                "/api/v1/auth/refresh",
                params={"character_id": 99999},
            )

            assert response.status_code == 404

    def test_login_redirect_redirects(self, test_client):
        """Test login_redirect returns a redirect response."""
        with patch("backend.app.api.v1.auth.settings") as mock_settings:
            mock_settings.ESI_CLIENT_ID = "test_client_id"
            mock_settings.ESI_CALLBACK_URL = "http://localhost:8000/callback"

            response = test_client.get(
                "/api/v1/auth/login/redirect",
                follow_redirects=False,
            )

            assert response.status_code == 302
            assert "login.eveonline.com" in response.headers.get("location", "")

    def test_login_redirect_redirects(self, test_client):
        """Test login_redirect returns a redirect response."""
        with patch("backend.app.api.v1.auth.settings") as mock_settings:
            mock_settings.ESI_CLIENT_ID = "test_client_id"
            mock_settings.ESI_CALLBACK_URL = "http://localhost:8000/callback"

            response = test_client.get(
                "/api/v1/auth/login/redirect",
                follow_redirects=False,
            )

            assert response.status_code == 302
            assert "login.eveonline.com" in response.headers.get("location", "")
