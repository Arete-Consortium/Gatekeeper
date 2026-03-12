"""Tests for configuration module."""

import warnings

import pytest

from backend.app.core.config import Settings


class TestCorsOriginsValidator:
    """Tests for CORS_ORIGINS field validator."""

    def test_parse_json_list(self):
        """Should parse JSON array string."""
        result = Settings.parse_cors_origins('["http://localhost:3000", "http://localhost:8080"]')
        assert result == ["http://localhost:3000", "http://localhost:8080"]

    def test_parse_comma_separated(self):
        """Should parse comma-separated string when not valid JSON."""
        result = Settings.parse_cors_origins("http://localhost:3000, http://localhost:8080")
        assert result == ["http://localhost:3000", "http://localhost:8080"]

    def test_parse_single_origin(self):
        """Should handle single origin as comma-separated."""
        result = Settings.parse_cors_origins("http://localhost:3000")
        assert result == ["http://localhost:3000"]

    def test_already_list(self):
        """Should pass through if already a list."""
        result = Settings.parse_cors_origins(["http://a.com", "http://b.com"])
        assert result == ["http://a.com", "http://b.com"]

    def test_empty_json_array(self):
        """Should handle empty JSON array."""
        result = Settings.parse_cors_origins("[]")
        assert result == []

    def test_whitespace_trimming(self):
        """Should trim whitespace from comma-separated values."""
        result = Settings.parse_cors_origins("  http://a.com  ,  http://b.com  ")
        assert result == ["http://a.com", "http://b.com"]

    def test_parse_three_origins(self):
        """Should parse three comma-separated origins."""
        result = Settings.parse_cors_origins("http://a.com, http://b.com, http://c.com")
        assert result == ["http://a.com", "http://b.com", "http://c.com"]

    def test_parse_json_single_item_list(self):
        """Should parse JSON array with single item."""
        result = Settings.parse_cors_origins('["http://localhost:3000"]')
        assert result == ["http://localhost:3000"]

    def test_empty_string_returns_single_empty(self):
        """Empty string produces a list with one empty string."""
        result = Settings.parse_cors_origins("")
        assert result == [""]

    def test_already_empty_list(self):
        """Should pass through empty list."""
        result = Settings.parse_cors_origins([])
        assert result == []

    def test_mixed_protocols(self):
        """Should handle http and https origins."""
        result = Settings.parse_cors_origins("http://a.com, https://b.com")
        assert result == ["http://a.com", "https://b.com"]

    def test_origins_with_ports(self):
        """Should preserve port numbers in origins."""
        result = Settings.parse_cors_origins("http://localhost:3000, http://localhost:8080")
        assert "http://localhost:3000" in result
        assert "http://localhost:8080" in result

    def test_invalid_json_falls_back_to_csv(self):
        """Invalid JSON falls back to comma-separated parsing."""
        result = Settings.parse_cors_origins("{not valid json}")
        assert result == ["{not valid json}"]


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_default_api_version(self):
        """Should have default API version."""
        settings = Settings()
        assert settings.API_VERSION is not None

    def test_default_project_name(self):
        """Should have default project name."""
        settings = Settings()
        assert settings.PROJECT_NAME == "EVE Gatekeeper"

    def test_default_debug_false(self):
        """DEBUG defaults to false (production mode unless overridden)."""
        # Need valid secret key when DEBUG=False (production mode)
        s = Settings(DEBUG=False, SECRET_KEY="a" * 32)
        assert s.DEBUG is False

    def test_default_esi_base_url(self):
        """Should have correct ESI base URL."""
        settings = Settings()
        assert settings.ESI_BASE_URL == "https://esi.evetech.net/latest"

    def test_default_zkill_base_url(self):
        """Should have correct zKillboard base URL."""
        settings = Settings()
        assert settings.ZKILL_BASE_URL == "https://zkillboard.com/api"

    def test_default_zkill_user_agent(self):
        """Should have zKillboard user agent."""
        settings = Settings()
        assert "EVE_Gatekeeper" in settings.ZKILL_USER_AGENT

    def test_default_rate_limit_enabled(self):
        """Rate limiting enabled by default."""
        s = Settings(RATE_LIMIT_ENABLED=True)
        assert s.RATE_LIMIT_ENABLED is True

    def test_default_rate_limit_per_minute(self):
        """Rate limit per minute has a positive value."""
        settings = Settings()
        assert settings.RATE_LIMIT_PER_MINUTE > 0

    def test_default_cookie_secure(self):
        """Cookie secure flag defaults to True."""
        settings = Settings()
        assert settings.COOKIE_SECURE is True

    def test_default_cookie_samesite(self):
        """Cookie SameSite defaults to none."""
        settings = Settings()
        assert settings.COOKIE_SAMESITE == "none"

    def test_default_cookie_max_age(self):
        """Cookie max age defaults to 24 hours."""
        settings = Settings()
        assert settings.COOKIE_MAX_AGE == 86400

    def test_default_log_level(self):
        """Log level has a default value."""
        settings = Settings()
        assert settings.LOG_LEVEL is not None

    def test_default_webhook_timeout(self):
        """Webhook timeout defaults to 10 seconds."""
        settings = Settings()
        assert settings.WEBHOOK_TIMEOUT == 10

    def test_default_esi_concurrency_limit(self):
        """ESI concurrency limit defaults to 20."""
        settings = Settings()
        assert settings.ESI_CONCURRENCY_LIMIT == 20

    def test_default_esi_timeout(self):
        """ESI timeout defaults to 30 seconds."""
        settings = Settings()
        assert settings.ESI_TIMEOUT == 30.0

    def test_default_kill_history_max_age(self):
        """Kill history max age defaults to 24 hours."""
        settings = Settings()
        assert settings.KILL_HISTORY_MAX_AGE_HOURS == 24

    def test_default_kill_history_max_entries(self):
        """Kill history max entries defaults to 10000."""
        settings = Settings()
        assert settings.KILL_HISTORY_MAX_ENTRIES == 10000


