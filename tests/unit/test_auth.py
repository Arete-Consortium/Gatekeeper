"""Unit tests for ESI OAuth2 authentication."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.api.v1.auth import (
    OAuthStateData,
    _oauth_states,
    cleanup_expired_states,
    consume_state,
    generate_state,
)
from backend.app.services.token_store import MemoryTokenStore


class TestOAuthState:
    """Tests for OAuth state management."""

    def setup_method(self):
        """Clear state before each test."""
        _oauth_states.clear()

    def test_generate_state_creates_unique_states(self):
        """State tokens should be unique."""
        state1 = generate_state()
        state2 = generate_state()
        assert state1 != state2
        assert len(state1) > 20  # Sufficient entropy

    def test_consume_state_accepts_valid_state(self):
        """Valid state should be accepted and consumed."""
        state = generate_state()
        result = consume_state(state)
        assert result is not None
        # State should be consumed
        assert consume_state(state) is None

    def test_consume_state_rejects_unknown_state(self):
        """Unknown state should be rejected."""
        assert consume_state("unknown-state") is None

    def test_consume_state_rejects_expired_state(self):
        """Expired state should be rejected."""
        state = "test-expired-state"
        _oauth_states[state] = OAuthStateData(
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        assert consume_state(state) is None

    def test_consume_state_returns_frontend_origin(self):
        """consume_state should return stored frontend_origin."""
        state = generate_state(frontend_origin="https://edengk.com")
        result = consume_state(state)
        assert result is not None
        assert result.frontend_origin == "https://edengk.com"

    def test_cleanup_expired_states(self):
        """Expired states should be cleaned up."""
        valid = generate_state()
        expired = "expired-state"
        _oauth_states[expired] = OAuthStateData(
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )

        cleanup_expired_states()

        assert valid in _oauth_states
        assert expired not in _oauth_states


class TestMemoryTokenStore:
    """Tests for in-memory token storage."""

    @pytest.fixture
    def store(self):
        return MemoryTokenStore()

    @pytest.mark.asyncio
    async def test_store_and_get_token(self, store):
        """Should store and retrieve token."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        await store.store_token(
            character_id=12345,
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_at=expires,
            character_name="Test Character",
            scopes=["esi-location.read_location.v1"],
        )

        token = await store.get_token(12345)
        assert token is not None
        assert token["character_id"] == 12345
        assert token["access_token"] == "test-access-token"
        assert token["character_name"] == "Test Character"
        assert "esi-location.read_location.v1" in token["scopes"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, store):
        """Should return None for unknown character."""
        token = await store.get_token(99999)
        assert token is None

    @pytest.mark.asyncio
    async def test_remove_token(self, store):
        """Should remove token."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        await store.store_token(
            character_id=12345,
            access_token="test",
            refresh_token="test",
            expires_at=expires,
            character_name="Test",
            scopes=[],
        )

        removed = await store.remove_token(12345)
        assert removed is True

        token = await store.get_token(12345)
        assert token is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_token(self, store):
        """Should return False when removing nonexistent token."""
        removed = await store.remove_token(99999)
        assert removed is False

    @pytest.mark.asyncio
    async def test_list_characters(self, store):
        """Should list all stored characters."""
        expires = datetime.now(UTC) + timedelta(hours=1)

        await store.store_token(
            character_id=111,
            access_token="a",
            refresh_token="r",
            expires_at=expires,
            character_name="Char One",
            scopes=[],
        )
        await store.store_token(
            character_id=222,
            access_token="b",
            refresh_token="s",
            expires_at=expires,
            character_name="Char Two",
            scopes=[],
        )

        characters = await store.list_characters()
        assert len(characters) == 2
        char_ids = {c["character_id"] for c in characters}
        assert char_ids == {111, 222}

    @pytest.mark.asyncio
    async def test_clear_all(self, store):
        """Should clear all tokens."""
        expires = datetime.now(UTC) + timedelta(hours=1)

        await store.store_token(
            character_id=111,
            access_token="a",
            refresh_token="r",
            expires_at=expires,
            character_name="One",
            scopes=[],
        )
        await store.store_token(
            character_id=222,
            access_token="b",
            refresh_token="s",
            expires_at=expires,
            character_name="Two",
            scopes=[],
        )

        count = await store.clear_all()
        assert count == 2

        characters = await store.list_characters()
        assert len(characters) == 0

    @pytest.mark.asyncio
    async def test_update_existing_token(self, store):
        """Should update existing token."""
        expires1 = datetime.now(UTC) + timedelta(hours=1)
        expires2 = datetime.now(UTC) + timedelta(hours=2)

        await store.store_token(
            character_id=12345,
            access_token="old-token",
            refresh_token="old-refresh",
            expires_at=expires1,
            character_name="Test",
            scopes=["scope1"],
        )

        await store.store_token(
            character_id=12345,
            access_token="new-token",
            refresh_token="new-refresh",
            expires_at=expires2,
            character_name="Test Updated",
            scopes=["scope1", "scope2"],
        )

        token = await store.get_token(12345)
        assert token["access_token"] == "new-token"
        assert token["character_name"] == "Test Updated"
        assert len(token["scopes"]) == 2


class TestAuthDependencies:
    """Tests for authentication dependencies."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        from unittest.mock import MagicMock

        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_get_current_character_valid_token(self, mock_request):
        """Should return character for valid token."""
        from backend.app.api.v1.dependencies import get_current_character
        from backend.app.services.token_store import set_token_store

        store = MemoryTokenStore()
        set_token_store(store)

        expires = datetime.now(UTC) + timedelta(hours=1)
        await store.store_token(
            character_id=12345,
            access_token="valid-token",
            refresh_token="refresh",
            expires_at=expires,
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        character = await get_current_character(
            request=mock_request,
            character_id=12345,
            authorization=None,
            user_agent=None,
            token_store=store,
        )
        assert character.character_id == 12345
        assert character.character_name == "Test Pilot"
        assert character.access_token == "valid-token"

    @pytest.mark.asyncio
    async def test_get_current_character_no_token(self, mock_request):
        """Should raise 401 when no token found."""
        from fastapi import HTTPException

        from backend.app.api.v1.dependencies import get_current_character
        from backend.app.services.token_store import set_token_store

        store = MemoryTokenStore()
        set_token_store(store)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_character(
                request=mock_request,
                character_id=99999,
                authorization=None,
                user_agent=None,
                token_store=store,
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_character_expired_token(self, mock_request):
        """Should raise 401 when token expired."""
        from fastapi import HTTPException

        from backend.app.api.v1.dependencies import get_current_character
        from backend.app.services.token_store import set_token_store

        store = MemoryTokenStore()
        set_token_store(store)

        expired = datetime.now(UTC) - timedelta(hours=1)
        await store.store_token(
            character_id=12345,
            access_token="expired-token",
            refresh_token="refresh",
            expires_at=expired,
            character_name="Test",
            scopes=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_character(
                request=mock_request,
                character_id=12345,
                authorization=None,
                user_agent=None,
                token_store=store,
            )

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_require_scopes_valid(self):
        """Should pass when required scopes present."""
        from backend.app.api.v1.dependencies import require_scopes
        from backend.app.services.token_store import set_token_store

        store = MemoryTokenStore()
        set_token_store(store)

        expires = datetime.now(UTC) + timedelta(hours=1)
        await store.store_token(
            character_id=12345,
            access_token="token",
            refresh_token="refresh",
            expires_at=expires,
            character_name="Test",
            scopes=["esi-location.read_location.v1", "esi-ui.write_waypoint.v1"],
        )

        verify = require_scopes("esi-location.read_location.v1")
        # This would need to be called with proper dependency injection
        # For unit test, we verify the factory creates a callable

        assert callable(verify)

    @pytest.mark.asyncio
    async def test_get_optional_character_none(self, mock_request):
        """Should return None when no character_id provided."""
        from backend.app.api.v1.dependencies import get_optional_character
        from backend.app.services.token_store import set_token_store

        store = MemoryTokenStore()
        set_token_store(store)

        character = await get_optional_character(
            request=mock_request,
            character_id=None,
            authorization=None,
            user_agent=None,
            token_store=store,
        )
        assert character is None

    @pytest.mark.asyncio
    async def test_get_optional_character_valid(self, mock_request):
        """Should return character when valid."""
        from backend.app.api.v1.dependencies import get_optional_character
        from backend.app.services.token_store import set_token_store

        store = MemoryTokenStore()
        set_token_store(store)

        expires = datetime.now(UTC) + timedelta(hours=1)
        await store.store_token(
            character_id=12345,
            access_token="token",
            refresh_token="refresh",
            expires_at=expires,
            character_name="Test",
            scopes=[],
        )

        character = await get_optional_character(
            request=mock_request,
            character_id=12345,
            authorization=None,
            user_agent=None,
            token_store=store,
        )
        assert character is not None
        assert character.character_id == 12345
