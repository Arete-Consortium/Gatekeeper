"""Unit tests for risk calculation caching."""

import pytest

from backend.app.api.v1.systems import (
    RISK_CACHE_TTL,
    _build_risk_cache_key,
)


class TestRiskCacheKeyBuilder:
    """Tests for risk cache key generation."""

    def test_basic_key_generation(self):
        """Test basic risk cache key format."""
        key = _build_risk_cache_key(
            system_name="Jita",
            live=True,
            ship_profile=None,
        )
        assert key == "risk:Jita:True:default"

    def test_key_with_ship_profile(self):
        """Test cache key includes ship profile."""
        key = _build_risk_cache_key(
            system_name="Jita",
            live=True,
            ship_profile="hauler",
        )
        assert key == "risk:Jita:True:hauler"

    def test_key_without_live_data(self):
        """Test cache key differs when live=False."""
        key_live = _build_risk_cache_key(
            system_name="Jita",
            live=True,
            ship_profile=None,
        )
        key_cached = _build_risk_cache_key(
            system_name="Jita",
            live=False,
            ship_profile=None,
        )
        assert key_live != key_cached
        assert "True" in key_live
        assert "False" in key_cached

    def test_different_systems_different_keys(self):
        """Test that different systems produce different keys."""
        key_jita = _build_risk_cache_key("Jita", True, None)
        key_amarr = _build_risk_cache_key("Amarr", True, None)
        key_rancer = _build_risk_cache_key("Rancer", True, None)
        assert key_jita != key_amarr != key_rancer

    def test_different_profiles_different_keys(self):
        """Test that different ship profiles produce different keys."""
        key_default = _build_risk_cache_key("Jita", True, None)
        key_hauler = _build_risk_cache_key("Jita", True, "hauler")
        key_frigate = _build_risk_cache_key("Jita", True, "frigate")
        key_capital = _build_risk_cache_key("Jita", True, "capital")
        assert key_default != key_hauler != key_frigate != key_capital

    def test_all_ship_profiles(self):
        """Test cache keys for all ship profiles."""
        profiles = ["hauler", "frigate", "cruiser", "battleship", "mining", "capital", "cloaky"]
        keys = [_build_risk_cache_key("Jita", True, p) for p in profiles]
        # All keys should be unique
        assert len(keys) == len(set(keys))

    def test_nullsec_system_key(self):
        """Test cache key for nullsec system."""
        key = _build_risk_cache_key("HED-GP", True, "capital")
        assert "HED-GP" in key
        assert "capital" in key


class TestRiskCacheTTL:
    """Tests for risk cache TTL configuration."""

    def test_risk_cache_ttl_is_set(self):
        """Test that risk cache TTL is configured."""
        assert RISK_CACHE_TTL > 0

    def test_risk_cache_ttl_reasonable(self):
        """Test TTL is reasonable (shorter than route TTL due to dynamic data)."""
        from backend.app.api.v1.routing import ROUTE_CACHE_TTL

        # Risk TTL should be shorter since zKill data changes more frequently
        assert RISK_CACHE_TTL <= ROUTE_CACHE_TTL
        # But not too short (at least 30 seconds)
        assert RISK_CACHE_TTL >= 30


