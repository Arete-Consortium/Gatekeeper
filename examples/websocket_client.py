"""
EVE Gatekeeper WebSocket Client Example

Demonstrates connecting to the real-time kill feed WebSocket with:
- Automatic reconnection with exponential backoff
- Subscription management
- Event handling
- Logging and error handling

Usage:
    python websocket_client.py

    # Or import and use programmatically:
    from websocket_client import KillFeedClient

    async def handle_kill(event):
        print(f"Kill in {event['system_name']}")

    client = KillFeedClient("ws://localhost:8000/api/v1/ws/killfeed")
    client.on_kill = handle_kill
    await client.connect()
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KillEvent:
    """Represents a kill event from the feed."""

    kill_id: int
    system_id: int
    system_name: str
    region_id: int
    timestamp: datetime
    ship_type_id: int
    ship_name: str | None
    is_pod: bool
    total_value: float
    attacker_count: int
    npc: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KillEvent:
        """Create KillEvent from WebSocket message."""
        return cls(
            kill_id=data["kill_id"],
            system_id=data["solar_system_id"],
            system_name=data.get("solar_system_name", "Unknown"),
            region_id=data.get("region_id", 0),
            timestamp=datetime.fromisoformat(data["kill_time"].replace("Z", "+00:00")),
            ship_type_id=data.get("ship_type_id", 0),
            ship_name=data.get("ship_name"),
            is_pod=data.get("is_pod", False),
            total_value=data.get("total_value", 0.0),
            attacker_count=data.get("attacker_count", 0),
            npc=data.get("npc", False),
        )


@dataclass
class ReconnectConfig:
    """Configuration for reconnection behavior."""

    initial_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    max_attempts: int = 0  # 0 = unlimited


@dataclass
class KillFeedClient:
    """
    WebSocket client for EVE Gatekeeper kill feed.

    Features:
    - Automatic reconnection with exponential backoff
    - Subscription to specific systems or regions
    - Event callbacks for kills, connections, and errors

    Example:
        async def on_kill(event: KillEvent):
            print(f"Kill in {event.system_name}: {event.ship_name}")

        client = KillFeedClient("ws://localhost:8000/api/v1/ws/killfeed")
        client.on_kill = on_kill
        await client.connect()
    """

    url: str
    reconnect_config: ReconnectConfig = field(default_factory=ReconnectConfig)
    on_kill: Callable[[KillEvent], None] | None = None
    on_connect: Callable[[], None] | None = None
    on_disconnect: Callable[[str], None] | None = None
    on_error: Callable[[Exception], None] | None = None

    _websocket: Any = field(default=None, init=False, repr=False)
    _running: bool = field(default=False, init=False, repr=False)
    _reconnect_attempts: int = field(default=0, init=False, repr=False)
    _subscribed_systems: set[int] = field(default_factory=set, init=False, repr=False)
    _subscribed_regions: set[int] = field(default_factory=set, init=False, repr=False)

    async def connect(self) -> None:
        """
        Connect to the WebSocket and start receiving events.

        This method will run indefinitely, automatically reconnecting
        if the connection is lost.
        """
        self._running = True

        while self._running:
            try:
                await self._connect_once()
            except Exception as e:
                if not self._running:
                    break

                self._reconnect_attempts += 1

                if (
                    self.reconnect_config.max_attempts > 0
                    and self._reconnect_attempts >= self.reconnect_config.max_attempts
                ):
                    logger.error(
                        f"Max reconnection attempts reached ({self.reconnect_config.max_attempts})"
                    )
                    if self.on_error:
                        self.on_error(e)
                    break

                delay = self._calculate_backoff()
                logger.warning(
                    f"Connection lost, reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts})"
                )

                if self.on_disconnect:
                    self.on_disconnect(str(e))

                await asyncio.sleep(delay)

    async def _connect_once(self) -> None:
        """Establish a single WebSocket connection and handle messages."""
        import websockets

        logger.info(f"Connecting to {self.url}")

        async with websockets.connect(self.url) as ws:
            self._websocket = ws
            self._reconnect_attempts = 0

            logger.info("Connected to kill feed")
            if self.on_connect:
                self.on_connect()

            # Re-subscribe if we had previous subscriptions
            await self._resubscribe()

            # Handle incoming messages
            async for message in ws:
                try:
                    await self._handle_message(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse message: {e}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    if self.on_error:
                        self.on_error(e)

    async def _handle_message(self, message: str) -> None:
        """Process an incoming WebSocket message."""
        data = json.loads(message)

        # Check message type
        msg_type = data.get("type", "kill")

        if msg_type == "kill":
            event = KillEvent.from_dict(data)

            # Check if we should filter this event
            if self._should_handle_event(event):
                if self.on_kill:
                    self.on_kill(event)
        elif msg_type == "ping":
            # Respond to ping if needed
            pass
        elif msg_type == "subscribed":
            logger.debug(f"Subscription confirmed: {data}")
        else:
            logger.debug(f"Unknown message type: {msg_type}")

    def _should_handle_event(self, event: KillEvent) -> bool:
        """Check if event matches our subscriptions."""
        # If no subscriptions, handle all events
        if not self._subscribed_systems and not self._subscribed_regions:
            return True

        # Check system subscription
        if event.system_id in self._subscribed_systems:
            return True

        # Check region subscription
        if event.region_id in self._subscribed_regions:
            return True

        return False

    def _calculate_backoff(self) -> float:
        """Calculate delay for next reconnection attempt using exponential backoff."""
        delay = self.reconnect_config.initial_delay * (
            self.reconnect_config.multiplier ** (self._reconnect_attempts - 1)
        )
        return min(delay, self.reconnect_config.max_delay)

    async def _resubscribe(self) -> None:
        """Re-establish subscriptions after reconnection."""
        if self._subscribed_systems:
            await self._send_subscription("systems", list(self._subscribed_systems))
        if self._subscribed_regions:
            await self._send_subscription("regions", list(self._subscribed_regions))

    async def _send_subscription(self, sub_type: str, ids: list[int]) -> None:
        """Send a subscription message."""
        if self._websocket:
            message = {"action": "subscribe", "type": sub_type, "ids": ids}
            await self._websocket.send(json.dumps(message))
            logger.debug(f"Sent subscription for {len(ids)} {sub_type}")

    async def subscribe_system(self, system_id: int) -> None:
        """
        Subscribe to kills in a specific system.

        Args:
            system_id: EVE system ID to subscribe to
        """
        self._subscribed_systems.add(system_id)
        if self._websocket:
            await self._send_subscription("systems", [system_id])

    async def subscribe_systems(self, system_ids: list[int]) -> None:
        """Subscribe to kills in multiple systems."""
        self._subscribed_systems.update(system_ids)
        if self._websocket:
            await self._send_subscription("systems", system_ids)

    async def subscribe_region(self, region_id: int) -> None:
        """
        Subscribe to kills in a specific region.

        Args:
            region_id: EVE region ID to subscribe to
        """
        self._subscribed_regions.add(region_id)
        if self._websocket:
            await self._send_subscription("regions", [region_id])

    async def unsubscribe_system(self, system_id: int) -> None:
        """Unsubscribe from a system."""
        self._subscribed_systems.discard(system_id)
        if self._websocket:
            message = {"action": "unsubscribe", "type": "systems", "ids": [system_id]}
            await self._websocket.send(json.dumps(message))

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket."""
        self._running = False
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        logger.info("Disconnected from kill feed")

    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return self._websocket is not None and not self._websocket.closed


