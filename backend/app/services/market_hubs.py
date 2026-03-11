"""Market hub activity service — fetches live order counts from ESI.

For each of the 5 major trade hub regions, queries the ESI market orders
endpoint and reads the X-Pages header to estimate total active orders.
Results are cached for 30 minutes with graceful fallback to static estimates.
"""

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

# Cache TTL in seconds (30 minutes)
CACHE_TTL = 1800

# Hub definitions: (system_id, system_name, region_id, region_name, is_primary, static_volume)
HUB_DEFINITIONS: list[tuple[int, str, int, str, bool, float]] = [
    (30000142, "Jita", 10000002, "The Forge", True, 50_000_000_000_000),
    (30002187, "Amarr", 10000043, "Domain", False, 15_000_000_000_000),
    (30002659, "Dodixie", 10000032, "Sinq Laison", False, 3_000_000_000_000),
    (30002510, "Rens", 10000030, "Heimatar", False, 2_000_000_000_000),
    (30002053, "Hek", 10000042, "Metropolis", False, 1_000_000_000_000),
]

# Orders per page in ESI responses
ORDERS_PER_PAGE = 1000


@dataclass
class MarketHubData:
    """Market hub with live activity data."""

    system_id: int
    system_name: str
    region_id: int
    region_name: str
    is_primary: bool
    daily_volume_estimate: float
    active_orders: int


@dataclass
class _CacheEntry:
    """Cached market hub data with timestamp."""

    data: list[MarketHubData]
    timestamp: float


# Module-level cache
_cache: _CacheEntry | None = None


async def _fetch_region_order_pages(client: httpx.AsyncClient, region_id: int) -> int | None:
    """Fetch the X-Pages header for a region's market orders.

    Returns the total number of pages, or None on failure.
    """
    url = f"{settings.ESI_BASE_URL}/markets/{region_id}/orders/"
    try:
        response = await client.head(
            url,
            params={"order_type": "all", "page": 1},
        )
        response.raise_for_status()
        x_pages = response.headers.get("x-pages", "1")
        return int(x_pages)
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.warning("Failed to fetch order pages for region %d: %s", region_id, e)
        return None


async def fetch_market_hub_data() -> list[MarketHubData]:
    """Fetch live market activity for all 5 trade hubs.

    Uses the ESI X-Pages header to estimate active order counts per region.
    Falls back to static estimates on failure. Results are cached for 30 minutes.
    """
    global _cache

    # Check cache
    if _cache is not None and (time.monotonic() - _cache.timestamp) < CACHE_TTL:
        return _cache.data

    hubs: list[MarketHubData] = []
    esi_success = False

    try:
        async with httpx.AsyncClient(
            timeout=settings.ESI_TIMEOUT,
            headers={"User-Agent": settings.ESI_USER_AGENT},
        ) as client:
            # Fetch all regions concurrently
            tasks = [
                _fetch_region_order_pages(client, region_id)
                for _, _, region_id, _, _, _ in HUB_DEFINITIONS
            ]
            results = await asyncio.gather(*tasks)

            for (
                system_id,
                system_name,
                region_id,
                region_name,
                is_primary,
                static_volume,
            ), pages in zip(HUB_DEFINITIONS, results, strict=True):
                if pages is not None:
                    active_orders = pages * ORDERS_PER_PAGE
                    esi_success = True
                else:
                    # Fallback: estimate orders from static volume ratio
                    active_orders = 0

                hubs.append(
                    MarketHubData(
                        system_id=system_id,
                        system_name=system_name,
                        region_id=region_id,
                        region_name=region_name,
                        is_primary=is_primary,
                        daily_volume_estimate=static_volume,
                        active_orders=active_orders,
                    )
                )

    except Exception as e:
        logger.error("ESI market hub fetch failed entirely: %s", e)

    # If ESI failed for all hubs, return static fallback
    if not esi_success or not hubs:
        logger.info("Using static market hub estimates (ESI unavailable)")
        hubs = [
            MarketHubData(
                system_id=sid,
                system_name=sname,
                region_id=rid,
                region_name=rname,
                is_primary=primary,
                daily_volume_estimate=vol,
                active_orders=0,
            )
            for sid, sname, rid, rname, primary, vol in HUB_DEFINITIONS
        ]

    _cache = _CacheEntry(data=hubs, timestamp=time.monotonic())
    return hubs


def clear_cache() -> None:
    """Clear the market hub cache (useful for testing)."""
    global _cache
    _cache = None
