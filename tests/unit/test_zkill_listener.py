"""Unit tests for zKillboard listener."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.zkill_listener import ZKillListener


class TestZKillListenerInit:
    """Tests for ZKillListener initialization."""

    def test_default_queue_id(self):
        """Test default queue ID is set."""
        listener = ZKillListener()
        assert listener.queue_id == "eve-gatekeeper"

    def test_custom_queue_id(self):
        """Test custom queue ID."""
        listener = ZKillListener(queue_id="custom-queue")
        assert listener.queue_id == "custom-queue"

    def test_on_kill_callback(self):
        """Test on_kill callback is set."""
        callback = MagicMock()
        listener = ZKillListener(on_kill=callback)
        assert listener.on_kill is callback

    def test_initial_state(self):
        """Test initial state is not running."""
        listener = ZKillListener()
        assert listener.is_running is False
        assert listener._task is None
        assert listener._client is None


class TestZKillListenerLifecycle:
    """Tests for listener start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        """Test that start sets running state."""
        listener = ZKillListener()

        # Mock the listen loop to avoid actual network calls
        with patch.object(listener, "_listen_loop", new_callable=AsyncMock):
            await listener.start()

            assert listener.is_running is True
            assert listener._client is not None
            assert listener._task is not None

            # Clean up
            await listener.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test that starting twice logs warning."""
        listener = ZKillListener()

        with patch.object(listener, "_listen_loop", new_callable=AsyncMock):
            await listener.start()

            # Start again should not create new task
            with patch("backend.app.services.zkill_listener.logger") as mock_logger:
                await listener.start()
                mock_logger.warning.assert_called()

            await listener.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_state(self):
        """Test that stop clears running state."""
        listener = ZKillListener()

        with patch.object(listener, "_listen_loop", new_callable=AsyncMock):
            await listener.start()
            await listener.stop()

            assert listener.is_running is False
            assert listener._task is None
            assert listener._client is None

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test stopping when not running is safe."""
        listener = ZKillListener()

        # Should not raise
        await listener.stop()

        assert listener.is_running is False


class TestZKillListenerReconnect:
    """Tests for reconnection logic."""

    def test_initial_reconnect_delay(self):
        """Test initial reconnect delay is 1 second."""
        listener = ZKillListener()
        assert listener._reconnect_delay == 1

    def test_max_reconnect_delay(self):
        """Test max reconnect delay is set."""
        listener = ZKillListener()
        assert listener._max_reconnect_delay == 60


class TestZKillListenerCallback:
    """Tests for kill callback handling."""

    @pytest.mark.asyncio
    async def test_callback_receives_kill_data(self):
        """Test that callback receives kill data."""
        received_kills = []

        def on_kill(kill_data):
            received_kills.append(kill_data)

        listener = ZKillListener(on_kill=on_kill)

        # Simulate calling the callback
        test_kill = {"killmail_id": 12345, "solar_system_id": 30000142}
        if listener.on_kill:
            listener.on_kill(test_kill)

        assert len(received_kills) == 1
        assert received_kills[0]["killmail_id"] == 12345

    def test_no_callback_does_not_crash(self):
        """Test that listener works without callback."""
        listener = ZKillListener()
        assert listener.on_kill is None
        # Should not crash if we check the callback
        if listener.on_kill:
            listener.on_kill({})
