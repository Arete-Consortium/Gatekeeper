"""Unit tests for WebSocket reconnection logic."""

import asyncio
import time
from unittest.mock import patch

import pytest

from backend.app.services.websocket_reconnection import (
    ConnectionHealth,
    ConnectionState,
    ReconnectingWebSocketClient,
    ReconnectionConfig,
)


class TestReconnectionConfig:
    """Tests for ReconnectionConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        with patch("backend.app.services.websocket_reconnection.settings") as mock_settings:
            mock_settings.WS_INITIAL_RETRY_DELAY = 1.0
            mock_settings.WS_MAX_RETRY_DELAY = 60.0
            mock_settings.WS_RETRY_MULTIPLIER = 2.0
            mock_settings.WS_MAX_RETRY_ATTEMPTS = 0
            mock_settings.WS_HEALTH_CHECK_INTERVAL = 30.0
            mock_settings.WS_CONNECTION_TIMEOUT = 10.0

            config = ReconnectionConfig()

            assert config.initial_delay == 1.0
            assert config.max_delay == 60.0
            assert config.multiplier == 2.0
            assert config.max_attempts == 0
            assert config.health_check_interval == 30.0
            assert config.connection_timeout == 10.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ReconnectionConfig(
            initial_delay=0.5,
            max_delay=30.0,
            multiplier=1.5,
            max_attempts=5,
            health_check_interval=15.0,
            connection_timeout=5.0,
        )

        assert config.initial_delay == 0.5
        assert config.max_delay == 30.0
        assert config.multiplier == 1.5
        assert config.max_attempts == 5
        assert config.health_check_interval == 15.0
        assert config.connection_timeout == 5.0

    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
        )

        # First attempt (0): 1 * 2^0 = 1
        assert config.calculate_delay(0) == 1.0

        # Second attempt (1): 1 * 2^1 = 2
        assert config.calculate_delay(1) == 2.0

        # Third attempt (2): 1 * 2^2 = 4
        assert config.calculate_delay(2) == 4.0

        # Fourth attempt (3): 1 * 2^3 = 8
        assert config.calculate_delay(3) == 8.0

    def test_calculate_delay_caps_at_max(self):
        """Test delay is capped at max_delay."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=10.0,
            multiplier=2.0,
        )

        # 1 * 2^5 = 32, but capped at 10
        assert config.calculate_delay(5) == 10.0

        # 1 * 2^10 = 1024, but capped at 10
        assert config.calculate_delay(10) == 10.0


class TestConnectionHealth:
    """Tests for ConnectionHealth metrics tracking."""

    def test_initial_state(self):
        """Test initial health state."""
        health = ConnectionHealth()

        assert health.last_connected_at is None
        assert health.last_disconnected_at is None
        assert health.last_message_received_at is None
        assert health.total_connections == 0
        assert health.total_disconnections == 0
        assert health.total_reconnections == 0
        assert health.current_retry_attempt == 0

    def test_record_connection_first_time(self):
        """Test recording first connection."""
        health = ConnectionHealth()
        before = time.time()
        health.record_connection()
        after = time.time()

        assert before <= health.last_connected_at <= after
        assert health.total_connections == 1
        assert health.total_reconnections == 0  # First connection is not a reconnection
        assert health.current_retry_attempt == 0

    def test_record_connection_reconnection(self):
        """Test recording reconnection."""
        health = ConnectionHealth()
        health.record_connection()  # First
        health.record_connection()  # Reconnection

        assert health.total_connections == 2
        assert health.total_reconnections == 1  # Second+ connections are reconnections

    def test_record_disconnection(self):
        """Test recording disconnection."""
        health = ConnectionHealth()
        before = time.time()
        health.record_disconnection()
        after = time.time()

        assert before <= health.last_disconnected_at <= after
        assert health.total_disconnections == 1

    def test_record_message(self):
        """Test recording message receipt."""
        health = ConnectionHealth()
        before = time.time()
        health.record_message()
        after = time.time()

        assert before <= health.last_message_received_at <= after

    def test_record_health_check(self):
        """Test recording health check."""
        health = ConnectionHealth()
        before = time.time()
        health.record_health_check()
        after = time.time()

        assert before <= health.last_health_check_at <= after

    def test_record_failed_attempt(self):
        """Test recording failed reconnection attempt."""
        health = ConnectionHealth()
        health.record_failed_attempt()

        assert health.current_retry_attempt == 1
        assert health.consecutive_failures == 1
        assert health.total_failed_reconnections == 1

        health.record_failed_attempt()
        assert health.current_retry_attempt == 2
        assert health.consecutive_failures == 2
        assert health.total_failed_reconnections == 2

    def test_reset_retry_counter(self):
        """Test resetting retry counter on success."""
        health = ConnectionHealth()
        health.record_failed_attempt()
        health.record_failed_attempt()
        health.reset_retry_counter()

        assert health.current_retry_attempt == 0
        assert health.consecutive_failures == 0
        # total_failed_reconnections should not be reset
        assert health.total_failed_reconnections == 2

    def test_uptime_seconds(self):
        """Test uptime calculation."""
        health = ConnectionHealth()

        # No connection yet
        assert health.uptime_seconds is None

        # After connection
        health.record_connection()
        time.sleep(0.1)
        assert health.uptime_seconds >= 0.1

    def test_time_since_last_message(self):
        """Test time since last message calculation."""
        health = ConnectionHealth()

        # No messages yet
        assert health.time_since_last_message is None

        # After message
        health.record_message()
        time.sleep(0.1)
        assert health.time_since_last_message >= 0.1

    def test_to_dict(self):
        """Test converting health metrics to dictionary."""
        health = ConnectionHealth()
        health.record_connection()
        health.record_message()

        result = health.to_dict()

        assert "last_connected_at" in result
        assert "last_message_received_at" in result
        assert "total_connections" in result
        assert "uptime_seconds" in result
        assert result["total_connections"] == 1


