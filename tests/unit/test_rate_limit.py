"""Unit tests for rate limiting middleware."""

import json
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Request

from backend.app.middleware.rate_limit import (
    extract_character_from_request,
    get_rate_limit_for_identifier,
    get_request_identifier,
    limiter,
    rate_limit_exceeded_handler,
    setup_rate_limiting,
)


class TestExtractCharacterIdFromRequest:
    """Tests for extracting character_id from requests."""

    def test_extracts_from_valid_bearer_token(self):
        """Test extraction from valid JWT Bearer token."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        mock_request.query_params = {}

        mock_payload = MagicMock()
        mock_payload.sub = 12345678

        with patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate:
            mock_validate.return_value = (mock_payload, None)

            result = extract_character_from_request(mock_request)

            assert result[0] == 12345678
            mock_validate.assert_called_once_with("valid-token", verify_fingerprint=None)

    def test_extracts_from_query_param(self):
        """Test extraction from character_id query parameter."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {"character_id": "98765432"}

        result = extract_character_from_request(mock_request)

        assert result[0] == 98765432

    def test_returns_none_for_invalid_bearer_token(self):
        """Test returns None when Bearer token is invalid."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer invalid-token"}
        mock_request.query_params = {}

        with patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate:
            mock_validate.return_value = (None, "Invalid token")

            result = extract_character_from_request(mock_request)

            assert result[0] is None

    def test_returns_none_for_invalid_query_param(self):
        """Test returns None when character_id query param is not a number."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {"character_id": "not-a-number"}

        result = extract_character_from_request(mock_request)

        assert result[0] is None

    def test_returns_none_for_no_auth(self):
        """Test returns None when no authentication is present."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {}

        result = extract_character_from_request(mock_request)

        assert result[0] is None

    def test_prefers_bearer_token_over_query_param(self):
        """Test that Bearer token takes precedence over query param."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        mock_request.query_params = {"character_id": "11111111"}

        mock_payload = MagicMock()
        mock_payload.sub = 22222222
        mock_payload.tier = "free"

        with patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate:
            mock_validate.return_value = (mock_payload, None)

            result = extract_character_from_request(mock_request)

            # Should use Bearer token's character_id, not query param
            assert result[0] == 22222222

    def test_falls_back_to_query_when_bearer_invalid(self):
        """Test falls back to query param when Bearer token is invalid."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer invalid"}
        mock_request.query_params = {"character_id": "33333333"}

        with patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate:
            mock_validate.return_value = (None, "Invalid")

            result = extract_character_from_request(mock_request)

            assert result[0] == 33333333

    def test_handles_bearer_prefix_case_insensitive(self):
        """Test that 'bearer' prefix is case-insensitive."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "BEARER token"}
        mock_request.query_params = {}

        mock_payload = MagicMock()
        mock_payload.sub = 44444444
        mock_payload.tier = "free"

        with patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate:
            mock_validate.return_value = (mock_payload, None)

            result = extract_character_from_request(mock_request)

            assert result[0] == 44444444


