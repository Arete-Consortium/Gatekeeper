"""Tests for zKillboard statistics service."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.models.risk import ZKillStats
from backend.app.services.zkill_stats import (
    ZKillStatsPreloader,
    build_zkill_stats_key,
    get_cached_stats_sync,
    get_zkill_preloader,
)


class TestBuildZkillStatsKey:
    """Tests for build_zkill_stats_key function."""

    def test_builds_correct_key(self):
        """Should build correct cache key format."""
        key = build_zkill_stats_key(30000142)
        assert key == "zkill:stats:30000142"

    def test_different_system_ids(self):
        """Should produce different keys for different systems."""
        key1 = build_zkill_stats_key(30000142)
        key2 = build_zkill_stats_key(30002187)
        assert key1 != key2

    def test_handles_large_system_id(self):
        """Should handle large system IDs."""
        key = build_zkill_stats_key(99999999999)
        assert "99999999999" in key


class TestZKillStats:
    """Tests for ZKillStats model."""

    def test_default_values(self):
        """Should have zero defaults."""
        stats = ZKillStats()
        assert stats.recent_kills == 0
        assert stats.recent_pods == 0

    def test_with_values(self):
        """Should accept custom values."""
        stats = ZKillStats(recent_kills=10, recent_pods=5)
        assert stats.recent_kills == 10
        assert stats.recent_pods == 5

    def test_model_dump(self):
        """Should serialize to dict."""
        stats = ZKillStats(recent_kills=10, recent_pods=5)
        data = stats.model_dump()
        assert data == {"recent_kills": 10, "recent_pods": 5}


class TestZKillStatsPreloader:
    """Tests for ZKillStatsPreloader class."""

    def test_init(self):
        """Should initialize with default values."""
        preloader = ZKillStatsPreloader()
        assert preloader._running is False
        assert preloader._task is None

    def test_priority_systems(self):
        """Should have priority systems defined."""
        preloader = ZKillStatsPreloader()
        assert len(preloader._priority_systems) > 0
        # Should include major trade hubs
        assert 30000142 in preloader._priority_systems  # Jita
        assert 30002187 in preloader._priority_systems  # Amarr

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        """Start should set running flag."""
        preloader = ZKillStatsPreloader()

        with patch.object(preloader, "_preload_loop", new_callable=AsyncMock):
            await preloader.start()
            assert preloader._running is True
            await preloader.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Multiple starts should be safe."""
        preloader = ZKillStatsPreloader()

        with patch.object(preloader, "_preload_loop", new_callable=AsyncMock):
            await preloader.start()
            await preloader.start()  # Should not error
            assert preloader._running is True
            await preloader.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running(self):
        """Stop should clear running flag."""
        preloader = ZKillStatsPreloader()

        with patch.object(preloader, "_preload_loop", new_callable=AsyncMock):
            await preloader.start()
            await preloader.stop()
            assert preloader._running is False


class TestGetZkillPreloader:
    """Tests for get_zkill_preloader function."""

    def test_returns_preloader(self):
        """Should return a preloader instance."""
        preloader = get_zkill_preloader()
        assert isinstance(preloader, ZKillStatsPreloader)

    def test_returns_same_instance(self):
        """Should return the same instance on multiple calls."""
        p1 = get_zkill_preloader()
        p2 = get_zkill_preloader()
        assert p1 is p2


class TestGetCachedStatsSync:
    """Tests for get_cached_stats_sync function."""

    def test_returns_none_when_not_cached(self):
        """Should return None when stats not in cache."""
        # This will use the memory cache which should be empty for this key
        result = get_cached_stats_sync(99999999)
        assert result is None