class TestRiskCachingIntegration:
    """Integration tests for risk caching behavior."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Reset global cache before each test."""
        import backend.app.services.cache as cache_module

        cache_module._cache = None
        yield
        cache_module._cache = None

    @pytest.mark.asyncio
    async def test_risk_cache_hit_returns_cached_data(self):
        """Test that cached risk reports are returned on cache hit."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()
        cached_risk = {
            "system_name": "Rancer",
            "score": 75.5,
            "danger_level": "high",
            "breakdown": {
                "security_component": 40.0,
                "kills_component": 25.5,
                "pods_component": 10.0,
            },
            "zkill_stats": {
                "recent_kills": 50,
                "recent_pods": 20,
            },
            "ship_profile": None,
        }

        # Pre-populate cache
        key = _build_risk_cache_key("Rancer", True, None)
        await mock_cache.set_json(key, cached_risk, ttl=RISK_CACHE_TTL)

        # Verify data is in cache
        result = await mock_cache.get_json(key)
        assert result is not None
        assert result["score"] == 75.5
        assert result["danger_level"] == "high"

    @pytest.mark.asyncio
    async def test_risk_cache_miss_for_empty_cache(self):
        """Test that cache miss occurs for uncached systems."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()

        # Cache should be empty
        key = _build_risk_cache_key("Jita", True, None)
        result = await mock_cache.get_json(key)
        assert result is None

    @pytest.mark.asyncio
    async def test_risk_cache_stores_computed_result(self):
        """Test that computed risk reports are stored in cache."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()
        risk_data = {
            "system_name": "Jita",
            "score": 5.0,
            "danger_level": "low",
            "breakdown": {
                "security_component": 5.0,
                "kills_component": 0.0,
                "pods_component": 0.0,
            },
            "zkill_stats": None,
            "ship_profile": None,
        }

        key = _build_risk_cache_key("Jita", True, None)

        # Store in cache
        await mock_cache.set_json(key, risk_data, ttl=RISK_CACHE_TTL)

        # Verify storage
        stored = await mock_cache.get_json(key)
        assert stored["score"] == 5.0
        assert stored["system_name"] == "Jita"

    @pytest.mark.asyncio
    async def test_different_profiles_cached_separately(self):
        """Test that different ship profiles are cached separately."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()

        # Cache data for default profile
        default_risk = {"system_name": "Rancer", "score": 50.0, "ship_profile": None}
        await mock_cache.set_json(
            _build_risk_cache_key("Rancer", True, None), default_risk, ttl=RISK_CACHE_TTL
        )

        # Cache data for hauler profile (higher risk)
        hauler_risk = {"system_name": "Rancer", "score": 85.0, "ship_profile": "hauler"}
        await mock_cache.set_json(
            _build_risk_cache_key("Rancer", True, "hauler"), hauler_risk, ttl=RISK_CACHE_TTL
        )

        # Verify separate storage
        default_result = await mock_cache.get_json(_build_risk_cache_key("Rancer", True, None))
        hauler_result = await mock_cache.get_json(_build_risk_cache_key("Rancer", True, "hauler"))

        assert default_result["score"] == 50.0
        assert hauler_result["score"] == 85.0


class TestRiskCacheMetrics:
    """Tests for risk cache metrics recording."""

    def test_record_risk_cache_hit_increments_counter(self):
        """Test that cache hits are recorded in metrics."""
        from backend.app.api.metrics import RISK_CACHE_HITS, record_risk_cache_hit

        # Get current value
        initial = RISK_CACHE_HITS._value.get()

        record_risk_cache_hit()

        # Verify increment
        after = RISK_CACHE_HITS._value.get()
        assert after == initial + 1

    def test_record_risk_cache_miss_increments_counter(self):
        """Test that cache misses are recorded in metrics."""
        from backend.app.api.metrics import RISK_CACHE_MISSES, record_risk_cache_miss

        # Get current value
        initial = RISK_CACHE_MISSES._value.get()

        record_risk_cache_miss()

        # Verify increment
        after = RISK_CACHE_MISSES._value.get()
        assert after == initial + 1

    def test_risk_metrics_are_counters(self):
        """Test that risk metrics are cumulative counters."""
        from backend.app.api.metrics import (
            RISK_CACHE_HITS,
            RISK_CACHE_MISSES,
            record_risk_cache_hit,
            record_risk_cache_miss,
        )

        # Record multiple times
        initial_hits = RISK_CACHE_HITS._value.get()
        initial_misses = RISK_CACHE_MISSES._value.get()

        for _ in range(5):
            record_risk_cache_hit()
        for _ in range(3):
            record_risk_cache_miss()

        assert RISK_CACHE_HITS._value.get() == initial_hits + 5
        assert RISK_CACHE_MISSES._value.get() == initial_misses + 3