class TestGetRequestIdentifier:
    """Tests for request identifier function."""

    def test_returns_user_id_for_authenticated_request(self):
        """Test that user ID is used for authenticated requests."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"

        mock_payload = MagicMock()
        mock_payload.sub = 12345678
        mock_payload.tier = "free"

        with (
            patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate,
            patch("backend.app.middleware.rate_limit.settings") as mock_settings,
        ):
            mock_validate.return_value = (mock_payload, None)
            mock_settings.API_KEY_ENABLED = False

            result = get_request_identifier(mock_request)

            assert result == "user:12345678"

    def test_returns_ip_address_by_default(self):
        """Test that IP address is used when no authentication."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.API_KEY_ENABLED = False

            result = get_request_identifier(mock_request)

            # Should return IP address with prefix
            assert result.startswith("ip:")
            assert "192.168.1.100" in result or "testclient" in result

    def test_returns_api_key_when_enabled(self):
        """Test that API key is used when present and enabled."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-api-key-123"}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.API_KEY_ENABLED = True

            result = get_request_identifier(mock_request)

            assert result == "apikey:test-api-key-123"

    def test_returns_ip_when_api_key_disabled(self):
        """Test that IP is used when API key present but disabled."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-api-key-123"}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.API_KEY_ENABLED = False

            result = get_request_identifier(mock_request)

            # Should not use API key
            assert not result.startswith("apikey:")
            assert result.startswith("ip:")

    def test_user_takes_precedence_over_api_key(self):
        """Test that authenticated user ID takes precedence over API key."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "Authorization": "Bearer valid-token",
            "X-API-Key": "test-api-key",
        }
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"

        mock_payload = MagicMock()
        mock_payload.sub = 55555555
        mock_payload.tier = "free"

        with (
            patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate,
            patch("backend.app.middleware.rate_limit.settings") as mock_settings,
        ):
            mock_validate.return_value = (mock_payload, None)
            mock_settings.API_KEY_ENABLED = True

            result = get_request_identifier(mock_request)

            # Should use user ID, not API key
            assert result == "user:55555555"


class TestGetRateLimitForIdentifier:
    """Tests for getting rate limit based on identifier type."""

    def test_returns_user_limit_for_authenticated(self):
        """Test returns user limit for user: identifiers."""
        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 200

            result = get_rate_limit_for_identifier("user:12345678")

            assert result == "200/minute"

    def test_returns_apikey_limit_for_api_keys(self):
        """Test returns API key limit for apikey: identifiers."""
        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE_APIKEY = 300

            result = get_rate_limit_for_identifier("apikey:test-key")

            assert result == "300/minute"

    def test_returns_default_limit_for_ip(self):
        """Test returns default limit for IP-based identifiers."""
        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100

            result = get_rate_limit_for_identifier("ip:192.168.1.100")

            assert result == "100/minute"

    def test_returns_default_limit_for_unknown_prefix(self):
        """Test returns default limit for unknown identifier types."""
        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100

            result = get_rate_limit_for_identifier("unknown:something")

            assert result == "100/minute"


class TestRateLimitExceededHandler:
    """Tests for rate limit exceeded error handler."""

    def test_returns_429_status(self):
        """Test that handler returns 429 status code."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"
        mock_request.url.path = "/api/v1/some-endpoint"
        mock_request.method = "GET"
        mock_exc = MagicMock()
        mock_exc.detail = "100 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 200
            mock_settings.RATE_LIMIT_PER_MINUTE_PRO = 300
            mock_settings.RATE_LIMIT_PER_MINUTE_APIKEY = 300
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_MAP = 30
            mock_settings.RATE_LIMIT_ROUTE = 20
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = False

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert response.status_code == 429

    def test_response_is_json(self):
        """Test that response is JSON formatted."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"
        mock_request.url.path = "/api/v1/some-endpoint"
        mock_request.method = "GET"
        mock_exc = MagicMock()
        mock_exc.detail = "100 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 200
            mock_settings.RATE_LIMIT_PER_MINUTE_PRO = 300
            mock_settings.RATE_LIMIT_PER_MINUTE_APIKEY = 300
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_MAP = 30
            mock_settings.RATE_LIMIT_ROUTE = 20
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = False

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert response.media_type == "application/json"
            assert b"Rate limit exceeded" in response.body

    def test_includes_rate_limit_headers(self):
        """Test that response includes rate limit headers."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"
        mock_request.url.path = "/api/v1/some-endpoint"
        mock_request.method = "GET"
        mock_exc = MagicMock()
        mock_exc.detail = "100 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 200
            mock_settings.RATE_LIMIT_PER_MINUTE_PRO = 300
            mock_settings.RATE_LIMIT_PER_MINUTE_APIKEY = 300
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_MAP = 30
            mock_settings.RATE_LIMIT_ROUTE = 20
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = False

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "Retry-After" in response.headers
            assert "X-RateLimit-User-Type" in response.headers

    def test_includes_user_type_in_response_for_anonymous(self):
        """Test that response includes user_type for anonymous requests."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"
        mock_request.url.path = "/api/v1/some-endpoint"
        mock_request.method = "GET"
        mock_exc = MagicMock()
        mock_exc.detail = "100 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 200
            mock_settings.RATE_LIMIT_PER_MINUTE_PRO = 300
            mock_settings.RATE_LIMIT_PER_MINUTE_APIKEY = 300
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_MAP = 30
            mock_settings.RATE_LIMIT_ROUTE = 20
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = False

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            body = json.loads(response.body)
            assert body["user_type"] == "anonymous"
            assert response.headers["X-RateLimit-User-Type"] == "anonymous"
            # Endpoint limit (60) is lower than per-identifier limit (100)
            assert response.headers["X-RateLimit-Limit"] == "60"

    def test_includes_user_type_in_response_for_authenticated(self):
        """Test that response includes user_type for authenticated requests."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid-token"}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"
        mock_request.url.path = "/api/v1/some-endpoint"
        mock_request.method = "GET"
        mock_exc = MagicMock()
        mock_exc.detail = "200 per 1 minute"

        mock_payload = MagicMock()
        mock_payload.sub = 12345678
        mock_payload.tier = "free"

        with (
            patch("backend.app.middleware.rate_limit.validate_jwt") as mock_validate,
            patch("backend.app.middleware.rate_limit.settings") as mock_settings,
        ):
            mock_validate.return_value = (mock_payload, None)
            mock_settings.RATE_LIMIT_PER_MINUTE = 100
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 200
            mock_settings.RATE_LIMIT_PER_MINUTE_PRO = 300
            mock_settings.RATE_LIMIT_PER_MINUTE_APIKEY = 300
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_MAP = 30
            mock_settings.RATE_LIMIT_ROUTE = 20
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = False

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            body = json.loads(response.body)
            assert body["user_type"] == "authenticated"
            assert response.headers["X-RateLimit-User-Type"] == "authenticated"
            # Endpoint limit (60) is lower than per-user limit (200)
            assert response.headers["X-RateLimit-Limit"] == "60"

    def test_includes_user_type_in_response_for_api_key(self):
        """Test that response includes user_type for API key requests."""
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-API-Key": "test-api-key"}
        mock_request.query_params = {}
        mock_request.client.host = "192.168.1.100"
        mock_request.url.path = "/api/v1/some-endpoint"
        mock_request.method = "GET"
        mock_exc = MagicMock()
        mock_exc.detail = "300 per 1 minute"

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_PER_MINUTE = 100
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 200
            mock_settings.RATE_LIMIT_PER_MINUTE_PRO = 300
            mock_settings.RATE_LIMIT_PER_MINUTE_APIKEY = 300
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_MAP = 30
            mock_settings.RATE_LIMIT_ROUTE = 20
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = True

            response = rate_limit_exceeded_handler(mock_request, mock_exc)

            body = json.loads(response.body)
            assert body["user_type"] == "api_key"
            assert response.headers["X-RateLimit-User-Type"] == "api_key"
            # Endpoint limit (60) is lower than per-apikey limit (300)
            assert response.headers["X-RateLimit-Limit"] == "60"


class TestLimiterConfiguration:
    """Tests for limiter configuration."""

    def test_limiter_exists(self):
        """Test that limiter is configured."""
        assert limiter is not None

    def test_limiter_has_headers_enabled(self):
        """Test that limiter headers are enabled."""
        # The limiter should have been created with headers_enabled=True
        assert limiter._headers_enabled is True


class TestSetupRateLimiting:
    """Tests for setup_rate_limiting function."""

    def test_setup_when_disabled(self):
        """Test that setup does nothing when rate limiting is disabled."""
        app = FastAPI()

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = False

            setup_rate_limiting(app)

            # Should not have limiter in state
            assert not hasattr(app.state, "limiter")

    def test_setup_when_enabled(self):
        """Test that setup configures app when rate limiting is enabled."""
        app = FastAPI()

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True

            setup_rate_limiting(app)

            # Should have limiter in state
            assert hasattr(app.state, "limiter")
            assert app.state.limiter is limiter
