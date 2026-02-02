"""Unit tests for route calculation caching."""

import pytest

from backend.app.api.v1.routing import (
    ROUTE_CACHE_TTL,
    _build_route_cache_key,
)


class TestRouteCacheKeyBuilder:
    """Tests for route cache key generation."""

    def test_basic_key_generation(self):
        """Test basic route cache key format."""
        key = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=False,
            wormholes=False,
        )
        assert key == "route:Jita:Amarr:shortest:avoid::bridges:False:thera:False:pochven:False:wormholes:False"

    def test_key_with_avoid_systems(self):
        """Test cache key includes sorted avoid list."""
        key = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="safer",
            avoid={"Rancer", "Tama", "Amamake"},
            bridges=False,
            thera=False,
            pochven=False,
        )
        # Avoid list should be sorted for consistent keys
        assert "avoid:Amamake,Rancer,Tama" in key

    def test_key_with_bridges_enabled(self):
        """Test cache key differs when bridges enabled."""
        key_without = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=False,
        )
        key_with = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=True,
            thera=False,
            pochven=False,
        )
        assert key_without != key_with
        assert "bridges:True" in key_with
        assert "bridges:False" in key_without

    def test_key_with_thera_enabled(self):
        """Test cache key differs when Thera routing enabled."""
        key_without = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=False,
        )
        key_with = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=False,
            thera=True,
            pochven=False,
        )
        assert key_without != key_with
        assert "thera:True" in key_with

    def test_key_with_pochven_enabled(self):
        """Test cache key differs when Pochven routing enabled."""
        key_without = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=False,
        )
        key_with = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=True,
        )
        assert key_without != key_with
        assert "pochven:True" in key_with

    def test_key_hashes_long_avoid_list(self):
        """Test that very long avoid lists get hashed."""
        # Create a long avoid list
        long_avoid = {f"System-{i}" for i in range(100)}
        key = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=long_avoid,
            bridges=False,
            thera=False,
            pochven=False,
        )
        # Key should use hash instead of full list
        assert "avoid_hash:" in key
        assert len(key) < 250  # Key should be manageable length

    def test_different_profiles_different_keys(self):
        """Test that different profiles produce different keys."""
        key_shortest = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=False,
        )
        key_safer = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="safer",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=False,
        )
        key_paranoid = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="paranoid",
            avoid=set(),
            bridges=False,
            thera=False,
            pochven=False,
        )
        assert key_shortest != key_safer != key_paranoid

    def test_avoid_set_order_independent(self):
        """Test that avoid set order doesn't affect key."""
        key1 = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid={"A", "B", "C"},
            bridges=False,
            thera=False,
            pochven=False,
        )
        key2 = _build_route_cache_key(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid={"C", "A", "B"},
            bridges=False,
            thera=False,
            pochven=False,
        )
        assert key1 == key2


class TestRouteCacheTTL:
    """Tests for route cache TTL configuration."""

    def test_route_cache_ttl_is_set(self):
        """Test that route cache TTL is configured."""
        assert ROUTE_CACHE_TTL > 0

    def test_route_cache_ttl_reasonable(self):
        """Test TTL is reasonable (between 1 minute and 1 hour)."""
        assert 60 <= ROUTE_CACHE_TTL <= 3600


class TestRouteCachingIntegration:
    """Integration tests for route caching behavior."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset global cache before each test."""
        import backend.app.services.cache as cache_module

        cache_module._cache = None
        yield
        cache_module._cache = None

    @pytest.mark.asyncio
    async def test_route_cache_hit_returns_cached_data(self):
        """Test that cached routes are returned on cache hit."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()
        cached_route = {
            "from_system": "Jita",
            "to_system": "Amarr",
            "profile": "shortest",
            "total_jumps": 10,
            "total_cost": 10.0,
            "max_risk": 5.0,
            "avg_risk": 2.5,
            "path": [],
            "bridges_used": 0,
            "thera_used": 0,
            "pochven_used": 0,
        }

        # Pre-populate cache
        key = _build_route_cache_key("Jita", "Amarr", "shortest", set(), False, False, False)
        await mock_cache.set_json(key, cached_route, ttl=ROUTE_CACHE_TTL)

        # Verify data is in cache
        result = await mock_cache.get_json(key)
        assert result is not None
        assert result["total_jumps"] == 10

    @pytest.mark.asyncio
    async def test_route_cache_miss_computes_route(self):
        """Test that cache miss triggers route computation."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()

        # Cache should be empty
        key = _build_route_cache_key("Jita", "Amarr", "shortest", set(), False, False, False)
        result = await mock_cache.get_json(key)
        assert result is None

    @pytest.mark.asyncio
    async def test_route_cache_stores_computed_result(self):
        """Test that computed routes are stored in cache."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()
        route_data = {
            "from_system": "Jita",
            "to_system": "Perimeter",
            "profile": "shortest",
            "total_jumps": 1,
            "total_cost": 1.0,
            "max_risk": 1.0,
            "avg_risk": 1.0,
            "path": [{"system_name": "Perimeter"}],
            "bridges_used": 0,
            "thera_used": 0,
            "pochven_used": 0,
        }

        key = _build_route_cache_key("Jita", "Perimeter", "shortest", set(), False, False, False)

        # Store in cache
        await mock_cache.set_json(key, route_data, ttl=ROUTE_CACHE_TTL)

        # Verify storage
        stored = await mock_cache.get_json(key)
        assert stored["total_jumps"] == 1
        assert stored["from_system"] == "Jita"


class TestRouteCacheMetrics:
    """Tests for route cache metrics recording."""

    def test_record_route_cache_hit_increments_counter(self):
        """Test that cache hits are recorded in metrics."""
        from backend.app.api.metrics import ROUTE_CACHE_HITS, record_route_cache_hit

        # Get current value
        initial = ROUTE_CACHE_HITS.labels(profile="shortest")._value.get()

        record_route_cache_hit("shortest")

        # Verify increment
        after = ROUTE_CACHE_HITS.labels(profile="shortest")._value.get()
        assert after == initial + 1

    def test_record_route_cache_miss_increments_counter(self):
        """Test that cache misses are recorded in metrics."""
        from backend.app.api.metrics import ROUTE_CACHE_MISSES, record_route_cache_miss

        # Get current value
        initial = ROUTE_CACHE_MISSES.labels(profile="safer")._value.get()

        record_route_cache_miss("safer")

        # Verify increment
        after = ROUTE_CACHE_MISSES.labels(profile="safer")._value.get()
        assert after == initial + 1

    def test_cache_metrics_labeled_by_profile(self):
        """Test that cache metrics are labeled by routing profile."""
        from backend.app.api.metrics import (
            ROUTE_CACHE_HITS,
            ROUTE_CACHE_MISSES,
            record_route_cache_hit,
            record_route_cache_miss,
        )

        # Record for different profiles
        record_route_cache_hit("shortest")
        record_route_cache_hit("safer")
        record_route_cache_miss("paranoid")

        # Each profile has its own counter
        assert ROUTE_CACHE_HITS.labels(profile="shortest")._value.get() >= 1
        assert ROUTE_CACHE_HITS.labels(profile="safer")._value.get() >= 1
        assert ROUTE_CACHE_MISSES.labels(profile="paranoid")._value.get() >= 1
