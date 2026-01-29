"""WebSocket reconnection logic with exponential backoff and health monitoring.

This module provides a robust reconnection framework for WebSocket connections,
including configurable retry delays, health monitoring, and maximum retry limits.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..core.config import settings

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection states."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"  # Max retries exceeded


@dataclass
class ReconnectionConfig:
    """Configuration for WebSocket reconnection behavior."""

    initial_delay: float = field(default_factory=lambda: settings.WS_INITIAL_RETRY_DELAY)
    max_delay: float = field(default_factory=lambda: settings.WS_MAX_RETRY_DELAY)
    multiplier: float = field(default_factory=lambda: settings.WS_RETRY_MULTIPLIER)
    max_attempts: int = field(default_factory=lambda: settings.WS_MAX_RETRY_ATTEMPTS)
    health_check_interval: float = field(default_factory=lambda: settings.WS_HEALTH_CHECK_INTERVAL)
    connection_timeout: float = field(default_factory=lambda: settings.WS_CONNECTION_TIMEOUT)

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt using exponential backoff.

        Args:
            attempt: The current retry attempt (0-indexed)

        Returns:
            The delay in seconds, capped at max_delay
        """
        delay = self.initial_delay * (self.multiplier**attempt)
        return min(delay, self.max_delay)


@dataclass
class ConnectionHealth:
    """Tracks health metrics for a WebSocket connection."""

    last_connected_at: float | None = None
    last_disconnected_at: float | None = None
    last_message_received_at: float | None = None
    last_health_check_at: float | None = None
    total_connections: int = 0
    total_disconnections: int = 0
    total_reconnections: int = 0
    total_failed_reconnections: int = 0
    current_retry_attempt: int = 0
    consecutive_failures: int = 0

    def record_connection(self) -> None:
        """Record a successful connection."""
        now = time.time()
        self.last_connected_at = now
        self.total_connections += 1
        if self.total_connections > 1:
            self.total_reconnections += 1
        self.current_retry_attempt = 0
        self.consecutive_failures = 0

    def record_disconnection(self) -> None:
        """Record a disconnection."""
        self.last_disconnected_at = time.time()
        self.total_disconnections += 1

    def record_message(self) -> None:
        """Record a received message."""
        self.last_message_received_at = time.time()

    def record_health_check(self) -> None:
        """Record a health check."""
        self.last_health_check_at = time.time()

    def record_failed_attempt(self) -> None:
        """Record a failed reconnection attempt."""
        self.current_retry_attempt += 1
        self.consecutive_failures += 1
        self.total_failed_reconnections += 1

    def reset_retry_counter(self) -> None:
        """Reset retry counter (call on successful connection)."""
        self.current_retry_attempt = 0
        self.consecutive_failures = 0

    @property
    def uptime_seconds(self) -> float | None:
        """Calculate uptime since last connection."""
        if self.last_connected_at is None:
            return None
        return time.time() - self.last_connected_at

    @property
    def time_since_last_message(self) -> float | None:
        """Calculate time since last message received."""
        if self.last_message_received_at is None:
            return None
        return time.time() - self.last_message_received_at

    def to_dict(self) -> dict[str, Any]:
        """Convert health metrics to dictionary for API responses."""
        return {
            "last_connected_at": self.last_connected_at,
            "last_disconnected_at": self.last_disconnected_at,
            "last_message_received_at": self.last_message_received_at,
            "last_health_check_at": self.last_health_check_at,
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "total_reconnections": self.total_reconnections,
            "total_failed_reconnections": self.total_failed_reconnections,
            "current_retry_attempt": self.current_retry_attempt,
            "consecutive_failures": self.consecutive_failures,
            "uptime_seconds": self.uptime_seconds,
            "time_since_last_message": self.time_since_last_message,
        }


