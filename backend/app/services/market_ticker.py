"""Market ticker service for ESI market history.

Fetches and caches market history for commonly traded items across
the 5 major trade hub regions via the ESI market history endpoint.
"""

import logging
import time

import httpx

from ..models.market_ticker import (
    MarketTickerHistoryResponse,
    MarketTickerItem,
    MarketTickerResponse,
)

logger = logging.getLogger(__name__)

# ESI market history endpoint
ESI_MARKET_HISTORY_URL = "https://esi.evetech.net/latest/markets/{region_id}/history/"

# Cache TTL: 1 hour (market history updates once/day)
CACHE_TTL = 3600

# Module-level cache
_ticker_cache: dict[str, list[MarketTickerItem]] = {}  # "region_id:type_id" -> items
_cache_time: dict[str, float] = {}

# Major trade hub regions
TRADE_HUB_REGIONS: dict[int, str] = {
    10000002: "The Forge",
    10000043: "Domain",
    10000032: "Sinq Laison",
    10000042: "Metropolis",
    10000030: "Heimatar",
}

# Top commonly traded items
TRACKED_ITEMS: dict[int, str] = {
    44992: "PLEX",
    34: "Tritanium",
    35: "Pyerite",
    36: "Mexallon",
    37: "Isogen",
    38: "Nocxium",
    39: "Zydrine",
    40: "Megacyte",
    11399: "Morphite",
    16272: "Heavy Water",
    16273: "Liquid Ozone",
    16275: "Strontium Clathrates",
    17888: "Nitrogen Isotopes",
    17889: "Hydrogen Isotopes",
    17887: "Oxygen Isotopes",
    16274: "Helium Isotopes",
    40520: "Small Skill Injector",
    40519: "Large Skill Injector",
    71050: "Omega",
}


def clear_cache() -> None:
    """Clear the module-level cache."""
    _ticker_cache.clear()
    _cache_time.clear()


def _cache_key(region_id: int, type_id: int) -> str:
    """Generate a cache key for a region/type pair."""
    return f"{region_id}:{type_id}"


async def _fetch_market_history(
    client: httpx.AsyncClient, region_id: int, type_id: int
) -> list[dict]:
    """Fetch market history from ESI for a single region/type pair.

    Args:
        client: httpx async client.
        region_id: EVE region ID.
        type_id: EVE type ID.

    Returns:
        List of daily market history entries from ESI.
    """
    url = ESI_MARKET_HISTORY_URL.format(region_id=region_id)
    try:
        resp = await client.get(
            url,
            params={"datasource": "tranquility", "type_id": type_id},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        logger.warning(
            "ESI market history fetch failed for region=%d type=%d: %s",
            region_id,
            type_id,
            exc,
        )
        return []


def _compute_price_change(history: list[dict]) -> float:
    """Compute price change percentage between last two days.

    Args:
        history: Sorted list of daily market history entries.

    Returns:
        Price change percentage (positive = increase, negative = decrease).
    """
    if len(history) < 2:
        return 0.0

    current = history[-1].get("average", 0.0)
    previous = history[-2].get("average", 0.0)

    if previous == 0.0:
        return 0.0

    return round(((current - previous) / previous) * 100, 2)


async def fetch_ticker_data(
    region_id: int | None = None, type_id: int | None = None
) -> list[MarketTickerItem]:
    """Fetch market ticker data for tracked items across trade hub regions.

    Uses a 1-hour cache since market history only updates once per day.

    Args:
        region_id: Optional region filter.
        type_id: Optional type filter.

    Returns:
        List of MarketTickerItem entries with latest prices.
    """
    regions = (
        {region_id: TRADE_HUB_REGIONS[region_id]}
        if region_id and region_id in TRADE_HUB_REGIONS
        else TRADE_HUB_REGIONS
    )
    items = (
        {type_id: TRACKED_ITEMS[type_id]}
        if type_id and type_id in TRACKED_ITEMS
        else TRACKED_ITEMS
    )

    now = time.time()
    results: list[MarketTickerItem] = []
    to_fetch: list[tuple[int, str, int, str]] = []  # (region_id, region_name, type_id, type_name)

    # Check cache first
    for rid, rname in regions.items():
        for tid, tname in items.items():
            key = _cache_key(rid, tid)
            cached_time = _cache_time.get(key, 0)
            if now - cached_time < CACHE_TTL and key in _ticker_cache:
                results.extend(_ticker_cache[key])
            else:
                to_fetch.append((rid, rname, tid, tname))

    if not to_fetch:
        return results

    async with httpx.AsyncClient(timeout=15.0) as client:
        for rid, rname, tid, tname in to_fetch:
            history = await _fetch_market_history(client, rid, tid)
            key = _cache_key(rid, tid)

            if not history:
                _ticker_cache[key] = []
                _cache_time[key] = now
                continue

            # Sort by date ascending
            history.sort(key=lambda x: x.get("date", ""))

            price_change = _compute_price_change(history)

            # Use the latest day's data
            latest = history[-1]
            ticker_item = MarketTickerItem(
                type_id=tid,
                type_name=tname,
                region_id=rid,
                region_name=rname,
                average_price=latest.get("average", 0.0),
                highest=latest.get("highest", 0.0),
                lowest=latest.get("lowest", 0.0),
                volume=latest.get("volume", 0),
                date=latest.get("date", ""),
                price_change_pct=price_change,
            )

            _ticker_cache[key] = [ticker_item]
            _cache_time[key] = now
            results.append(ticker_item)

    return results


async def get_market_ticker() -> MarketTickerResponse:
    """Get all tracked market ticker items.

    Returns:
        MarketTickerResponse with latest prices for all tracked items.
    """
    items = await fetch_ticker_data()
    return MarketTickerResponse(items=items, item_count=len(items))


async def get_item_history(type_id: int) -> MarketTickerHistoryResponse:
    """Get market history for a specific item across all trade hub regions.

    Args:
        type_id: EVE type ID.

    Returns:
        MarketTickerHistoryResponse with history entries.
    """
    type_name = TRACKED_ITEMS.get(type_id, f"Unknown ({type_id})")
    items = await fetch_ticker_data(type_id=type_id)
    return MarketTickerHistoryResponse(
        type_id=type_id,
        type_name=type_name,
        history=items,
    )
