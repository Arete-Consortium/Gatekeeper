"""Unit tests for multi-character management API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.api.v1.characters import (
    LinkCharacterResponse,
    UnlinkCharacterResponse,
    link_character,
    unlink_character,
    set_active_character,
    list_characters,
    switch_character,
    get_active_character,
)
from backend.app.models.character_preferences import (
    ActiveCharacterResponse,
    CharacterListResponse,
    CharacterPreferences,
    CharacterSwitchRequest,
)
from backend.app.services.character_preferences import MemoryPreferencesStore
from backend.app.services.token_store import MemoryTokenStore


@pytest.fixture
def token_store():
    """Create a fresh in-memory token store."""
    return MemoryTokenStore(encrypt=False)


@pytest.fixture
def prefs_store():
    """Create a fresh in-memory preferences store."""
    return MemoryPreferencesStore()


@pytest.fixture
def active_manager():
    """Create a mock active character manager."""
    manager = MagicMock()
    manager.get_active.return_value = None
    manager.set_active.return_value = None
    manager.clear_active.return_value = None
    manager.get_stats.return_value = {"active_sessions": 0, "unique_characters": 0}
    return manager


@pytest.fixture
async def stored_character(token_store):
    """Store a test character token and return its data."""
    expires = datetime.now(UTC) + timedelta(hours=1)
    await token_store.store_token(
        character_id=12345,
        access_token="test_access",
        refresh_token="test_refresh",
        expires_at=expires,
        character_name="Test Pilot",
        scopes=["esi-location.read_location.v1"],
    )
    return {
        "character_id": 12345,
        "character_name": "Test Pilot",
        "expires_at": expires,
    }


@pytest.fixture
async def second_character(token_store):
    """Store a second test character token."""
    expires = datetime.now(UTC) + timedelta(hours=1)
    await token_store.store_token(
        character_id=67890,
        access_token="test_access_2",
        refresh_token="test_refresh_2",
        expires_at=expires,
        character_name="Alt Pilot",
        scopes=["esi-location.read_location.v1"],
    )
    return {
        "character_id": 67890,
        "character_name": "Alt Pilot",
        "expires_at": expires,
    }


class TestLinkCharacter:
    """Tests for POST /characters/link endpoint."""

    @pytest.mark.asyncio
    async def test_link_character_returns_auth_url(self):
        """Linking a character should return an SSO auth URL."""
        with patch("backend.app.api.v1.auth.login", new_callable=AsyncMock) as mock_login:
            mock_login.return_value = MagicMock(
                auth_url="https://login.eveonline.com/v2/oauth/authorize?state=test123",
                state="test123",
            )
            result = await link_character()

        assert isinstance(result, LinkCharacterResponse)
        assert "eveonline.com" in result.auth_url
        assert result.state == "test123"

    @pytest.mark.asyncio
    async def test_link_character_calls_login(self):
        """Link should delegate to the auth login function."""
        with patch("backend.app.api.v1.auth.login", new_callable=AsyncMock) as mock_login:
            mock_login.return_value = MagicMock(
                auth_url="https://example.com/auth",
                state="abc",
            )
            await link_character()

        mock_login.assert_called_once_with(redirect_uri=None, scopes=None)


class TestUnlinkCharacter:
    """Tests for DELETE /characters/{character_id} endpoint."""

    @pytest.mark.asyncio
    async def test_unlink_character_success(self, token_store, prefs_store, stored_character):
        """Unlinking a character removes its token and preferences."""
        # Store some prefs first
        await prefs_store.get_or_create(12345, "Test Pilot")

        result = await unlink_character(
            character_id=12345,
            token_store=token_store,
            prefs_store=prefs_store,
        )

        assert isinstance(result, UnlinkCharacterResponse)
        assert result.status == "unlinked"
        assert result.character_id == 12345
        assert result.character_name == "Test Pilot"

        # Verify token is removed
        token = await token_store.get_token(12345)
        assert token is None

    @pytest.mark.asyncio
    async def test_unlink_character_not_found(self, token_store, prefs_store):
        """Unlinking a non-existent character raises 404."""
        with pytest.raises(Exception) as exc_info:
            await unlink_character(
                character_id=99999,
                token_store=token_store,
                prefs_store=prefs_store,
            )
        assert "404" in str(exc_info.value.status_code)


class TestSetActiveCharacter:
    """Tests for POST /characters/{character_id}/active endpoint."""

    @pytest.mark.asyncio
    async def test_set_active_success(
        self, token_store, prefs_store, active_manager, stored_character
    ):
        """Setting active character returns the character response."""
        result = await set_active_character(
            character_id=12345,
            x_session_id="test-session",
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert isinstance(result, ActiveCharacterResponse)
        assert result.character_id == 12345
        assert result.is_active is True
        active_manager.set_active.assert_called_once_with("test-session", 12345)

    @pytest.mark.asyncio
    async def test_set_active_not_found(self, token_store, prefs_store, active_manager):
        """Setting active for a non-existent character raises 404."""
        with pytest.raises(Exception) as exc_info:
            await set_active_character(
                character_id=99999,
                x_session_id="test-session",
                token_store=token_store,
                prefs_store=prefs_store,
                active_manager=active_manager,
            )
        assert "404" in str(exc_info.value.status_code)

    @pytest.mark.asyncio
    async def test_set_active_expired_token(self, token_store, prefs_store, active_manager):
        """Setting active for an expired token raises 401."""
        expired = datetime.now(UTC) - timedelta(hours=1)
        await token_store.store_token(
            character_id=11111,
            access_token="expired_token",
            refresh_token="refresh",
            expires_at=expired,
            character_name="Expired Pilot",
            scopes=[],
        )

        with pytest.raises(Exception) as exc_info:
            await set_active_character(
                character_id=11111,
                x_session_id="test-session",
                token_store=token_store,
                prefs_store=prefs_store,
                active_manager=active_manager,
            )
        assert "401" in str(exc_info.value.status_code)


class TestListCharacters:
    """Tests for GET /characters/ endpoint."""

    @pytest.mark.asyncio
    async def test_list_empty(self, token_store, prefs_store, active_manager):
        """Listing with no characters returns empty list."""
        result = await list_characters(
            x_session_id=None,
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert isinstance(result, CharacterListResponse)
        assert result.total_count == 0
        assert result.characters == []

    @pytest.mark.asyncio
    async def test_list_multiple_characters(
        self, token_store, prefs_store, active_manager, stored_character, second_character
    ):
        """Listing returns all stored characters."""
        result = await list_characters(
            x_session_id=None,
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert result.total_count == 2
        char_ids = {c.character_id for c in result.characters}
        assert 12345 in char_ids
        assert 67890 in char_ids

    @pytest.mark.asyncio
    async def test_list_with_active_session(
        self, token_store, prefs_store, active_manager, stored_character
    ):
        """Listing with a session ID returns active character."""
        active_manager.get_active.return_value = 12345

        result = await list_characters(
            x_session_id="test-session",
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert result.active_character_id == 12345


class TestSwitchCharacter:
    """Tests for POST /characters/switch endpoint."""

    @pytest.mark.asyncio
    async def test_switch_character_success(
        self, token_store, prefs_store, active_manager, stored_character
    ):
        """Switching to a valid character succeeds."""
        request = CharacterSwitchRequest(character_id=12345)

        result = await switch_character(
            request=request,
            x_session_id="test-session",
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert result.character_id == 12345
        assert result.is_active is True
        active_manager.set_active.assert_called_once_with("test-session", 12345)

    @pytest.mark.asyncio
    async def test_switch_character_not_found(
        self, token_store, prefs_store, active_manager
    ):
        """Switching to a non-existent character raises 404."""
        request = CharacterSwitchRequest(character_id=99999)

        with pytest.raises(Exception) as exc_info:
            await switch_character(
                request=request,
                x_session_id="test-session",
                token_store=token_store,
                prefs_store=prefs_store,
                active_manager=active_manager,
            )
        assert "404" in str(exc_info.value.status_code)


class TestGetActiveCharacter:
    """Tests for GET /characters/active endpoint."""

    @pytest.mark.asyncio
    async def test_get_active_none(self, token_store, prefs_store, active_manager):
        """No active character returns None."""
        active_manager.get_active.return_value = None

        result = await get_active_character(
            x_session_id="test-session",
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_character(
        self, token_store, prefs_store, active_manager, stored_character
    ):
        """Active character returns its info."""
        active_manager.get_active.return_value = 12345

        result = await get_active_character(
            x_session_id="test-session",
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert result is not None
        assert result.character_id == 12345
        assert result.character_name == "Test Pilot"

    @pytest.mark.asyncio
    async def test_get_active_token_removed(self, token_store, prefs_store, active_manager):
        """If active character's token is gone, returns None and clears active."""
        active_manager.get_active.return_value = 99999

        result = await get_active_character(
            x_session_id="test-session",
            token_store=token_store,
            prefs_store=prefs_store,
            active_manager=active_manager,
        )

        assert result is None
        active_manager.clear_active.assert_called_once_with("test-session")
