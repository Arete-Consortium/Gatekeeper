"""Unit tests for token storage service."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.token_store import (
    FileTokenStore,
    MemoryTokenStore,
    RedisTokenStore,
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


class TestFileTokenStoreEdgeCases:
    """Edge case tests for file token store."""

    @pytest.fixture
    def temp_path(self):
        """Create a temporary file path for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "tokens.json"

    @pytest.fixture
    def store(self, temp_path):
        """Create a file token store with temp path."""
        return FileTokenStore(path=temp_path)

    @pytest.mark.asyncio
    async def test_remove_nonexistent_token(self, store):
        """Test removing a token that doesn't exist returns False."""
        result = await store.remove_token(99999)
        assert result is False


class TestRedisTokenStore:
    """Tests for Redis-based token storage with mocked Redis."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        mock.hset = AsyncMock(return_value=True)
        mock.hgetall = AsyncMock(return_value={})
        mock.delete = AsyncMock(return_value=1)
        mock.sadd = AsyncMock(return_value=1)
        mock.srem = AsyncMock(return_value=1)
        mock.smembers = AsyncMock(return_value=set())
        return mock

    @pytest.fixture
    def store(self, mock_redis):
        """Create a RedisTokenStore with mocked Redis."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            store = RedisTokenStore("redis://localhost:6379")
        return store

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
    async def test_store_token(self, store, mock_redis, sample_token_data):
        """Test storing a token in Redis."""
        await store.store_token(**sample_token_data)

        mock_redis.hset.assert_called_once()
        mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_found(self, store, mock_redis, sample_token_data):
        """Test getting a token from Redis."""
        mock_redis.hgetall.return_value = {
            b"character_id": b"12345",
            b"access_token": b"access_token_123",
            b"refresh_token": b"refresh_token_123",
            b"expires_at": sample_token_data["expires_at"].isoformat().encode(),
            b"character_name": b"Test Pilot",
            b"scopes": b'["esi-location.read_location.v1"]',
        }

        result = await store.get_token(12345)

        assert result is not None
        assert result["character_id"] == 12345
        assert result["access_token"] == "access_token_123"
        assert result["character_name"] == "Test Pilot"
        assert result["scopes"] == ["esi-location.read_location.v1"]

    @pytest.mark.asyncio
    async def test_get_token_not_found(self, store, mock_redis):
        """Test getting a non-existent token from Redis."""
        mock_redis.hgetall.return_value = {}

        result = await store.get_token(99999)

        assert result is None

    @pytest.mark.asyncio
    async def test_remove_token(self, store, mock_redis):
        """Test removing a token from Redis."""
        mock_redis.delete.return_value = 1

        result = await store.remove_token(12345)

        assert result is True
        mock_redis.delete.assert_called_once()
        mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_token_not_found(self, store, mock_redis):
        """Test removing a non-existent token from Redis."""
        mock_redis.delete.return_value = 0

        result = await store.remove_token(99999)

        assert result is False

    @pytest.mark.asyncio
    async def test_list_characters(self, store, mock_redis, sample_token_data):
        """Test listing characters from Redis."""
        mock_redis.smembers.return_value = {b"12345", b"67890"}
        mock_redis.hgetall.side_effect = [
            {
                b"character_id": b"12345",
                b"access_token": b"token1",
                b"refresh_token": b"refresh1",
                b"expires_at": sample_token_data["expires_at"].isoformat().encode(),
                b"character_name": b"Pilot 1",
                b"scopes": b"[]",
            },
            {
                b"character_id": b"67890",
                b"access_token": b"token2",
                b"refresh_token": b"refresh2",
                b"expires_at": sample_token_data["expires_at"].isoformat().encode(),
                b"character_name": b"Pilot 2",
                b"scopes": b"[]",
            },
        ]

        characters = await store.list_characters()

        assert len(characters) == 2
        char_ids = {c["character_id"] for c in characters}
        assert 12345 in char_ids
        assert 67890 in char_ids

    @pytest.mark.asyncio
    async def test_list_characters_with_invalid_entry(self, store, mock_redis, sample_token_data):
        """Test listing characters handles missing entries."""
        mock_redis.smembers.return_value = {b"12345", b"99999"}
        mock_redis.hgetall.side_effect = [
            {
                b"character_id": b"12345",
                b"access_token": b"token1",
                b"refresh_token": b"refresh1",
                b"expires_at": sample_token_data["expires_at"].isoformat().encode(),
                b"character_name": b"Pilot 1",
                b"scopes": b"[]",
            },
            {},  # 99999 not found
        ]

        characters = await store.list_characters()

        assert len(characters) == 1
        assert characters[0]["character_id"] == 12345

    @pytest.mark.asyncio
    async def test_clear_all(self, store, mock_redis, sample_token_data):
        """Test clearing all tokens from Redis."""
        mock_redis.smembers.return_value = {b"12345", b"67890"}
        mock_redis.delete.return_value = 1

        count = await store.clear_all()

        assert count == 2
        assert mock_redis.delete.call_count == 2


class TestTokenStoreDependency:
    """Tests for token store dependency injection."""

    @pytest.fixture(autouse=True)
    def reset_store(self):
        """Reset the global token store before/after each test."""
        import backend.app.services.token_store as module

        module._token_store = None
        yield
        module._token_store = None

    def test_set_and_get_token_store(self):
        """Test setting and getting the global token store."""
        original_store = MemoryTokenStore()
        set_token_store(original_store)

        retrieved = get_token_store()
        assert retrieved is original_store

    def test_get_token_store_creates_redis_when_url_set(self):
        """Test get_token_store creates Redis store when REDIS_URL is set."""
        mock_redis = MagicMock()

        with patch("backend.app.services.token_store.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"

            with patch("redis.asyncio.from_url", return_value=mock_redis):
                store = get_token_store()

            assert isinstance(store, RedisTokenStore)

    def test_get_token_store_creates_memory_in_debug(self):
        """Test get_token_store creates memory store in DEBUG mode."""
        with patch("backend.app.services.token_store.settings") as mock_settings:
            mock_settings.REDIS_URL = None
            mock_settings.DEBUG = True

            store = get_token_store()

            assert isinstance(store, MemoryTokenStore)

    def test_get_token_store_creates_file_in_production(self):
        """Test get_token_store creates file store in production."""
        with patch("backend.app.services.token_store.settings") as mock_settings:
            mock_settings.REDIS_URL = None
            mock_settings.DEBUG = False

            with patch.object(FileTokenStore, "__init__", return_value=None):
                store = get_token_store()

                assert isinstance(store, FileTokenStore)

    def test_get_token_store_caches_instance(self):
        """Test get_token_store returns cached instance."""
        with patch("backend.app.services.token_store.settings") as mock_settings:
            mock_settings.REDIS_URL = None
            mock_settings.DEBUG = True

            store1 = get_token_store()
            store2 = get_token_store()

            assert store1 is store2
