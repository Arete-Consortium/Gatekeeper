"""Tests for configuration module."""

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


class TestSettingsDefaults:
    """Tests for Settings default values."""

    def test_default_api_version(self):
        """Should have default API version."""
        settings = Settings()
        assert settings.API_VERSION is not None

    def test_default_cache_ttl(self):
        """Should have default cache TTL values."""
        settings = Settings()
        assert settings.CACHE_TTL_RISK > 0
        assert settings.CACHE_TTL_ROUTE > 0


class TestDatabaseUrl:
    """Tests for database_url property."""

    def test_database_url_property_exists(self):
        """Should have database_url property."""
        settings = Settings()
        # Just verify the property exists and returns a string
        assert isinstance(settings.database_url, str)