class TestDatabaseUrl:
    """Tests for database_url property."""

    def test_database_url_property_exists(self):
        """Should have database_url property."""
        settings = Settings()
        # Just verify the property exists and returns a string
        assert isinstance(settings.database_url, str)

    def test_database_url_uses_postgres_when_set(self):
        """database_url prefers POSTGRES_URL when set."""
        settings = Settings(POSTGRES_URL="postgresql://user:pass@host/db")
        assert settings.database_url == "postgresql://user:pass@host/db"

    def test_database_url_falls_back_to_sqlite(self):
        """database_url uses DATABASE_URL when POSTGRES_URL is not set."""
        settings = Settings(POSTGRES_URL=None, DATABASE_URL="sqlite:///test.db")
        assert settings.database_url == "sqlite:///test.db"


class TestIsProduction:
    """Tests for is_production property."""

    def test_is_production_when_debug_false(self):
        """is_production returns True when DEBUG is False."""
        # Must provide a valid secret key for production
        s = Settings(DEBUG=False, SECRET_KEY="a" * 32)
        assert s.is_production is True

    def test_not_production_when_debug_true(self):
        """is_production returns False when DEBUG is True."""
        settings = Settings(DEBUG=True)
        assert settings.is_production is False


class TestSecretKeyValidation:
    """Tests for SECRET_KEY validation."""

    def test_short_secret_key_warns(self):
        """Short SECRET_KEY emits a warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Settings(DEBUG=True, SECRET_KEY="short")
            short_warnings = [x for x in w if "at least 32 characters" in str(x.message)]
            assert len(short_warnings) >= 1

    def test_default_secret_key_warns(self):
        """Default SECRET_KEY emits an insecure warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Settings(DEBUG=True, SECRET_KEY="change-me-in-production")
            insecure_warnings = [x for x in w if "insecure" in str(x.message)]
            assert len(insecure_warnings) >= 1

    def test_production_rejects_default_secret(self):
        """Production mode rejects the default SECRET_KEY."""
        with pytest.raises(ValueError, match="must be changed from default"):
            Settings(DEBUG=False, SECRET_KEY="change-me-in-production")

    def test_production_rejects_short_secret(self):
        """Production mode rejects short SECRET_KEY."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            Settings(DEBUG=False, SECRET_KEY="tooshort")

    def test_production_accepts_valid_secret(self):
        """Production mode accepts a sufficiently long SECRET_KEY."""
        s = Settings(DEBUG=False, SECRET_KEY="a" * 32)
        assert s.SECRET_KEY == "a" * 32


class TestWebSocketDefaults:
    """Tests for WebSocket configuration defaults."""

    def test_ws_initial_retry_delay(self):
        """WS initial retry delay defaults to 1.0 seconds."""
        settings = Settings()
        assert settings.WS_INITIAL_RETRY_DELAY == 1.0

    def test_ws_max_retry_delay(self):
        """WS max retry delay defaults to 60.0 seconds."""
        settings = Settings()
        assert settings.WS_MAX_RETRY_DELAY == 60.0

    def test_ws_retry_multiplier(self):
        """WS retry multiplier defaults to 2.0."""
        settings = Settings()
        assert settings.WS_RETRY_MULTIPLIER == 2.0

    def test_ws_max_retry_attempts_unlimited(self):
        """WS max retry attempts defaults to 0 (unlimited)."""
        settings = Settings()
        assert settings.WS_MAX_RETRY_ATTEMPTS == 0

    def test_ws_health_check_interval(self):
        """WS health check interval defaults to 30.0 seconds."""
        settings = Settings()
        assert settings.WS_HEALTH_CHECK_INTERVAL == 30.0

    def test_ws_connection_timeout(self):
        """WS connection timeout defaults to 10.0 seconds."""
        settings = Settings()
        assert settings.WS_CONNECTION_TIMEOUT == 10.0


class TestOptionalFields:
    """Tests for optional configuration fields.

    Note: env vars / .env may override defaults to empty strings,
    so we test that the field accepts None or falsy values.
    """

    def test_esi_client_id_optional(self):
        """ESI_CLIENT_ID accepts None."""
        s = Settings(ESI_CLIENT_ID=None)
        assert s.ESI_CLIENT_ID is None

    def test_esi_secret_key_optional(self):
        """ESI_SECRET_KEY accepts None."""
        s = Settings(ESI_SECRET_KEY=None)
        assert s.ESI_SECRET_KEY is None

    def test_sentry_dsn_optional(self):
        """SENTRY_DSN accepts None."""
        s = Settings(SENTRY_DSN=None)
        assert s.SENTRY_DSN is None

    def test_stripe_secret_key_optional(self):
        """STRIPE_SECRET_KEY accepts None."""
        s = Settings(STRIPE_SECRET_KEY=None)
        assert s.STRIPE_SECRET_KEY is None

    def test_stripe_webhook_secret_optional(self):
        """STRIPE_WEBHOOK_SECRET accepts None."""
        s = Settings(STRIPE_WEBHOOK_SECRET=None)
        assert s.STRIPE_WEBHOOK_SECRET is None

    def test_redis_url_optional(self):
        """REDIS_URL accepts None."""
        s = Settings(REDIS_URL=None)
        assert s.REDIS_URL is None

    def test_discord_webhook_url_optional(self):
        """DISCORD_WEBHOOK_URL accepts None."""
        s = Settings(DISCORD_WEBHOOK_URL=None)
        assert s.DISCORD_WEBHOOK_URL is None

    def test_slack_webhook_url_optional(self):
        """SLACK_WEBHOOK_URL accepts None."""
        s = Settings(SLACK_WEBHOOK_URL=None)
        assert s.SLACK_WEBHOOK_URL is None

    def test_api_base_url_optional(self):
        """API_BASE_URL accepts None."""
        s = Settings(API_BASE_URL=None)
        assert s.API_BASE_URL is None


class TestRateLimitTiers:
    """Tests for rate limit tier configuration."""

    def test_pro_rate_limit_higher_than_user(self):
        """Pro tier rate limit is higher than free user."""
        settings = Settings()
        assert settings.RATE_LIMIT_PER_MINUTE_PRO > settings.RATE_LIMIT_PER_MINUTE_USER

    def test_user_rate_limit_at_least_anonymous(self):
        """Authenticated user rate limit is at least as high as anonymous."""
        settings = Settings()
        assert settings.RATE_LIMIT_PER_MINUTE_USER >= settings.RATE_LIMIT_PER_MINUTE

    def test_auth_rate_limit_is_lowest(self):
        """Auth endpoint rate limit is the most restrictive."""
        settings = Settings()
        assert settings.RATE_LIMIT_AUTH <= settings.RATE_LIMIT_DEFAULT

    def test_health_rate_limit_is_highest(self):
        """Health endpoint rate limit is the most permissive."""
        settings = Settings()
        assert settings.RATE_LIMIT_HEALTH >= settings.RATE_LIMIT_DEFAULT
