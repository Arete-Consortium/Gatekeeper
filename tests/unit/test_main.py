"""Unit tests for main.py health check edge cases."""

from unittest.mock import MagicMock, patch

import pytest


class TestHealthCheck:
    """Test health check endpoint edge cases."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        mock = MagicMock()
        mock.API_VERSION = "1.0.0"
        mock.REDIS_URL = None
        return mock

    @pytest.mark.asyncio
    async def test_health_check_database_warning_empty_systems(self, mock_settings):
        """Test health check returns degraded when universe.systems is empty."""
        from backend.app.main import health_check

        mock_universe = MagicMock()
        mock_universe.systems = {}  # Empty systems

        with (
            patch("backend.app.main.settings", mock_settings),
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
        ):
            result = await health_check()

        assert result["status"] == "degraded"
        assert result["checks"]["database"] == "warning"

    @pytest.mark.asyncio
    async def test_health_check_database_error_exception(self, mock_settings):
        """Test health check returns unhealthy when load_universe raises."""
        from backend.app.main import health_check

        with (
            patch("backend.app.main.settings", mock_settings),
            patch(
                "backend.app.services.data_loader.load_universe",
                side_effect=Exception("DB error"),
            ),
        ):
            result = await health_check()

        assert result["status"] == "unhealthy"
        assert result["checks"]["database"] == "error"

    @pytest.mark.asyncio
    async def test_health_check_redis_cache(self, mock_settings):
        """Test health check detects redis cache when REDIS_URL is set."""
        from backend.app.main import health_check

        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_universe = MagicMock()
        mock_universe.systems = {"Jita": MagicMock()}

        mock_cache = MagicMock()
        mock_cache._redis = MagicMock()  # Has _redis attribute = redis cache

        with (
            patch("backend.app.main.settings", mock_settings),
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch("backend.app.services.cache.get_cache_sync", return_value=mock_cache),
        ):
            result = await health_check()

        assert result["status"] == "healthy"
        assert result["checks"]["cache"] == "redis"

    @pytest.mark.asyncio
    async def test_health_check_redis_fallback_memory(self, mock_settings):
        """Test health check falls back to memory when redis check fails."""
        from backend.app.main import health_check

        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_universe = MagicMock()
        mock_universe.systems = {"Jita": MagicMock()}

        # Cache without _redis attribute (memory cache)
        mock_cache = MagicMock(spec=[])  # No _redis

        with (
            patch("backend.app.main.settings", mock_settings),
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch("backend.app.services.cache.get_cache_sync", return_value=mock_cache),
        ):
            result = await health_check()

        assert result["checks"]["cache"] == "memory"

    @pytest.mark.asyncio
    async def test_health_check_redis_exception(self, mock_settings):
        """Test health check defaults to memory when get_cache_sync raises."""
        from backend.app.main import health_check

        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_universe = MagicMock()
        mock_universe.systems = {"Jita": MagicMock()}

        with (
            patch("backend.app.main.settings", mock_settings),
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch(
                "backend.app.services.cache.get_cache_sync",
                side_effect=Exception("Redis connection failed"),
            ),
        ):
            result = await health_check()

        assert result["checks"]["cache"] == "memory"

    @pytest.mark.asyncio
    async def test_health_check_response_structure(self, mock_settings):
        """Test health check response contains all required fields."""
        from backend.app.main import health_check

        mock_universe = MagicMock()
        mock_universe.systems = {"Jita": MagicMock()}

        with (
            patch("backend.app.main.settings", mock_settings),
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
        ):
            result = await health_check()

        # Verify structure
        assert "status" in result
        assert "version" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "checks" in result
        assert "database" in result["checks"]
        assert "cache" in result["checks"]
        assert "esi" in result["checks"]


class TestStartupShutdown:
    """Test startup and shutdown events."""

    @pytest.mark.asyncio
    async def test_startup_event(self):
        """Test startup event initializes correctly."""
        from unittest.mock import AsyncMock

        from backend.app.main import startup_event

        mock_listener = MagicMock()
        mock_listener.start = AsyncMock()

        with (
            patch("backend.app.main.set_start_time") as mock_set_time,
            patch(
                "backend.app.services.zkill_listener.get_zkill_listener",
                return_value=mock_listener,
            ),
        ):
            await startup_event()

        mock_set_time.assert_called_once()
        mock_listener.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test shutdown event cleans up correctly."""
        from unittest.mock import AsyncMock

        from backend.app.main import shutdown_event

        mock_listener = MagicMock()
        mock_listener.stop = AsyncMock()

        with (
            patch(
                "backend.app.services.zkill_listener.get_zkill_listener",
                return_value=mock_listener,
            ),
            patch("backend.app.db.database.close_db", new_callable=AsyncMock) as mock_close_db,
        ):
            await shutdown_event()

        mock_listener.stop.assert_called_once()
        mock_close_db.assert_called_once()
