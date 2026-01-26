"""Unit tests for cache service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.cache import (
    MemoryCacheService,
    RedisCacheService,
    build_esi_key,
    build_risk_key,
    build_route_key,
    get_cache,
    get_cache_sync,
)


class TestMemoryCacheService:
    """Tests for in-memory cache service."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance."""
        return MemoryCacheService(maxsize=100)

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        await cache.set("test_key", "test_value", ttl=60)
        result = await cache.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache):
        """Test getting a nonexistent key returns None."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test exists check."""
        await cache.set("test_key", "test_value", ttl=60)
        assert await cache.exists("test_key") is True
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_delete(self, cache):
        """Test delete operation."""
        await cache.set("test_key", "test_value", ttl=60)
        assert await cache.exists("test_key") is True

        result = await cache.delete("test_key")
        assert result is True
        assert await cache.exists("test_key") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache):
        """Test deleting nonexistent key returns False."""
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all cache entries."""
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=60)

        result = await cache.clear()
        assert result is True
        assert await cache.exists("key1") is False
        assert await cache.exists("key2") is False

    @pytest.mark.asyncio
    async def test_set_json_and_get_json(self, cache):
        """Test JSON serialization convenience methods."""
        data = {"name": "Jita", "security": 0.95, "kills": [1, 2, 3]}

        await cache.set_json("json_key", data, ttl=60)
        result = await cache.get_json("json_key")

        assert result == data
        assert result["name"] == "Jita"
        assert result["kills"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_json_nonexistent(self, cache):
        """Test get_json for nonexistent key."""
        result = await cache.get_json("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        """Test cache statistics."""
        # Generate some hits and misses
        await cache.set("key1", "value1", ttl=60)
        await cache.get("key1")  # Hit
        await cache.get("key1")  # Hit
        await cache.get("nonexistent")  # Miss

        stats = cache.get_stats()
        assert stats["type"] == "memory"
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == pytest.approx(2 / 3)


class TestMemoryCacheServiceEdgeCases:
    """Edge case tests for memory cache."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache instance."""
        return MemoryCacheService(maxsize=100)

    @pytest.mark.asyncio
    async def test_different_ttls_stored_separately(self, cache):
        """Test that keys with different TTLs are stored correctly."""
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=120)

        # Both should be retrievable
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_overwrite_same_key(self, cache):
        """Test overwriting a key with new value."""
        await cache.set("key", "original", ttl=60)
        await cache.set("key", "updated", ttl=60)

        result = await cache.get("key")
        assert result == "updated"

    @pytest.mark.asyncio
    async def test_get_json_invalid_json(self, cache):
        """Test get_json with invalid JSON returns None."""
        await cache.set("bad_json", "not valid json {{{", ttl=60)

        result = await cache.get_json("bad_json")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_json_with_custom_object(self, cache):
        """Test set_json with custom object uses default=str."""

        class CustomObj:
            def __str__(self):
                return "custom_str_repr"

        # The cache uses default=str, so custom objects get stringified
        result = await cache.set_json("key", {"obj": CustomObj()}, ttl=60)
        assert result is True

        # Value should contain string representation
        stored = await cache.get_json("key")
        assert "custom_str_repr" in str(stored)

    @pytest.mark.asyncio
    async def test_delete_from_multiple_ttl_caches(self, cache):
        """Test delete removes key from all TTL caches."""
        # Store same key with different TTLs (simulating overwrites)
        await cache.set("key", "v1", ttl=60)

        # Delete should work
        result = await cache.delete("key")
        assert result is True
        assert await cache.exists("key") is False

    @pytest.mark.asyncio
    async def test_stats_initial_values(self, cache):
        """Test cache stats before any operations."""
        stats = cache.get_stats()
        assert stats["type"] == "memory"
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["entries"] == 0

    @pytest.mark.asyncio
    async def test_stats_entries_count(self, cache):
        """Test that entries count is accurate."""
        await cache.set("key1", "value1", ttl=60)
        await cache.set("key2", "value2", ttl=60)
        await cache.set("key3", "value3", ttl=120)  # Different TTL

        stats = cache.get_stats()
        assert stats["entries"] == 3