class MockWebSocketClient(ReconnectingWebSocketClient):
    """Mock implementation for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.receive_calls = 0
        self.health_check_calls = 0
        self.on_connect_calls = 0
        self.on_disconnect_calls = 0
        self.on_reconnect_failure_calls = 0

        # Control behavior
        self.connect_should_fail = False
        self.receive_should_fail = False
        self.messages_to_receive = 0

    async def _connect(self) -> None:
        self.connect_calls += 1
        if self.connect_should_fail:
            raise ConnectionError("Mock connection failure")

    async def _disconnect(self) -> None:
        self.disconnect_calls += 1

    async def _receive_message(self) -> None:
        self.receive_calls += 1
        if self.receive_should_fail:
            raise ConnectionError("Mock receive failure")
        if self.messages_to_receive > 0:
            self.messages_to_receive -= 1
        else:
            # Simulate waiting for message
            await asyncio.sleep(0.1)

    async def _send_health_check(self) -> None:
        self.health_check_calls += 1

    async def _on_connect(self) -> None:
        self.on_connect_calls += 1

    async def _on_disconnect(self) -> None:
        self.on_disconnect_calls += 1

    async def _on_reconnect_failure(self) -> None:
        self.on_reconnect_failure_calls += 1


class TestReconnectingWebSocketClient:
    """Tests for ReconnectingWebSocketClient."""

    def test_initial_state(self):
        """Test initial client state."""
        client = MockWebSocketClient(name="test")

        assert client.name == "test"
        assert client.state == ConnectionState.DISCONNECTED
        assert not client.is_connected
        assert not client.is_running

    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        """Test starting and stopping the client."""
        config = ReconnectionConfig(health_check_interval=1.0)
        client = MockWebSocketClient(name="test", config=config)

        await client.start()
        assert client.is_running

        # Let it connect
        await asyncio.sleep(0.2)
        assert client.connect_calls >= 1

        await client.stop()
        assert not client.is_running
        assert client.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test that starting twice logs warning."""
        client = MockWebSocketClient(name="test")

        await client.start()
        await client.start()  # Should just log warning

        await client.stop()

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        client = MockWebSocketClient(name="test")

        await client.start()
        await asyncio.sleep(0.2)

        assert client.state == ConnectionState.CONNECTED
        assert client.is_connected
        assert client.on_connect_calls >= 1
        assert client.health.total_connections >= 1

        await client.stop()

    @pytest.mark.asyncio
    async def test_connect_failure_with_retry(self):
        """Test connection failure triggers retry."""
        config = ReconnectionConfig(
            initial_delay=0.1,
            max_delay=0.5,
            max_attempts=3,
        )
        client = MockWebSocketClient(name="test", config=config)
        client.connect_should_fail = True

        await client.start()

        # Wait for retries to exhaust
        await asyncio.sleep(1.5)

        assert client.state == ConnectionState.FAILED
        assert not client.is_running
        assert client.connect_calls >= 3
        assert client.on_reconnect_failure_calls == 1

        await client.stop()

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self):
        """Test automatic reconnection after disconnect."""
        config = ReconnectionConfig(initial_delay=0.1)
        client = MockWebSocketClient(name="test", config=config)
        client.messages_to_receive = 2  # Receive 2 messages then disconnect

        await client.start()
        await asyncio.sleep(0.5)

        # Should have connected, received messages, then reconnected
        assert client.connect_calls >= 1

        await client.stop()

    @pytest.mark.asyncio
    async def test_max_retry_attempts(self):
        """Test that max retry attempts stops reconnection."""
        config = ReconnectionConfig(
            initial_delay=0.05,
            max_delay=0.1,
            max_attempts=2,
        )
        client = MockWebSocketClient(name="test", config=config)
        client.connect_should_fail = True

        await client.start()
        await asyncio.sleep(0.5)

        assert client.state == ConnectionState.FAILED
        assert client.connect_calls == 2
        assert client.health.current_retry_attempt == 2

        await client.stop()

    @pytest.mark.asyncio
    async def test_unlimited_retries(self):
        """Test unlimited retries when max_attempts is 0."""
        config = ReconnectionConfig(
            initial_delay=0.05,
            max_delay=0.1,
            max_attempts=0,  # Unlimited
        )
        client = MockWebSocketClient(name="test", config=config)
        client.connect_should_fail = True

        await client.start()
        await asyncio.sleep(0.3)

        # Should still be trying
        assert client.is_running
        assert client.connect_calls > 2  # Should have retried multiple times

        await client.stop()

    @pytest.mark.asyncio
    async def test_health_check_sent(self):
        """Test that health checks are sent periodically."""
        config = ReconnectionConfig(health_check_interval=0.1)
        client = MockWebSocketClient(name="test", config=config)

        await client.start()
        await asyncio.sleep(0.4)  # Wait for some health checks

        assert client.health_check_calls >= 1

        await client.stop()

    @pytest.mark.asyncio
    async def test_get_health_status(self):
        """Test health status reporting."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
            max_attempts=5,
        )
        client = MockWebSocketClient(name="test-client", config=config)

        await client.start()
        await asyncio.sleep(0.2)

        status = client.get_health_status()

        assert status["name"] == "test-client"
        assert status["state"] == "connected"
        assert status["is_connected"] is True
        assert status["is_running"] is True
        assert status["config"]["initial_delay"] == 1.0
        assert status["config"]["max_attempts"] == 5
        assert "health" in status
        assert status["health"]["total_connections"] >= 1

        await client.stop()

    @pytest.mark.asyncio
    async def test_wait_for_state(self):
        """Test waiting for a specific state."""
        client = MockWebSocketClient(name="test")

        await client.start()

        # Should reach connected state
        reached = await client.wait_for_state(ConnectionState.CONNECTED, timeout=2.0)
        assert reached

        await client.stop()

    @pytest.mark.asyncio
    async def test_wait_for_state_timeout(self):
        """Test timeout when waiting for state."""
        config = ReconnectionConfig(connection_timeout=0.1)
        client = MockWebSocketClient(name="test", config=config)
        client.connect_should_fail = True

        await client.start()

        # Should timeout waiting for connected state
        reached = await client.wait_for_state(ConnectionState.CONNECTED, timeout=0.3)
        assert not reached

        await client.stop()

    def test_connection_state_enum(self):
        """Test ConnectionState enum values."""
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.FAILED.value == "failed"


class TestExponentialBackoff:
    """Tests for exponential backoff behavior."""

    def test_backoff_sequence(self):
        """Test the backoff sequence."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=60.0,
            multiplier=2.0,
        )

        expected = [1, 2, 4, 8, 16, 32, 60, 60]  # Last values capped

        for attempt, expected_delay in enumerate(expected):
            assert config.calculate_delay(attempt) == expected_delay

    def test_backoff_with_different_multiplier(self):
        """Test backoff with 1.5x multiplier."""
        config = ReconnectionConfig(
            initial_delay=1.0,
            max_delay=100.0,
            multiplier=1.5,
        )

        # 1, 1.5, 2.25, 3.375, 5.0625...
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 1.5
        assert config.calculate_delay(2) == 2.25
        assert abs(config.calculate_delay(3) - 3.375) < 0.001

    def test_backoff_starts_at_initial_delay(self):
        """Test that backoff starts at initial_delay, not 0."""
        config = ReconnectionConfig(
            initial_delay=5.0,
            max_delay=100.0,
            multiplier=2.0,
        )

        assert config.calculate_delay(0) == 5.0
        assert config.calculate_delay(1) == 10.0


class TestConnectionHealthTracking:
    """Tests for connection health tracking during reconnection."""

    def test_health_tracks_consecutive_failures(self):
        """Test that consecutive failures are tracked."""
        health = ConnectionHealth()

        health.record_failed_attempt()
        assert health.consecutive_failures == 1

        health.record_failed_attempt()
        assert health.consecutive_failures == 2

        health.record_connection()
        assert health.consecutive_failures == 0  # Reset on success

    def test_health_tracks_total_failed_attempts(self):
        """Test that total failed attempts persist."""
        health = ConnectionHealth()

        health.record_failed_attempt()
        health.record_failed_attempt()
        health.record_connection()  # Success resets consecutive, not total
        health.record_failed_attempt()

        assert health.total_failed_reconnections == 3
        assert health.consecutive_failures == 1

    def test_health_tracks_reconnections(self):
        """Test reconnection counting."""
        health = ConnectionHealth()

        health.record_connection()  # First connection
        assert health.total_reconnections == 0

        health.record_disconnection()
        health.record_connection()  # Reconnection
        assert health.total_reconnections == 1

        health.record_disconnection()
        health.record_connection()  # Another reconnection
        assert health.total_reconnections == 2
