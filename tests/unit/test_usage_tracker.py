"""Tests for in-memory usage tracking service and middleware."""

import time
from collections import Counter
from threading import Thread
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.middleware.usage import _FEATURE_PATTERNS, UsageTrackingMiddleware
from backend.app.services.usage_tracker import (
    _DAU_WINDOW,
    _dau_lock,
    _endpoint_counts,
    _endpoint_lock,
    _feature_counts,
    _feature_lock,
    _ip_timestamps,
    get_dau_estimate,
    get_feature_usage,
    get_top_endpoints,
    track_endpoint,
    track_feature,
    track_request_ip,
)


@pytest.fixture(autouse=True)
def reset_counters():
    """Reset all in-memory counters before and after each test."""
    with _feature_lock:
        _feature_counts.clear()
    with _endpoint_lock:
        _endpoint_counts.clear()
    with _dau_lock:
        _ip_timestamps.clear()
    yield
    with _feature_lock:
        _feature_counts.clear()
    with _endpoint_lock:
        _endpoint_counts.clear()
    with _dau_lock:
        _ip_timestamps.clear()


# =============================================================================
# Feature Usage Tracking
# =============================================================================


class TestFeatureTracking:
    """Tests for feature usage counter operations."""

    def test_track_single_feature(self):
        track_feature("map_views")
        usage = get_feature_usage()
        assert usage["map_views"] == 1

    def test_track_feature_increments(self):
        track_feature("map_views")
        track_feature("map_views")
        track_feature("map_views")
        usage = get_feature_usage()
        assert usage["map_views"] == 3

    def test_track_multiple_features(self):
        track_feature("map_views")
        track_feature("route_calculations")
        track_feature("intel_lookups")
        usage = get_feature_usage()
        assert usage["map_views"] == 1
        assert usage["route_calculations"] == 1
        assert usage["intel_lookups"] == 1

    def test_get_feature_usage_empty(self):
        usage = get_feature_usage()
        assert usage == {}

    def test_get_feature_usage_returns_dict(self):
        """Return value is a plain dict (not Counter)."""
        track_feature("test")
        usage = get_feature_usage()
        assert isinstance(usage, dict)
        assert not isinstance(usage, Counter)

    def test_feature_tracking_thread_safety(self):
        """Concurrent feature tracking does not lose counts."""
        n_threads = 10
        n_increments = 100

        def worker():
            for _ in range(n_increments):
                track_feature("concurrent_test")

        threads = [Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        usage = get_feature_usage()
        assert usage["concurrent_test"] == n_threads * n_increments


# =============================================================================
# Endpoint Hit Tracking
# =============================================================================


class TestEndpointTracking:
    """Tests for endpoint hit counter operations."""

    def test_track_endpoint(self):
        track_endpoint("/api/v1/route")
        endpoints = get_top_endpoints(10)
        assert len(endpoints) == 1
        assert endpoints[0]["endpoint"] == "/api/v1/route"
        assert endpoints[0]["count"] == 1

    def test_track_endpoint_increments(self):
        track_endpoint("/api/v1/route")
        track_endpoint("/api/v1/route")
        endpoints = get_top_endpoints(10)
        assert endpoints[0]["count"] == 2

    def test_top_endpoints_ordering(self):
        """Most-hit endpoints appear first."""
        track_endpoint("/api/v1/route")
        track_endpoint("/api/v1/route")
        track_endpoint("/api/v1/route")
        track_endpoint("/api/v1/map/config")
        track_endpoint("/api/v1/map/config")
        track_endpoint("/api/v1/intel/pilot/123")

        endpoints = get_top_endpoints(10)
        assert endpoints[0]["endpoint"] == "/api/v1/route"
        assert endpoints[0]["count"] == 3
        assert endpoints[1]["endpoint"] == "/api/v1/map/config"
        assert endpoints[1]["count"] == 2

    def test_top_endpoints_limit(self):
        """get_top_endpoints respects the n limit."""
        for i in range(20):
            track_endpoint(f"/api/v1/endpoint_{i}")

        endpoints = get_top_endpoints(5)
        assert len(endpoints) == 5

    def test_top_endpoints_empty(self):
        endpoints = get_top_endpoints(10)
        assert endpoints == []

    def test_top_endpoints_default_limit(self):
        """Default n=10 when not specified."""
        for i in range(15):
            track_endpoint(f"/api/v1/endpoint_{i}")

        endpoints = get_top_endpoints()
        assert len(endpoints) == 10

    def test_endpoint_tracking_thread_safety(self):
        """Concurrent endpoint tracking does not lose counts."""
        n_threads = 10
        n_increments = 100

        def worker():
            for _ in range(n_increments):
                track_endpoint("/api/v1/concurrent")

        threads = [Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        endpoints = get_top_endpoints(1)
        assert endpoints[0]["count"] == n_threads * n_increments


# =============================================================================
# DAU Estimation (Unique IPs in 24h)
# =============================================================================


class TestDAUEstimation:
    """Tests for unique IP DAU estimation."""

    def test_track_single_ip(self):
        track_request_ip("192.168.1.1")
        assert get_dau_estimate() == 1

    def test_track_duplicate_ip(self):
        """Same IP tracked multiple times counts as 1 unique."""
        track_request_ip("192.168.1.1")
        track_request_ip("192.168.1.1")
        track_request_ip("192.168.1.1")
        assert get_dau_estimate() == 1

    def test_track_multiple_unique_ips(self):
        track_request_ip("192.168.1.1")
        track_request_ip("192.168.1.2")
        track_request_ip("192.168.1.3")
        assert get_dau_estimate() == 3

    def test_dau_empty(self):
        assert get_dau_estimate() == 0

    def test_dau_prunes_old_entries(self):
        """IPs older than 24h are pruned during estimation."""
        old_time = time.time() - _DAU_WINDOW - 100
        with _dau_lock:
            _ip_timestamps["old_ip"] = old_time
            _ip_timestamps["recent_ip"] = time.time()

        estimate = get_dau_estimate()
        assert estimate == 1

        with _dau_lock:
            assert "old_ip" not in _ip_timestamps
            assert "recent_ip" in _ip_timestamps

    def test_dau_prunes_all_old(self):
        """All old IPs are pruned, returning 0."""
        old_time = time.time() - _DAU_WINDOW - 100
        with _dau_lock:
            _ip_timestamps["ip1"] = old_time
            _ip_timestamps["ip2"] = old_time

        assert get_dau_estimate() == 0

    def test_dau_thread_safety(self):
        """Concurrent IP tracking does not corrupt state."""
        n_threads = 10

        def worker(thread_id):
            for i in range(50):
                track_request_ip(f"10.0.{thread_id}.{i}")

        threads = [Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 10 threads * 50 unique IPs each = 500
        assert get_dau_estimate() == 500

    def test_ip_timestamp_update(self):
        """Re-tracking an IP updates its timestamp."""
        old_time = time.time() - 100
        with _dau_lock:
            _ip_timestamps["192.168.1.1"] = old_time

        track_request_ip("192.168.1.1")

        with _dau_lock:
            assert _ip_timestamps["192.168.1.1"] > old_time


# =============================================================================
# Usage Tracking Middleware
# =============================================================================


class TestUsageTrackingMiddleware:
    """Tests for the UsageTrackingMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_tracks_endpoint(self):
        """Middleware records endpoint path."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/route"
        mock_request.client.host = "10.0.0.1"

        mock_response = MagicMock()
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        endpoints = get_top_endpoints(10)
        assert any(e["endpoint"] == "/api/v1/route" for e in endpoints)

    @pytest.mark.asyncio
    async def test_middleware_tracks_ip(self):
        """Middleware records client IP for DAU."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/route"
        mock_request.client.host = "203.0.113.42"

        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, call_next)

        assert get_dau_estimate() >= 1

    @pytest.mark.asyncio
    async def test_middleware_skips_health(self):
        """Health endpoint is not tracked."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/health"
        mock_request.client.host = "10.0.0.1"

        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, call_next)

        # Should not be tracked
        endpoints = get_top_endpoints(10)
        assert not any(e["endpoint"] == "/health" for e in endpoints)
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_skips_docs(self):
        """Docs endpoints are not tracked."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        for path in ["/docs", "/redoc", "/openapi.json", "/metrics"]:
            mock_request = MagicMock()
            mock_request.url.path = path
            mock_request.client.host = "10.0.0.1"
            call_next = AsyncMock(return_value=MagicMock())
            await middleware.dispatch(mock_request, call_next)

        endpoints = get_top_endpoints(10)
        assert endpoints == []

    @pytest.mark.asyncio
    async def test_middleware_detects_map_feature(self):
        """Map URL pattern triggers map_views feature tracking."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/map/config"
        mock_request.client.host = "10.0.0.1"

        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, call_next)

        usage = get_feature_usage()
        assert usage.get("map_views", 0) >= 1

    @pytest.mark.asyncio
    async def test_middleware_detects_route_feature(self):
        """Route URL pattern triggers route_calculations feature tracking."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/route/calculate"
        mock_request.client.host = "10.0.0.1"

        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, call_next)

        usage = get_feature_usage()
        assert usage.get("route_calculations", 0) >= 1

    @pytest.mark.asyncio
    async def test_middleware_detects_intel_feature(self):
        """Intel URL pattern triggers intel_lookups feature tracking."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/intel/pilot/12345"
        mock_request.client.host = "10.0.0.1"

        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, call_next)

        usage = get_feature_usage()
        assert usage.get("intel_lookups", 0) >= 1

    @pytest.mark.asyncio
    async def test_middleware_no_client(self):
        """Missing client (e.g. internal request) uses 'unknown' IP."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/route"
        mock_request.client = None

        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, call_next)

        # Should not crash; IP tracked as "unknown"
        assert get_dau_estimate() >= 1

    @pytest.mark.asyncio
    async def test_middleware_calls_next(self):
        """Middleware always calls call_next to pass to the next handler."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/route"
        mock_request.client.host = "10.0.0.1"

        call_next = AsyncMock(return_value=MagicMock())

        await middleware.dispatch(mock_request, call_next)

        call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_middleware_returns_response(self):
        """Middleware returns the response from call_next."""
        middleware = UsageTrackingMiddleware(app=MagicMock())

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/route"
        mock_request.client.host = "10.0.0.1"

        expected_response = MagicMock()
        call_next = AsyncMock(return_value=expected_response)

        result = await middleware.dispatch(mock_request, call_next)

        assert result is expected_response


# =============================================================================
# Feature Pattern Configuration
# =============================================================================


class TestFeaturePatterns:
    """Tests for the feature pattern mapping configuration."""

    def test_feature_patterns_exist(self):
        assert len(_FEATURE_PATTERNS) >= 4

    def test_map_pattern(self):
        patterns = dict(_FEATURE_PATTERNS)
        assert patterns.get("/api/v1/map/") == "map_views"

    def test_route_pattern(self):
        patterns = dict(_FEATURE_PATTERNS)
        assert patterns.get("/api/v1/route") == "route_calculations"

    def test_intel_pattern(self):
        patterns = dict(_FEATURE_PATTERNS)
        assert patterns.get("/api/v1/intel/") == "intel_lookups"

    def test_killfeed_pattern(self):
        patterns = dict(_FEATURE_PATTERNS)
        assert patterns.get("/ws/killfeed") == "kill_feed_connections"