async def main():
    """Demo of the kill feed client."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Event handlers
    def on_kill(event: KillEvent):
        value_str = f"{event.total_value / 1_000_000:.1f}M ISK" if event.total_value else "Unknown"
        ship = event.ship_name or f"Ship ID {event.ship_type_id}"
        pod = " (POD)" if event.is_pod else ""
        npc = " [NPC]" if event.npc else ""
        print(
            f"[{event.timestamp.strftime('%H:%M:%S')}] Kill in {event.system_name}: {ship}{pod}{npc} - {value_str}"
        )

    def on_connect():
        print("\n*** Connected to kill feed ***\n")

    def on_disconnect(reason: str):
        print(f"\n*** Disconnected: {reason} ***\n")

    def on_error(error: Exception):
        print(f"\n*** Error: {error} ***\n")

    # Create client
    client = KillFeedClient(
        url="ws://localhost:8000/api/v1/ws/killfeed",
        reconnect_config=ReconnectConfig(
            initial_delay=1.0,
            max_delay=30.0,
            multiplier=2.0,
            max_attempts=0,  # Unlimited retries
        ),
    )

    # Set event handlers
    client.on_kill = on_kill
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_error = on_error

    print("EVE Gatekeeper Kill Feed Client")
    print("=" * 40)
    print("Connecting to ws://localhost:8000/api/v1/ws/killfeed")
    print("Press Ctrl+C to disconnect")
    print()

    try:
        # Connect and start receiving events
        await client.connect()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await client.disconnect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        print("\nMake sure the backend server is running:")
        print("  cd backend && uvicorn app.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
