"""Unit tests for status API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from backend.app.api.v1.status import (
    format_uptime,
    get_status,
    set_start_time,
)


class TestFormatUptime:
    """Tests for format_uptime function."""

    def test_format_seconds_only(self):
        """Test formatting seconds only."""
        result = format_uptime(45)
        assert result == "45s"

    def test_format_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        result = format_uptime(125)  # 2m 5s
        assert result == "2m 5s"

    def test_format_hours_minutes_seconds(self):
        """Test formatting hours, minutes, and seconds."""
        result = format_uptime(3725)  # 1h 2m 5s
        assert result == "1h 2m 5s"

    def test_format_days_hours_minutes_seconds(self):
        """Test formatting days, hours, minutes, and seconds."""
        result = format_uptime(90125)  # 1d 1h 2m 5s
        assert result == "1d 1h 2m 5s"

    def test_format_only_days(self):
        """Test formatting when only days are significant."""
        result = format_uptime(86400)  # Exactly 1 day
        assert result == "1d 0s"

    def test_format_multiple_days(self):
        """Test formatting multiple days."""
        result = format_uptime(259200)  # 3 days
        assert result == "3d 0s"

    def test_format_zero_seconds(self):
        """Test formatting zero seconds."""
        result = format_uptime(0)
        assert result == "0s"


class TestSetStartTime:
    """Tests for set_start_time function."""

    def test_set_start_time(self):
        """Test setting the start time."""
        import backend.app.api.v1.status as status_module

        new_time = datetime.now(UTC) - timedelta(hours=1)
        set_start_time(new_time)

        assert status_module._start_time == new_time


class TestGetStatus:
    """Tests for get_status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_success(self):
        """Test successful status response."""
        with patch("backend.app.api.v1.status.settings") as mock_settings:
            mock_settings.API_VERSION = "1.0.0"
            mock_settings.PROJECT_NAME = "EVE Gatekeeper"
            mock_settings.DEBUG = False
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.REDIS_URL = None
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.API_KEY_ENABLED = False
            mock_settings.METRICS_ENABLED = True

            with patch("backend.app.services.data_loader.load_universe") as mock_universe:
                mock_universe.return_value.systems = {"Jita": {}, "Amarr": {}}

                result = await get_status()

        assert result["status"] == "operational"
        assert result["version"] == "1.0.0"
        assert result["checks"]["database"] == "ok"
        assert result["checks"]["cache"] == "memory"
        assert result["checks"]["systems_loaded"] == 2

    @pytest.mark.asyncio
    async def test_get_status_database_error(self):
        """Test status when database/universe loading fails."""
        with patch("backend.app.api.v1.status.settings") as mock_settings:
            mock_settings.API_VERSION = "1.0.0"
            mock_settings.PROJECT_NAME = "Test"
            mock_settings.DEBUG = False
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.REDIS_URL = None
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.API_KEY_ENABLED = False
            mock_settings.METRICS_ENABLED = False

            with patch(
                "backend.app.services.data_loader.load_universe",
                side_effect=Exception("Database error"),
            ):
                result = await get_status()

        assert result["checks"]["database"] == "error"
        assert result["checks"]["systems_loaded"] == 0

    @pytest.mark.asyncio
    async def test_get_status_redis_configured(self):
        """Test status when Redis is configured."""
        with patch("backend.app.api.v1.status.settings") as mock_settings:
            mock_settings.API_VERSION = "1.0.0"
            mock_settings.PROJECT_NAME = "Test"
            mock_settings.DEBUG = False
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.REDIS_URL = "redis://localhost:6379"
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.API_KEY_ENABLED = False
            mock_settings.METRICS_ENABLED = False

            with patch("backend.app.services.data_loader.load_universe") as mock_universe:
                mock_universe.return_value.systems = {}

                result = await get_status()

        assert result["checks"]["cache"] == "redis_configured"

    @pytest.mark.asyncio
    async def test_get_status_uptime_formatted(self):
        """Test that uptime is properly formatted."""
        import backend.app.api.v1.status as status_module

        # Set start time to 1 hour ago
        status_module._start_time = datetime.now(UTC) - timedelta(hours=1, minutes=5)

        with patch("backend.app.api.v1.status.settings") as mock_settings:
            mock_settings.API_VERSION = "1.0.0"
            mock_settings.PROJECT_NAME = "Test"
            mock_settings.DEBUG = False
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.REDIS_URL = None
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.API_KEY_ENABLED = False
            mock_settings.METRICS_ENABLED = False

            with patch("backend.app.services.data_loader.load_universe") as mock_universe:
                mock_universe.return_value.systems = {}

                result = await get_status()

        assert "uptime_formatted" in result
        assert "1h" in result["uptime_formatted"]
        assert "5m" in result["uptime_formatted"]