class TestCacheKeyBuilders:
    """Tests for cache key builder functions."""

    def test_build_route_key(self):
        """Test route cache key generation."""
        key = build_route_key("Jita", "Amarr", "safer")
        assert key == "route:Jita:Amarr:safer"

    def test_build_risk_key(self):
        """Test risk cache key generation."""
        key = build_risk_key("Jita")
        assert key == "risk:Jita"

    def test_build_esi_key(self):
        """Test ESI cache key generation."""
        key = build_esi_key("/universe/systems/30000142/")
        assert key == "esi:/universe/systems/30000142/"

    def test_build_route_key_with_special_chars(self):
        """Test route key with special characters."""
        key = build_route_key("J-GAMP", "HED-GP", "paranoid")
        assert key == "route:J-GAMP:HED-GP:paranoid"

    def test_build_risk_key_nullsec(self):
        """Test risk key for nullsec system."""
        key = build_risk_key("PR-8CA")
        assert key == "risk:PR-8CA"


class TestRedisCacheService:
    """Tests for Redis cache service with mocked redis."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.setex = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.exists = AsyncMock(return_value=1)
        mock.flushdb = AsyncMock(return_value=True)
        mock.ping = AsyncMock(return_value=True)
        mock.close = AsyncMock(return_value=None)
        return mock

    @pytest.fixture
    def redis_cache(self, mock_redis):
        """Create a RedisCacheService with mocked redis."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            cache = RedisCacheService("redis://localhost:6379")
        return cache

    @pytest.mark.asyncio
    async def test_redis_get_hit(self, redis_cache, mock_redis):
        """Test Redis get with cache hit."""
        mock_redis.get = AsyncMock(return_value="cached_value")

        result = await redis_cache.get("test_key")

        assert result == "cached_value"
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_redis_get_miss(self, redis_cache, mock_redis):
        """Test Redis get with cache miss."""
        mock_redis.get = AsyncMock(return_value=None)

        result = await redis_cache.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_redis_get_exception(self, redis_cache, mock_redis):
        """Test Redis get handles exceptions gracefully."""
        mock_redis.get = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_cache.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_redis_set(self, redis_cache, mock_redis):
        """Test Redis set operation."""
        result = await redis_cache.set("test_key", "test_value", ttl=300)

        assert result is True
        mock_redis.setex.assert_called_once_with("test_key", 300, "test_value")

    @pytest.mark.asyncio
    async def test_redis_set_exception(self, redis_cache, mock_redis):
        """Test Redis set handles exceptions gracefully."""
        mock_redis.setex = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_cache.set("test_key", "test_value")

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_delete(self, redis_cache, mock_redis):
        """Test Redis delete operation."""
        mock_redis.delete = AsyncMock(return_value=1)

        result = await redis_cache.delete("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_redis_delete_not_found(self, redis_cache, mock_redis):
        """Test Redis delete when key doesn't exist."""
        mock_redis.delete = AsyncMock(return_value=0)

        result = await redis_cache.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_delete_exception(self, redis_cache, mock_redis):
        """Test Redis delete handles exceptions gracefully."""
        mock_redis.delete = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_cache.delete("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_exists(self, redis_cache, mock_redis):
        """Test Redis exists operation."""
        mock_redis.exists = AsyncMock(return_value=1)

        result = await redis_cache.exists("test_key")

        assert result is True

    @pytest.mark.asyncio
    async def test_redis_exists_not_found(self, redis_cache, mock_redis):
        """Test Redis exists when key doesn't exist."""
        mock_redis.exists = AsyncMock(return_value=0)

        result = await redis_cache.exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_exists_exception(self, redis_cache, mock_redis):
        """Test Redis exists handles exceptions gracefully."""
        mock_redis.exists = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_cache.exists("test_key")

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_clear(self, redis_cache, mock_redis):
        """Test Redis clear operation."""
        result = await redis_cache.clear()

        assert result is True
        mock_redis.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_clear_exception(self, redis_cache, mock_redis):
        """Test Redis clear handles exceptions gracefully."""
        mock_redis.flushdb = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_cache.clear()

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_ping(self, redis_cache, mock_redis):
        """Test Redis ping operation."""
        mock_redis.ping = AsyncMock(return_value=True)

        result = await redis_cache.ping()

        assert result is True

    @pytest.mark.asyncio
    async def test_redis_ping_failure(self, redis_cache, mock_redis):
        """Test Redis ping when connection fails."""
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))

        result = await redis_cache.ping()

        assert result is False

    @pytest.mark.asyncio
    async def test_redis_close(self, redis_cache, mock_redis):
        """Test Redis close operation."""
        await redis_cache.close()

        mock_redis.close.assert_called_once()

    def test_redis_get_stats(self, redis_cache):
        """Test Redis cache statistics."""
        stats = redis_cache.get_stats()

        assert stats["type"] == "redis"
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_ratio"] == 0

    @pytest.mark.asyncio
    async def test_redis_stats_after_operations(self, redis_cache, mock_redis):
        """Test Redis stats track hits and misses."""
        # Simulate a hit
        mock_redis.get = AsyncMock(return_value="value")
        await redis_cache.get("key1")

        # Simulate a miss
        mock_redis.get = AsyncMock(return_value=None)
        await redis_cache.get("key2")

        stats = redis_cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5


