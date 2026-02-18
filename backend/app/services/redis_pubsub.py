"""Redis pub/sub service for multi-instance kill event broadcasting.

Enables multiple API instances to share kill events in real-time.
When one instance receives a kill from zKillboard, it publishes to Redis,
and all other instances receive and broadcast to their local WebSocket clients.
"""

import asyncio
import json
import logging
from typing import Any

from ..core.config import settings

logger = logging.getLogger(__name__)


class RedisPubSub:
    """Redis pub/sub service for kill event broadcasting.

    Features:
    - Publishes kills to Redis channel when received
    - Subscribes to channel and broadcasts to local WebSocket clients
    - Automatic reconnection on connection loss
    - Graceful fallback when Redis not available
    """

    def __init__(self, channel: str | None = None):
        self._channel = channel or settings.REDIS_PUBSUB_CHANNEL
        self._running = False
        self._subscribe_task: asyncio.Task | None = None
        self._redis: Any = None
        self._pubsub: Any = None
        self._connected = False
        self._instance_id = self._generate_instance_id()

        # Stats
        self._messages_published = 0
        self._messages_received = 0
        self._messages_ignored = 0  # From self

    def _generate_instance_id(self) -> str:
        """Generate a unique instance ID for this process."""
        import os
        import uuid

        return f"{os.getpid()}-{uuid.uuid4().hex[:8]}"

    @property
    def is_enabled(self) -> bool:
        """Check if pub/sub is enabled."""
        return settings.REDIS_URL is not None and settings.REDIS_PUBSUB_ENABLED

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected

    async def start(self) -> None:
        """Start the pub/sub service."""
        if self._running:
            logger.warning("Redis pub/sub already running")
            return

        if not self.is_enabled:
            logger.info("Redis pub/sub disabled (no REDIS_URL configured)")
            return

        self._running = True

        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()  # type: ignore[attr-defined]
            self._connected = True

            # Start subscription listener
            self._subscribe_task = asyncio.create_task(self._subscribe_loop())

            logger.info(
                "Redis pub/sub started",
                extra={
                    "channel": self._channel,
                    "instance_id": self._instance_id,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to start Redis pub/sub: {e}")
            self._running = False
            self._connected = False

    async def stop(self) -> None:
        """Stop the pub/sub service."""
        self._running = False

        if self._subscribe_task:
            self._subscribe_task.cancel()
            try:
                await self._subscribe_task
            except asyncio.CancelledError:
                pass
            self._subscribe_task = None

        if self._pubsub:
            await self._pubsub.unsubscribe(self._channel)
            await self._pubsub.close()
            self._pubsub = None

        if self._redis:
            await self._redis.close()
            self._redis = None

        self._connected = False
        logger.info("Redis pub/sub stopped")

    async def publish_kill(self, kill_data: dict[str, Any]) -> bool:
        """Publish a kill event to Redis.

        Args:
            kill_data: Kill data to publish.

        Returns:
            True if published, False otherwise.
        """
        if not self._connected or not self._redis:
            return False

        try:
            # Add instance ID to identify source
            message = {
                "type": "kill",
                "instance_id": self._instance_id,
                "data": kill_data,
            }

            await self._redis.publish(self._channel, json.dumps(message, default=str))
            self._messages_published += 1

            logger.debug(
                "Published kill to Redis",
                extra={"kill_id": kill_data.get("kill_id"), "channel": self._channel},
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to publish kill to Redis: {e}")
            return False

    async def _subscribe_loop(self) -> None:
        """Main subscription loop."""
        while self._running:
            try:
                await self._subscribe()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Redis subscription: {e}")
                self._connected = False
                if self._running:
                    await asyncio.sleep(5)  # Wait before retry

    async def _subscribe(self) -> None:
        """Subscribe to the kill channel and process messages."""
        if not self._redis:
            return

        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(self._channel)

        logger.debug(f"Subscribed to Redis channel: {self._channel}")

        async for message in self._pubsub.listen():
            if not self._running:
                break

            if message["type"] != "message":
                continue

            try:
                data = json.loads(message["data"])
                await self._handle_message(data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in Redis message")
            except Exception as e:
                logger.error(f"Error handling Redis message: {e}")

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming pub/sub message.

        Ignores messages from this instance to prevent echo.
        """
        msg_type = message.get("type")
        instance_id = message.get("instance_id")
        data = message.get("data")

        # Ignore messages from self
        if instance_id == self._instance_id:
            self._messages_ignored += 1
            return

        self._messages_received += 1

        if msg_type == "kill" and data:
            logger.debug(
                "Received kill from Redis pub/sub",
                extra={"kill_id": data.get("kill_id"), "from_instance": instance_id},
            )

            # Broadcast to local WebSocket clients
            from .connection_manager import connection_manager

            await connection_manager.broadcast_kill(data)

            # Add to local kill history
            from .kill_history import get_kill_history

            history = get_kill_history()
            history.add_kill(data)

    def get_stats(self) -> dict[str, Any]:
        """Get pub/sub statistics."""
        return {
            "enabled": self.is_enabled,
            "connected": self._connected,
            "channel": self._channel,
            "instance_id": self._instance_id,
            "messages_published": self._messages_published,
            "messages_received": self._messages_received,
            "messages_ignored_self": self._messages_ignored,
        }


# Global instance
_redis_pubsub: RedisPubSub | None = None


def get_redis_pubsub() -> RedisPubSub:
    """Get or create the Redis pub/sub instance."""
    global _redis_pubsub
    if _redis_pubsub is None:
        _redis_pubsub = RedisPubSub()
    return _redis_pubsub
