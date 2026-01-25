"""Unit tests for rate limiting middleware."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from backend.app.middleware.rate_limit import (
    get_request_identifier,
    limiter,
    rate_limit_exceeded_handler,
)


class TestGetRequestIdentifier:
    """Tests for request identifier function."""

    def test_returns_ip_address_by_default(self):
        """Test that IP address is used when no API key."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.100"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.API_KEY_ENABLED = False

            result = get_request_identifier(mock_request)
            # Should return IP address
            assert "192.168.1.100" in result or result == "testclient"

    def test_returns_api_key_when_enabled(self):
        """Test that API key is used when present and enabled."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-api-key-123"}
        mock_request.client.host = "192.168.1.100"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.API_KEY_ENABLED = True

            result = get_request_identifier(mock_request)
            assert result == "apikey:test-api-key-123"

    def test_returns_ip_when_api_key_disabled(self):
        """Test that IP is used when API key present but disabled."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-api-key-123"}
        mock_request.client.host = "192.168.1.100"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.API_KEY_ENABLED = False

            result = get_request_identifier(mock_request)
            # Should not use API key
            assert not result.startswith("apikey:")


class TestRateLimitExceededHandler:
    """Tests for rate limit exceeded error handler."""

    def test_returns_429_status(self):
        """Test that handler returns 429 status code."""
        mock_request = MagicMock(spec=Request)
        mock_exc = MagicMock()
        mock_exc.detail = "100 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert response.status_code == 429

    def test_response_is_json(self):
        """Test that response is JSON formatted."""
        mock_request = MagicMock(spec=Request)
        mock_exc = MagicMock()
        mock_exc.detail = "100 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert response.media_type == "application/json"
            assert b"Rate limit exceeded" in response.body

    def test_includes_rate_limit_headers(self):
        """Test that response includes rate limit headers."""
        mock_request = MagicMock(spec=Request)
        mock_exc = MagicMock()
        mock_exc.detail = "100 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "Retry-After" in response.headers


class TestLimiterConfiguration:
    """Tests for limiter configuration."""

    def test_limiter_exists(self):
        """Test that limiter is configured."""
        assert limiter is not None

    def test_limiter_has_headers_enabled(self):
        """Test that limiter headers are enabled."""
        # The limiter should have been created with headers_enabled=True
        assert limiter._headers_enabled is True
