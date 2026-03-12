"""Tests for Sentry initialization in create_app()."""

from unittest.mock import patch

import pytest

sentry_sdk = pytest.importorskip("sentry_sdk", reason="sentry_sdk not installed")


class TestSentryInit:
    """Verify Sentry SDK initialization behavior."""

    def test_sentry_not_initialized_when_dsn_empty(self):
        """Sentry should not initialize when SENTRY_DSN is None/empty."""
        with patch("backend.app.core.config.settings") as mock_settings:
            mock_settings.SENTRY_DSN = None
            mock_settings.PROJECT_NAME = "test"
            mock_settings.API_VERSION = "1.0.0"
            mock_settings.CORS_ORIGINS = []
            mock_settings.RATE_LIMIT_ENABLED = False

            with patch("sentry_sdk.init") as mock_init:
                from backend.app.main import create_app

                with patch("backend.app.main.settings", mock_settings):
                    create_app()

                mock_init.assert_not_called()

    def test_sentry_initialized_when_dsn_set(self):
        """Sentry should initialize when SENTRY_DSN is configured."""
        with patch("backend.app.main.settings") as mock_settings:
            mock_settings.SENTRY_DSN = "https://examplePublicKey@o0.ingest.sentry.io/0"
            mock_settings.is_production = True
            mock_settings.API_VERSION = "1.0.0"
            mock_settings.PROJECT_NAME = "test"
            mock_settings.CORS_ORIGINS = []
            mock_settings.RATE_LIMIT_ENABLED = False

            with patch("sentry_sdk.init") as mock_init:
                from backend.app.main import create_app

                create_app()

                mock_init.assert_called_once()
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"
                assert call_kwargs["environment"] == "production"
                assert call_kwargs["traces_sample_rate"] == 0.1
