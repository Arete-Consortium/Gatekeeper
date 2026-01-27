"""Lightweight zKillboard client for fetching system kill stats."""

import logging

import httpx

from ..core.config import settings
from ..models.risk import ZKillStats

logger = logging.getLogger(__name__)

# Pod ship type IDs
_POD_TYPE_IDS = {670, 33328}


async def fetch_system_stats(system_id: int, hours: int = 24) -> ZKillStats:
    """
    Fetch recent kill/pod counts for a solar system from zKillboard.

    Returns empty ZKillStats on any error.
    """
    past_seconds = hours * 3600
    url = f"{settings.ZKILL_BASE_URL}/kills/solarSystemID/{system_id}/pastSeconds/{past_seconds}/"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={"User-Agent": settings.ZKILL_USER_AGENT},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            kills = response.json()

            if not isinstance(kills, list):
                return ZKillStats()

            recent_kills = 0
            recent_pods = 0

            for kill in kills:
                victim = kill.get("victim", {})
                ship_type_id = victim.get("ship_type_id", 0)
                if ship_type_id in _POD_TYPE_IDS:
                    recent_pods += 1
                else:
                    recent_kills += 1

            return ZKillStats(recent_kills=recent_kills, recent_pods=recent_pods)

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching zKill stats for system {system_id}")
        return ZKillStats()
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} fetching zKill stats for system {system_id}")
        return ZKillStats()
    except Exception as e:
        logger.exception(f"Error fetching zKill stats for system {system_id}: {e}")
        return ZKillStats()
