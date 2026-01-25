"""Unit tests for token storage service."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from backend.app.services.token_store import (
    FileTokenStore,
    MemoryTokenStore,
    get_token_store,
    set_token_store,
)


class TestMemoryTokenStore:
    """Tests for in-memory token storage."""

    @pytest.fixture
    def store(self):
        """Create a fresh memory token store."""
        return MemoryTokenStore()

    @pytest.fixture
    def sample_token_data(self):
        """Sample token data for testing."""
        return {
            "character_id": 12345,
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "character_name": "Test Pilot",
            "scopes": ["esi-location.read_location.v1"],
        }

    @pytest.mark.asyncio
    async def test_store_and_get_token(self, store, sample_token_data):
        """Test storing and retrieving a token."""
        await store.store_token(**sample_token_data)

        result = await store.get_token(sample_token_data["character_id"])
        assert result is not None
        assert result["character_id"] == sample_token_data["character_id"]
        assert result["access_token"] == sample_token_data["access_token"]
        assert result["character_name"] == sample_token_data["character_name"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_token(self, store):
        """Test getting a token that doesn't exist."""
        result = await store.get_token(99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_remove_token(self, store, sample_token_data):
        """Test removing a token."""
        await store.store_token(**sample_token_data)

        result = await store.remove_token(sample_token_data["character_id"])
        assert result is True

        # Verify it's gone
        token = await store.get_token(sample_token_data["character_id"])
        assert token is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_token(self, store):
        """Test removing a token that doesn't exist."""
        result = await store.remove_token(99999)
        assert result is False

    @pytest.mark.asyncio
    async def test_list_characters(self, store, sample_token_data):
        """Test listing all characters with tokens."""
        # Store multiple tokens
        await store.store_token(**sample_token_data)
        await store.store_token(
            character_id=67890,
            access_token="access_2",
            refresh_token="refresh_2",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            character_name="Second Pilot",
            scopes=["esi-location.read_location.v1"],
        )

        characters = await store.list_characters()
        assert len(characters) == 2
        char_ids = {c["character_id"] for c in characters}
        assert 12345 in char_ids
        assert 67890 in char_ids

    @pytest.mark.asyncio
    async def test_clear_all(self, store, sample_token_data):
        """Test clearing all tokens."""
        await store.store_token(**sample_token_data)
        await store.store_token(
            character_id=67890,
            access_token="access_2",
            refresh_token="refresh_2",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            character_name="Second Pilot",
            scopes=[],
        )

        count = await store.clear_all()
        assert count == 2

        characters = await store.list_characters()
        assert len(characters) == 0

    @pytest.mark.asyncio
    async def test_overwrite_existing_token(self, store, sample_token_data):
        """Test that storing a token for an existing character overwrites it."""
        await store.store_token(**sample_token_data)

        # Store new token for same character
        new_access_token = "new_access_token"
        await store.store_token(
            character_id=sample_token_data["character_id"],
            access_token=new_access_token,
            refresh_token="new_refresh",
            expires_at=datetime.utcnow() + timedelta(hours=2),
            character_name=sample_token_data["character_name"],
            scopes=sample_token_data["scopes"],
        )

        result = await store.get_token(sample_token_data["character_id"])
        assert result["access_token"] == new_access_token


class TestFileTokenStore:
    """Tests for file-based token storage."""

    @pytest.fixture
    def temp_path(self):
        """Create a temporary file path for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "tokens.json"

    @pytest.fixture
    def store(self, temp_path):
        """Create a file token store with temp path."""
        return FileTokenStore(path=temp_path)

    @pytest.fixture
    def sample_token_data(self):
        """Sample token data for testing."""
        return {
            "character_id": 12345,
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_123",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "character_name": "Test Pilot",
            "scopes": ["esi-location.read_location.v1"],
        }

    @pytest.mark.asyncio
    async def test_store_and_get_token(self, store, sample_token_data):
        """Test storing and retrieving a token."""
        await store.store_token(**sample_token_data)

        result = await store.get_token(sample_token_data["character_id"])
        assert result is not None
        assert result["character_id"] == sample_token_data["character_id"]
        assert result["access_token"] == sample_token_data["access_token"]

    @pytest.mark.asyncio
    async def test_persistence(self, temp_path, sample_token_data):
        """Test that tokens persist across store instances."""
        # Store with first instance
        store1 = FileTokenStore(path=temp_path)
        await store1.store_token(**sample_token_data)

        # Load with new instance
        store2 = FileTokenStore(path=temp_path)
        result = await store2.get_token(sample_token_data["character_id"])

        assert result is not None
        assert result["character_id"] == sample_token_data["character_id"]
        assert result["access_token"] == sample_token_data["access_token"]

    @pytest.mark.asyncio
    async def test_remove_token(self, store, sample_token_data):
        """Test removing a token persists to file."""
        await store.store_token(**sample_token_data)

        result = await store.remove_token(sample_token_data["character_id"])
        assert result is True

        token = await store.get_token(sample_token_data["character_id"])
        assert token is None

    @pytest.mark.asyncio
    async def test_list_characters(self, store, sample_token_data):
        """Test listing characters."""
        await store.store_token(**sample_token_data)

        characters = await store.list_characters()
        assert len(characters) == 1
        assert characters[0]["character_id"] == sample_token_data["character_id"]

    @pytest.mark.asyncio
    async def test_clear_all(self, store, sample_token_data):
        """Test clearing all tokens."""
        await store.store_token(**sample_token_data)

        count = await store.clear_all()
        assert count == 1

        characters = await store.list_characters()
        assert len(characters) == 0

    @pytest.mark.asyncio
    async def test_load_corrupted_file(self, temp_path):
        """Test that corrupted file results in empty store."""
        # Write invalid JSON
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text("not valid json")

        store = FileTokenStore(path=temp_path)
        characters = await store.list_characters()
        assert len(characters) == 0


class TestTokenStoreDependency:
    """Tests for token store dependency injection."""

    def test_set_and_get_token_store(self):
        """Test setting and getting the global token store."""
        original_store = MemoryTokenStore()
        set_token_store(original_store)

        retrieved = get_token_store()
        assert retrieved is original_store

        # Clean up
        set_token_store(None)
