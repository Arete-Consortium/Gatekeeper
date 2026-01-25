"""Unit tests for cache service."""

import pytest

from backend.app.services.cache import (
    MemoryCacheService,
    build_esi_key,
    build_risk_key,
    build_route_key,
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
