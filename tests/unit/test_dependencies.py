"""Unit tests for authentication dependencies."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.api.v1.dependencies import (
    AuthenticatedCharacter,
    get_current_character,
    get_optional_character,
    require_scopes,
)
from backend.app.services.token_store import MemoryTokenStore


class TestAuthenticatedCharacterModel:
    """Tests for AuthenticatedCharacter model."""

    def test_create_authenticated_character(self):
        """Test creating an AuthenticatedCharacter."""
        char = AuthenticatedCharacter(
            character_id=12345,
            character_name="Test Pilot",
            access_token="token123",
            scopes=["esi-location.read_location.v1"],
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        assert char.character_id == 12345
        assert char.character_name == "Test Pilot"
        assert char.access_token == "token123"
        assert len(char.scopes) == 1


class TestGetCurrentCharacter:
    """Tests for get_current_character dependency."""

    @pytest.fixture
    def token_store(self):
        """Create a memory token store."""
        return MemoryTokenStore()

    @pytest.mark.asyncio
    async def test_get_current_character_valid(self, token_store):
        """Test getting character with valid token."""
        # Store a valid token
        await token_store.store_token(
            character_id=12345,
            access_token="valid_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        char = await get_current_character(character_id=12345, token_store=token_store)

        assert char.character_id == 12345
        assert char.character_name == "Test Pilot"
        assert char.access_token == "valid_token"

    @pytest.mark.asyncio
    async def test_get_current_character_not_found(self, token_store):
        """Test getting character when no token exists."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_character(character_id=99999, token_store=token_store)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_character_expired(self, token_store):
        """Test getting character with expired token."""
        from fastapi import HTTPException

        # Store an expired token
        await token_store.store_token(
            character_id=12345,
            access_token="expired_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            character_name="Test Pilot",
            scopes=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_character(character_id=12345, token_store=token_store)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


class TestGetOptionalCharacter:
    """Tests for get_optional_character dependency."""

    @pytest.fixture
    def token_store(self):
        """Create a memory token store."""
        return MemoryTokenStore()

    @pytest.mark.asyncio
    async def test_optional_character_none_id(self, token_store):
        """Test optional character with no ID provided."""
        result = await get_optional_character(character_id=None, token_store=token_store)
        assert result is None

    @pytest.mark.asyncio
    async def test_optional_character_valid(self, token_store):
        """Test optional character with valid token."""
        await token_store.store_token(
            character_id=12345,
            access_token="valid_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            character_name="Test Pilot",
            scopes=[],
        )

        result = await get_optional_character(character_id=12345, token_store=token_store)

        assert result is not None
        assert result.character_id == 12345

    @pytest.mark.asyncio
    async def test_optional_character_not_found(self, token_store):
        """Test optional character when token not found."""
        result = await get_optional_character(character_id=99999, token_store=token_store)
        assert result is None

    @pytest.mark.asyncio
    async def test_optional_character_expired(self, token_store):
        """Test optional character with expired token."""
        await token_store.store_token(
            character_id=12345,
            access_token="expired_token",
            refresh_token="refresh_token",
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            character_name="Test Pilot",
            scopes=[],
        )

        result = await get_optional_character(character_id=12345, token_store=token_store)
        assert result is None


class TestRequireScopes:
    """Tests for require_scopes dependency factory."""

    @pytest.fixture
    def token_store(self):
        """Create a memory token store."""
        return MemoryTokenStore()

    @pytest.mark.asyncio
    async def test_require_scopes_has_scope(self, token_store):
        """Test require_scopes when character has required scope."""
        await token_store.store_token(
            character_id=12345,
            access_token="token",
            refresh_token="refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        # Create dependency that requires location scope
        verify_scopes = require_scopes("esi-location.read_location.v1")

        # Get the character first
        char = await get_current_character(character_id=12345, token_store=token_store)

        # This should pass
        result = await verify_scopes(character=char)
        assert result.character_id == 12345

    @pytest.mark.asyncio
    async def test_require_scopes_missing_scope(self, token_store):
        """Test require_scopes when character is missing scope."""
        from fastapi import HTTPException

        await token_store.store_token(
            character_id=12345,
            access_token="token",
            refresh_token="refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            character_name="Test Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        # Create dependency that requires a different scope
        verify_scopes = require_scopes("esi-ui.write_waypoint.v1")

        char = await get_current_character(character_id=12345, token_store=token_store)

        with pytest.raises(HTTPException) as exc_info:
            await verify_scopes(character=char)

        assert exc_info.value.status_code == 403
        assert "Missing required scopes" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_multiple_scopes(self, token_store):
        """Test require_scopes with multiple scopes."""
        await token_store.store_token(
            character_id=12345,
            access_token="token",
            refresh_token="refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            character_name="Test Pilot",
            scopes=[
                "esi-location.read_location.v1",
                "esi-ui.write_waypoint.v1",
            ],
        )

        verify_scopes = require_scopes(
            "esi-location.read_location.v1",
            "esi-ui.write_waypoint.v1",
        )

        char = await get_current_character(character_id=12345, token_store=token_store)
        result = await verify_scopes(character=char)
        assert result.character_id == 12345