class ReconnectingWebSocketClient(ABC):
    """Abstract base class for WebSocket clients with automatic reconnection.

    Subclasses must implement:
    - _connect(): Establish the WebSocket connection
    - _disconnect(): Close the WebSocket connection
    - _receive_message(): Receive and process a message
    - _send_health_check(): Send a health check (ping) message

    Optional override:
    - _on_connect(): Called after successful connection
    - _on_disconnect(): Called after disconnection
    - _on_reconnect_failure(): Called when max retries exceeded
    """

    def __init__(
        self,
        name: str = "websocket",
        config: ReconnectionConfig | None = None,
    ):
        """Initialize the reconnecting WebSocket client.

        Args:
            name: A name for this connection (for logging)
            config: Reconnection configuration (uses defaults if not provided)
        """
        self.name = name
        self.config = config or ReconnectionConfig()
        self.health = ConnectionHealth()
        self._state = ConnectionState.DISCONNECTED
        self._running = False
        self._listen_task: asyncio.Task | None = None
        self._health_check_task: asyncio.Task | None = None
        self._state_lock = asyncio.Lock()
        self._state_changed = asyncio.Event()

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._state == ConnectionState.CONNECTED

    @property
    def is_running(self) -> bool:
        """Check if the client is running (attempting to maintain connection)."""
        return self._running

    async def start(self) -> None:
        """Start the WebSocket client with automatic reconnection."""
        if self._running:
            logger.warning(f"[{self.name}] Client already running")
            return

        self._running = True
        logger.info(f"[{self.name}] Starting WebSocket client")

        # Start the main listen loop
        self._listen_task = asyncio.create_task(self._listen_loop())

        # Start health check loop
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop(self) -> None:
        """Stop the WebSocket client and close connection."""
        if not self._running:
            return

        logger.info(f"[{self.name}] Stopping WebSocket client")
        self._running = False

        # Cancel tasks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        # Close connection
        await self._safe_disconnect()
        await self._set_state(ConnectionState.DISCONNECTED)

    async def _set_state(self, new_state: ConnectionState) -> None:
        """Set the connection state (thread-safe)."""
        async with self._state_lock:
            if self._state != new_state:
                old_state = self._state
                self._state = new_state
                logger.info(f"[{self.name}] State changed: {old_state.value} -> {new_state.value}")
                self._state_changed.set()

    async def wait_for_state(
        self,
        target_state: ConnectionState,
        timeout: float | None = None,
    ) -> bool:
        """Wait for a specific connection state.

        Args:
            target_state: The state to wait for
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if target state reached, False if timeout
        """
        try:
            async with asyncio.timeout(timeout):
                while self._state != target_state:
                    self._state_changed.clear()
                    if self._state == target_state:
                        return True
                    await self._state_changed.wait()
                return True
        except TimeoutError:
            return False

    async def _listen_loop(self) -> None:
        """Main loop that maintains connection with automatic reconnection."""
        while self._running:
            try:
                # Attempt to connect
                await self._attempt_connection()

                if not self.is_connected:
                    # Connection failed, handle reconnect
                    await self._handle_reconnect()
                    continue

                # Connected - start receiving messages
                try:
                    while self._running and self.is_connected:
                        await self._receive_message()
                        self.health.record_message()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning(f"[{self.name}] Error receiving message: {e}")

                # Disconnected - record and prepare for reconnect
                self.health.record_disconnection()
                await self._safe_disconnect()
                await self._on_disconnect()
                await self._set_state(ConnectionState.RECONNECTING)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"[{self.name}] Unexpected error in listen loop: {e}")
                await self._handle_reconnect()

    async def _attempt_connection(self) -> None:
        """Attempt to establish a connection."""
        await self._set_state(ConnectionState.CONNECTING)

        try:
            await asyncio.wait_for(
                self._connect(),
                timeout=self.config.connection_timeout,
            )
            await self._set_state(ConnectionState.CONNECTED)
            self.health.record_connection()
            await self._on_connect()
            logger.info(f"[{self.name}] Connected successfully")
        except TimeoutError:
            logger.warning(f"[{self.name}] Connection timed out")
            await self._set_state(ConnectionState.RECONNECTING)
        except Exception as e:
            logger.warning(f"[{self.name}] Connection failed: {e}")
            await self._set_state(ConnectionState.RECONNECTING)

    async def _handle_reconnect(self) -> None:
        """Handle reconnection with exponential backoff."""
        if not self._running:
            return

        self.health.record_failed_attempt()

        # Check if max attempts exceeded
        if self._should_give_up():
            logger.error(
                f"[{self.name}] Max retry attempts ({self.config.max_attempts}) exceeded. Giving up."
            )
            await self._set_state(ConnectionState.FAILED)
            await self._on_reconnect_failure()
            self._running = False
            return

        # Calculate delay
        delay = self.config.calculate_delay(self.health.current_retry_attempt - 1)

        logger.info(
            f"[{self.name}] Reconnecting in {delay:.1f}s "
            f"(attempt {self.health.current_retry_attempt}"
            f"{f'/{self.config.max_attempts}' if self.config.max_attempts > 0 else ''})"
        )

        await asyncio.sleep(delay)

    def _should_give_up(self) -> bool:
        """Check if we should stop trying to reconnect."""
        if self.config.max_attempts <= 0:
            return False  # Unlimited retries
        return self.health.current_retry_attempt >= self.config.max_attempts

    async def _health_check_loop(self) -> None:
        """Periodically send health check (ping) messages."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval)

                if self.is_connected:
                    try:
                        await self._send_health_check()
                        self.health.record_health_check()
                        logger.debug(f"[{self.name}] Health check sent")
                    except Exception as e:
                        logger.warning(f"[{self.name}] Health check failed: {e}")
            except asyncio.CancelledError:
                break

    async def _safe_disconnect(self) -> None:
        """Safely disconnect, catching any errors."""
        try:
            await self._disconnect()
        except Exception as e:
            logger.debug(f"[{self.name}] Error during disconnect (ignored): {e}")

    # Abstract methods - must be implemented by subclasses

    @abstractmethod
    async def _connect(self) -> None:
        """Establish the WebSocket connection.

        Raises:
            Exception: If connection fails
        """
        pass

    @abstractmethod
    async def _disconnect(self) -> None:
        """Close the WebSocket connection."""
        pass

    @abstractmethod
    async def _receive_message(self) -> None:
        """Receive and process a single message.

        This should block until a message is received.
        Raises an exception if the connection is lost.
        """
        pass

    @abstractmethod
    async def _send_health_check(self) -> None:
        """Send a health check message (ping).

        Raises:
            Exception: If sending fails
        """
        pass

    # Optional hooks for subclasses (intentionally not abstract - override as needed)

    async def _on_connect(self) -> None:  # noqa: B027
        """Called after successful connection. Override in subclass."""

    async def _on_disconnect(self) -> None:  # noqa: B027
        """Called after disconnection. Override in subclass."""

    async def _on_reconnect_failure(self) -> None:  # noqa: B027
        """Called when max retries exceeded. Override in subclass."""

    def get_health_status(self) -> dict[str, Any]:
        """Get the current health status of the connection."""
        return {
            "name": self.name,
            "state": self._state.value,
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "config": {
                "initial_delay": self.config.initial_delay,
                "max_delay": self.config.max_delay,
                "multiplier": self.config.multiplier,
                "max_attempts": self.config.max_attempts,
                "health_check_interval": self.config.health_check_interval,
                "connection_timeout": self.config.connection_timeout,
            },
            "health": self.health.to_dict(),
        }
