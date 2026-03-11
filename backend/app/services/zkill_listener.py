"""zKillboard RedisQ listener for real-time kill feed.

Uses HTTP long-polling (not WebSocket) but benefits from the same
reconnection patterns and health monitoring.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from ..core.config import settings
from .connection_manager import connection_manager
from .risk_engine import compute_risk
from .websocket_reconnection import (
    ConnectionHealth,
    ConnectionState,
    ReconnectionConfig,
)

logger = logging.getLogger(__name__)


class ZKillListener:
    """Listens to zKillboard RedisQ for real-time kill data.

    Uses HTTP long-polling with robust reconnection logic:
    - Exponential backoff on connection failures
    - Configurable retry delays from settings
    - Connection health monitoring
    - Automatic reconnection on disconnect
    - Optional maximum retry attempts
    """

    def __init__(
        self,
        queue_id: str | None = None,
        on_kill: Callable[[dict[str, Any]], None] | None = None,
        config: ReconnectionConfig | None = None,
    ):
        """Initialize the zKillboard listener.

        Args:
            queue_id: Unique queue ID for RedisQ (default: 'eve-gatekeeper')
            on_kill: Optional callback for each kill received
            config: Reconnection configuration (uses settings if not provided)
        """
        self.queue_id = queue_id or "eve-gatekeeper"
        self.on_kill = on_kill
        self._running = False
        self._task: asyncio.Task | None = None
        self._client: httpx.AsyncClient | None = None

        # Reconnection configuration
        self.config = config or ReconnectionConfig()

        # Connection health tracking
        self.health = ConnectionHealth()
        self._state = ConnectionState.DISCONNECTED

    @property
    def is_running(self) -> bool:
        """Check if the listener is running."""
        return self._running

    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if currently connected (actively polling)."""
        return self._state == ConnectionState.CONNECTED

    async def start(self) -> None:
        """Start the listener."""
        if self._running:
            logger.warning("ZKill listener already running")
            return

        self._running = True
        self._state = ConnectionState.CONNECTING
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout=35.0),  # RedisQ timeout is 30s
            headers={"User-Agent": settings.ZKILL_USER_AGENT},
            follow_redirects=True,
        )
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("ZKill listener started")

    async def stop(self) -> None:
        """Stop the listener."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._client:
            await self._client.aclose()
            self._client = None
        self._state = ConnectionState.DISCONNECTED
        logger.info("ZKill listener stopped")

    async def _listen_loop(self) -> None:
        """Main listening loop with reconnection logic."""
        while self._running:
            try:
                await self._fetch_kills()
                # Successful fetch - record connection and reset retry counter
                if self._state != ConnectionState.CONNECTED:
                    self._state = ConnectionState.CONNECTED
                    self.health.record_connection()
                    logger.info("ZKill listener connected to RedisQ")
                self.health.record_message()
                self.health.reset_retry_counter()
            except asyncio.CancelledError:
                break
            except httpx.TimeoutException:
                # Timeout is normal - RedisQ returns after 30s with no data
                # Still counts as healthy connection
                if self._state != ConnectionState.CONNECTED:
                    self._state = ConnectionState.CONNECTED
                    self.health.record_connection()
                self.health.reset_retry_counter()
                logger.debug("RedisQ timeout (normal), continuing...")
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from zKillboard: {e.response.status_code}")
                self.health.record_disconnection()
                self._state = ConnectionState.RECONNECTING
                should_continue = await self._handle_reconnect()
                if not should_continue:
                    break
            except Exception as e:
                logger.exception(f"Error in ZKill listener: {e}")
                self.health.record_disconnection()
                self._state = ConnectionState.RECONNECTING
                should_continue = await self._handle_reconnect()
                if not should_continue:
                    break

    async def _handle_reconnect(self) -> bool:
        """Handle reconnection with exponential backoff.

        Returns:
            True if should continue trying, False if max retries exceeded
        """
        if not self._running:
            return False

        self.health.record_failed_attempt()

        # Check if max attempts exceeded
        if self._should_give_up():
            logger.error(
                f"ZKill listener: Max retry attempts ({self.config.max_attempts}) exceeded. Giving up."
            )
            self._state = ConnectionState.FAILED
            self._running = False
            return False

        # Calculate delay using exponential backoff
        delay = self.config.calculate_delay(self.health.current_retry_attempt - 1)

        logger.info(
            f"ZKill listener: Reconnecting in {delay:.1f}s "
            f"(attempt {self.health.current_retry_attempt}"
            f"{f'/{self.config.max_attempts}' if self.config.max_attempts > 0 else ''})"
        )

        await asyncio.sleep(delay)
        return True

    def _should_give_up(self) -> bool:
        """Check if we should stop trying to reconnect."""
        if self.config.max_attempts <= 0:
            return False  # Unlimited retries
        return self.health.current_retry_attempt >= self.config.max_attempts

    async def _fetch_kills(self) -> None:
        """Fetch kills from RedisQ."""
        if not self._client:
            return

        url = f"{settings.ZKILL_REDISQ_URL}?queueID={self.queue_id}"

        response = await self._client.get(url)
        response.raise_for_status()

        data = response.json()
        package = data.get("package")

        if package is None:
            # No new kills available
            return

        # New RedisQ format: package has killID + zkb but no killmail
        # Fetch full killmail from ESI if not present
        if "killmail" not in package and "zkb" in package:
            killmail = await self._fetch_esi_killmail(package)
            if killmail:
                package["killmail"] = killmail
            else:
                logger.warning(f"Could not fetch ESI killmail for kill {package.get('killID')}")
                return

        # Process the kill
        await self._process_kill(package)

    async def _fetch_esi_killmail(self, package: dict[str, Any]) -> dict[str, Any] | None:
        """Fetch full killmail from ESI using the zkb href."""
        if not self._client:
            return None

        zkb = package.get("zkb", {})
        href = zkb.get("href")

        if href:
            try:
                resp = await self._client.get(href)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.debug(f"ESI killmail fetch via href failed: {e}")

        # Fallback: construct ESI URL from killID and hash
        kill_id = package.get("killID")
        kill_hash = zkb.get("hash")
        if kill_id and kill_hash:
            try:
                esi_url = f"https://esi.evetech.net/latest/killmails/{kill_id}/{kill_hash}/"
                resp = await self._client.get(esi_url)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning(f"ESI killmail fetch failed for {kill_id}: {e}")

        return None

    async def _process_kill(self, package: dict[str, Any]) -> None:
        """Process a kill package from zKillboard."""
        try:
            killmail = package.get("killmail", {})
            zkb = package.get("zkb", {})

            # Extract key information — support both old and new format
            kill_id = killmail.get("killmail_id") or package.get("killID")
            solar_system_id = killmail.get("solar_system_id")
            kill_time = killmail.get("killmail_time")
            victim = killmail.get("victim", {})

            # Check if it's a pod kill
            ship_type_id = victim.get("ship_type_id")
            is_pod = ship_type_id in (670, 33328)  # Capsule, Genolution Capsule

            # Get system name from our data
            from .data_loader import load_universe

            universe = load_universe()
            system_name = None
            region_id = None

            for name, sys in universe.systems.items():
                if sys.id == solar_system_id:
                    system_name = name
                    region_id = sys.region_id
                    break

            # Compute risk score if we know the system
            risk_score = 0.0
            if system_name:
                try:
                    risk_report = compute_risk(system_name)
                    risk_score = risk_report.score
                except Exception:
                    pass

            # Build kill data
            kill_data = {
                "kill_id": kill_id,
                "solar_system_id": solar_system_id,
                "solar_system_name": system_name,
                "region_id": region_id,
                "kill_time": kill_time,
                "ship_type_id": ship_type_id,
                "is_pod": is_pod,
                "victim_character_id": victim.get("character_id"),
                "victim_corporation_id": victim.get("corporation_id"),
                "victim_alliance_id": victim.get("alliance_id"),
                "attacker_count": len(killmail.get("attackers", [])),
                "total_value": zkb.get("totalValue"),
                "points": zkb.get("points"),
                "npc": zkb.get("npc", False),
                "solo": zkb.get("solo", False),
                "risk_score": risk_score,
                "received_at": datetime.now(UTC).isoformat(),
            }

            logger.debug(
                f"Kill {kill_id} in {system_name or solar_system_id}: "
                f"{kill_data['total_value']:,.0f} ISK"
            )

            # Store in kill history
            from .kill_history import get_kill_history

            history = get_kill_history()
            history.add_kill(kill_data)

            # Call custom handler if provided
            if self.on_kill:
                self.on_kill(kill_data)

            # Broadcast to connected WebSocket clients
            await connection_manager.broadcast_kill(kill_data)

            # Dispatch webhook alerts for matching subscriptions
            try:
                from .webhooks import KillAlert, dispatch_alert

                alert = KillAlert(
                    kill_id=kill_id,
                    system_name=system_name or str(solar_system_id),
                    system_id=solar_system_id,
                    region_id=region_id,
                    ship_type_id=ship_type_id,
                    attacker_count=len(killmail.get("attackers", [])),
                    total_value=zkb.get("totalValue"),
                    is_pod=is_pod,
                    is_npc=zkb.get("npc", False),
                    zkill_url=f"https://zkillboard.com/kill/{kill_id}/",
                )
                await dispatch_alert(alert)
            except Exception as e:
                logger.warning(f"Alert dispatch failed for kill {kill_id}: {e}")

            # Broadcast system risk update for map clients
            if system_name and solar_system_id:
                from .zkill_stats import fetch_system_kills

                try:
                    stats = await fetch_system_kills(solar_system_id, hours=1)
                    recent_kills = stats.recent_kills + stats.recent_pods
                    await connection_manager.broadcast_system_risk_update(
                        system_id=solar_system_id,
                        system_name=system_name,
                        risk_score=risk_score,
                        recent_kills=recent_kills,
                    )
                except Exception:
                    pass  # Don't fail on risk update error

            # Publish to Redis for multi-instance deployments
            from .redis_pubsub import get_redis_pubsub

            pubsub = get_redis_pubsub()
            await pubsub.publish_kill(kill_data)

        except Exception as e:
            logger.exception(f"Error processing kill: {e}")

    def get_health_status(self) -> dict[str, Any]:
        """Get the current health status of the listener."""
        return {
            "name": "zkill_listener",
            "state": self._state.value,
            "is_connected": self.is_connected,
            "is_running": self.is_running,
            "queue_id": self.queue_id,
            "config": {
                "initial_delay": self.config.initial_delay,
                "max_delay": self.config.max_delay,
                "multiplier": self.config.multiplier,
                "max_attempts": self.config.max_attempts,
            },
            "health": self.health.to_dict(),
        }


# Global listener instance
_zkill_listener: ZKillListener | None = None


def get_zkill_listener() -> ZKillListener:
    """Get or create the zKillboard listener instance."""
    global _zkill_listener
    if _zkill_listener is None:
        _zkill_listener = ZKillListener()
    return _zkill_listener
