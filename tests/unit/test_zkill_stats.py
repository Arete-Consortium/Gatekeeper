"""Tests for zKillboard statistics service."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.models.risk import ZKillStats
from backend.app.services.zkill_stats import (
    ZKillStatsPreloader,
    _rate_limit,
    build_zkill_stats_key,
    fetch_bulk_system_stats,
    fetch_system_kills,
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

    def test_returns_stats_when_cached(self):
        """Should return stats when in cache."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()
        cache_key = "zkill:stats:30000142"
        # Manually insert into the cache
        mock_cache._get_cache(600)[cache_key] = json.dumps({"recent_kills": 10, "recent_pods": 5})

        with patch("backend.app.services.zkill_stats.get_cache_sync", return_value=mock_cache):
            result = get_cached_stats_sync(30000142)

        assert result is not None
        assert result.recent_kills == 10
        assert result.recent_pods == 5

    def test_returns_none_on_invalid_json(self):
        """Should return None if cached value is invalid JSON."""
        from backend.app.services.cache import MemoryCacheService

        mock_cache = MemoryCacheService()
        cache_key = "zkill:stats:30000142"
        mock_cache._get_cache(600)[cache_key] = "not valid json"

        with patch("backend.app.services.zkill_stats.get_cache_sync", return_value=mock_cache):
            result = get_cached_stats_sync(30000142)

        assert result is None


class TestRateLimit:
    """Tests for _rate_limit function."""

    @pytest.mark.asyncio
    async def test_rate_limit_updates_timestamp(self):
        """Rate limit should update last request time."""
        import backend.app.services.zkill_stats as module

        old_time = module._last_request_time

        await _rate_limit()

        assert module._last_request_time > old_time


class TestFetchSystemKills:
    """Tests for fetch_system_kills function."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache for testing."""
        cache = AsyncMock()
        cache.get_json = AsyncMock(return_value=None)  # Cache miss
        cache.set_json = AsyncMock(return_value=True)
        return cache

    @pytest.mark.asyncio
    async def test_returns_cached_stats(self):
        """Should return cached stats without API call."""
        mock_cache = AsyncMock()
        mock_cache.get_json = AsyncMock(return_value={"recent_kills": 10, "recent_pods": 5})

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            result = await fetch_system_kills(30000142)

        assert result.recent_kills == 10
        assert result.recent_pods == 5

    @pytest.mark.asyncio
    async def test_fetches_from_api_on_cache_miss(self, mock_cache):
        """Should fetch from zKillboard API on cache miss."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"victim": {"ship_type_id": 587}},  # Regular ship kill
            {"victim": {"ship_type_id": 670}},  # Pod kill
        ]
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch(
                "backend.app.services.zkill_stats.httpx.AsyncClient", return_value=mock_client
            ):
                with patch("backend.app.services.zkill_stats._rate_limit", new_callable=AsyncMock):
                    result = await fetch_system_kills(30000142)

        assert result.recent_kills == 1
        assert result.recent_pods == 1
        mock_cache.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_timeout_exception(self, mock_cache):
        """Should return empty stats on timeout."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch(
                "backend.app.services.zkill_stats.httpx.AsyncClient", return_value=mock_client
            ):
                with patch("backend.app.services.zkill_stats._rate_limit", new_callable=AsyncMock):
                    result = await fetch_system_kills(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_handles_rate_limit_429(self, mock_cache):
        """Should return empty stats on 429 rate limit."""
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Rate limited", request=MagicMock(), response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch(
                "backend.app.services.zkill_stats.httpx.AsyncClient", return_value=mock_client
            ):
                with patch("backend.app.services.zkill_stats._rate_limit", new_callable=AsyncMock):
                    result = await fetch_system_kills(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_handles_http_error(self, mock_cache):
        """Should return empty stats on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch(
                "backend.app.services.zkill_stats.httpx.AsyncClient", return_value=mock_client
            ):
                with patch("backend.app.services.zkill_stats._rate_limit", new_callable=AsyncMock):
                    result = await fetch_system_kills(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self, mock_cache):
        """Should return empty stats on generic exception."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Unknown error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch(
                "backend.app.services.zkill_stats.httpx.AsyncClient", return_value=mock_client
            ):
                with patch("backend.app.services.zkill_stats._rate_limit", new_callable=AsyncMock):
                    result = await fetch_system_kills(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_handles_non_list_response(self, mock_cache):
        """Should handle API returning non-list response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # Not a list
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch(
                "backend.app.services.zkill_stats.httpx.AsyncClient", return_value=mock_client
            ):
                with patch("backend.app.services.zkill_stats._rate_limit", new_callable=AsyncMock):
                    result = await fetch_system_kills(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_counts_genolution_pods(self, mock_cache):
        """Should count Genolution capsules as pods."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"victim": {"ship_type_id": 33328}},  # Genolution pod
        ]
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch(
                "backend.app.services.zkill_stats.httpx.AsyncClient", return_value=mock_client
            ):
                with patch("backend.app.services.zkill_stats._rate_limit", new_callable=AsyncMock):
                    result = await fetch_system_kills(30000142)

        assert result.recent_pods == 1