class TestGetCache:
    """Tests for get_cache factory function."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset global cache before each test."""
        import backend.app.services.cache as cache_module

        cache_module._cache = None
        yield
        cache_module._cache = None

    @pytest.mark.asyncio
    async def test_get_cache_returns_memory_when_no_redis(self):
        """Test get_cache returns memory cache when Redis URL is not set."""
        with patch("backend.app.services.cache.settings") as mock_settings:
            mock_settings.REDIS_URL = None

            cache = await get_cache()

            assert isinstance(cache, MemoryCacheService)

    @pytest.mark.asyncio
    async def test_get_cache_returns_redis_when_available(self):
        """Test get_cache returns Redis cache when Redis is available."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("backend.app.services.cache.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"

            with patch("redis.asyncio.from_url", return_value=mock_redis):
                cache = await get_cache()

            assert isinstance(cache, RedisCacheService)

    @pytest.mark.asyncio
    async def test_get_cache_fallback_when_redis_ping_fails(self):
        """Test get_cache falls back to memory when Redis ping fails."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=False)

        with patch("backend.app.services.cache.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"

            with patch("redis.asyncio.from_url", return_value=mock_redis):
                cache = await get_cache()

            assert isinstance(cache, MemoryCacheService)

    @pytest.mark.asyncio
    async def test_get_cache_fallback_on_redis_exception(self):
        """Test get_cache falls back to memory when Redis connection fails."""
        with patch("backend.app.services.cache.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"

            with patch("redis.asyncio.from_url", side_effect=Exception("Connection refused")):
                cache = await get_cache()

            assert isinstance(cache, MemoryCacheService)

    @pytest.mark.asyncio
    async def test_get_cache_caches_instance(self):
        """Test get_cache returns cached instance on subsequent calls."""
        with patch("backend.app.services.cache.settings") as mock_settings:
            mock_settings.REDIS_URL = None

            cache1 = await get_cache()
            cache2 = await get_cache()

            assert cache1 is cache2


class TestGetCacheSync:
    """Tests for get_cache_sync function."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset global cache before each test."""
        import backend.app.services.cache as cache_module

        cache_module._cache = None
        yield
        cache_module._cache = None

    def test_get_cache_sync_creates_memory_cache(self):
        """Test get_cache_sync creates memory cache when none exists."""
        cache = get_cache_sync()

        assert isinstance(cache, MemoryCacheService)

    def test_get_cache_sync_returns_existing_cache(self):
        """Test get_cache_sync returns existing cache instance."""
        cache1 = get_cache_sync()
        cache2 = get_cache_sync()

        assert cache1 is cache2

    def test_get_cache_sync_returns_preset_cache(self):
        """Test get_cache_sync returns previously set cache."""
        import backend.app.services.cache as cache_module

        # Pre-set a mock cache
        mock_cache = MagicMock()
        cache_module._cache = mock_cache

        cache = get_cache_sync()

        assert cache is mock_cache
