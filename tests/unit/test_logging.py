"""Unit tests for logging configuration."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.logging import (
    LoggingMiddleware,
    add_log_level,
    add_timestamp,
    configure_logging,
    drop_color_message_key,
    get_console_processors,
    get_json_processors,
    get_logger,
)


class TestAddLogLevel:
    """Tests for add_log_level processor."""

    def test_add_log_level_info(self):
        """Test adding INFO log level."""
        event_dict = {"event": "test message"}
        result = add_log_level(None, "info", event_dict)

        assert result["level"] == "INFO"

    def test_add_log_level_error(self):
        """Test adding ERROR log level."""
        event_dict = {"event": "error message"}
        result = add_log_level(None, "error", event_dict)

        assert result["level"] == "ERROR"

    def test_add_log_level_warn_converted(self):
        """Test that 'warn' is converted to 'WARNING'."""
        event_dict = {"event": "warning message"}
        result = add_log_level(None, "warn", event_dict)

        assert result["level"] == "WARNING"

    def test_add_log_level_debug(self):
        """Test adding DEBUG log level."""
        event_dict = {"event": "debug message"}
        result = add_log_level(None, "debug", event_dict)

        assert result["level"] == "DEBUG"


class TestAddTimestamp:
    """Tests for add_timestamp processor."""

    def test_add_timestamp(self):
        """Test adding ISO timestamp."""
        event_dict = {"event": "test"}
        result = add_timestamp(None, "info", event_dict)

        assert "timestamp" in result
        # Should be ISO format
        assert "T" in result["timestamp"]
        assert result["timestamp"].endswith("+00:00") or "Z" in result["timestamp"]


class TestDropColorMessageKey:
    """Tests for drop_color_message_key processor."""

    def test_drop_color_message_key_present(self):
        """Test dropping color_message key when present."""
        event_dict = {"event": "test", "color_message": "colored text"}
        result = drop_color_message_key(None, "info", event_dict)

        assert "color_message" not in result
        assert result["event"] == "test"

    def test_drop_color_message_key_not_present(self):
        """Test handling when color_message not present."""
        event_dict = {"event": "test"}
        result = drop_color_message_key(None, "info", event_dict)

        assert result == {"event": "test"}


class TestGetProcessors:
    """Tests for processor list functions."""

    def test_get_json_processors(self):
        """Test JSON processors list."""
        processors = get_json_processors()

        assert isinstance(processors, list)
        assert len(processors) > 0
        # Should end with JSONRenderer
        assert "JSONRenderer" in str(type(processors[-1]))

    def test_get_console_processors(self):
        """Test console processors list."""
        processors = get_console_processors()

        assert isinstance(processors, list)
        assert len(processors) > 0
        # Should end with ConsoleRenderer
        assert "ConsoleRenderer" in str(type(processors[-1]))


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_logging_json_format(self):
        """Test configuring logging with JSON format."""
        with patch("backend.app.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_FORMAT = "json"

            with patch("backend.app.logging.structlog.configure") as mock_configure:
                configure_logging()

                mock_configure.assert_called_once()
                # Verify processors were passed
                call_kwargs = mock_configure.call_args.kwargs
                assert "processors" in call_kwargs

    def test_configure_logging_console_format(self):
        """Test configuring logging with console format."""
        with patch("backend.app.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "DEBUG"
            mock_settings.LOG_FORMAT = "console"

            with patch("backend.app.logging.structlog.configure") as mock_configure:
                configure_logging()

                mock_configure.assert_called_once()

    def test_configure_logging_sets_noisy_loggers(self):
        """Test that noisy library loggers are set to WARNING."""
        with patch("backend.app.logging.settings") as mock_settings:
            mock_settings.LOG_LEVEL = "INFO"
            mock_settings.LOG_FORMAT = "json"

            configure_logging()

            # Check that uvicorn.access is set to WARNING
            assert logging.getLogger("uvicorn.access").level == logging.WARNING
            assert logging.getLogger("httpx").level == logging.WARNING


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_bound_logger(self):
        """Test that get_logger returns a structlog BoundLogger."""
        logger = get_logger("test_module")

        assert logger is not None
        # Should be a structlog logger
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")

    def test_get_logger_default_name(self):
        """Test get_logger with default name."""
        logger = get_logger()

        assert logger is not None


class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    def test_middleware_init(self):
        """Test middleware initialization."""
        mock_app = MagicMock()
        middleware = LoggingMiddleware(mock_app)

        assert middleware.app is mock_app

    @pytest.mark.asyncio
    async def test_middleware_non_http_passthrough(self):
        """Test middleware passes through non-HTTP requests."""
        mock_app = AsyncMock()
        middleware = LoggingMiddleware(mock_app)

        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_middleware_http_binds_context(self):
        """Test middleware binds request context for HTTP requests."""
        mock_app = AsyncMock()
        middleware = LoggingMiddleware(mock_app)

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "GET",
            "headers": [],
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("backend.app.logging.structlog.contextvars") as mock_ctx:
            await middleware(scope, receive, send)

            mock_ctx.clear_contextvars.assert_called_once()
            mock_ctx.bind_contextvars.assert_called_once_with(
                request_id=None,
                path="/api/v1/test",
                method="GET",
            )

        mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_extracts_request_id(self):
        """Test middleware extracts x-request-id header."""
        mock_app = AsyncMock()
        middleware = LoggingMiddleware(mock_app)

        scope = {
            "type": "http",
            "path": "/api/v1/test",
            "method": "POST",
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-request-id", b"req-12345"),
            ],
        }
        receive = AsyncMock()
        send = AsyncMock()

        with patch("backend.app.logging.structlog.contextvars") as mock_ctx:
            await middleware(scope, receive, send)

            mock_ctx.bind_contextvars.assert_called_once_with(
                request_id="req-12345",
                path="/api/v1/test",
                method="POST",
            )