class TestFetchBulkSystemStats:
    """Tests for fetch_bulk_system_stats function."""

    @pytest.mark.asyncio
    async def test_returns_cached_stats_first(self):
        """Should check cache before fetching."""
        mock_cache = AsyncMock()
        mock_cache.get_json = AsyncMock(
            side_effect=[
                {"recent_kills": 10, "recent_pods": 5},  # Cache hit for first system
                None,  # Cache miss for second system
            ]
        )

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch("backend.app.services.zkill_stats.fetch_system_kills") as mock_fetch:
                mock_fetch.return_value = ZKillStats(recent_kills=1, recent_pods=0)

                result = await fetch_bulk_system_stats([30000142, 30002187])

        assert result[30000142].recent_kills == 10
        # Second system should be fetched
        mock_fetch.assert_called_once_with(30002187, 24)

    @pytest.mark.asyncio
    async def test_fetches_uncached_systems(self):
        """Should fetch stats for uncached systems."""
        mock_cache = AsyncMock()
        mock_cache.get_json = AsyncMock(return_value=None)  # All cache misses

        with patch("backend.app.services.zkill_stats.get_cache", return_value=mock_cache):
            with patch("backend.app.services.zkill_stats.fetch_system_kills") as mock_fetch:
                mock_fetch.return_value = ZKillStats(recent_kills=5, recent_pods=2)

                result = await fetch_bulk_system_stats([30000142, 30002187])

        assert len(result) == 2
        assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty_dict(self):
        """Should return empty dict for empty input."""
        result = await fetch_bulk_system_stats([])
        assert result == {}


class TestPreloaderLoop:
    """Tests for ZKillStatsPreloader._preload_loop."""

    @pytest.mark.asyncio
    async def test_preload_loop_fetches_stats(self):
        """Preload loop should fetch stats for priority systems."""
        preloader = ZKillStatsPreloader()

        with patch("backend.app.services.zkill_stats.fetch_bulk_system_stats") as mock_fetch:
            mock_fetch.return_value = {}

            # Start and quickly stop
            preloader._running = True
            task = asyncio.create_task(preloader._preload_loop())

            await asyncio.sleep(0.1)
            preloader._running = False
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_preload_loop_handles_exception(self):
        """Preload loop should handle exceptions gracefully."""
        preloader = ZKillStatsPreloader()

        call_count = 0

        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return {}

        with patch(
            "backend.app.services.zkill_stats.fetch_bulk_system_stats", side_effect=mock_fetch
        ):
            preloader._running = True
            task = asyncio.create_task(preloader._preload_loop())

            await asyncio.sleep(0.1)
            preloader._running = False
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            # Should have attempted at least once
            assert call_count >= 1
