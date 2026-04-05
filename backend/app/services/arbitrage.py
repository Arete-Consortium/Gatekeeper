"""Market arbitrage service for cross-hub price comparison.

Fetches live market orders from ESI for each trade hub region,
filters to hub station systems, and identifies profitable arbitrage
opportunities between hubs.
"""

import logging
import time

import httpx

from ..models.arbitrage import (
    ArbitrageCompareResponse,
    ArbitrageOpportunity,
    HubPriceData,
    PopularItem,
    PopularItemsResponse,
)

logger = logging.getLogger(__name__)

# ESI market orders endpoint
ESI_MARKET_ORDERS_URL = "https://esi.evetech.net/latest/markets/{region_id}/orders/"

# ESI universe names endpoint (for resolving type_id -> name)
ESI_NAMES_URL = "https://esi.evetech.net/latest/universe/names/"

# Cache TTL: 5 minutes
CACHE_TTL = 300

# Module-level cache: type_id -> (timestamp, ArbitrageCompareResponse)
_compare_cache: dict[str, tuple[float, ArbitrageCompareResponse]] = {}

# Trade hubs: system_id -> (system_name, region_id)
TRADE_HUBS: dict[int, tuple[str, int]] = {
    30000142: ("Jita", 10000002),
    30002187: ("Amarr", 10000043),
    30002659: ("Dodixie", 10000032),
    30002510: ("Rens", 10000030),
    30002053: ("Hek", 10000042),
}

# Popular items for quick access
POPULAR_ITEMS: list[PopularItem] = [
    PopularItem(type_id=44992, name="PLEX", category="Services"),
    PopularItem(type_id=40519, name="Large Skill Injector", category="Services"),
    PopularItem(type_id=40520, name="Small Skill Injector", category="Services"),
    PopularItem(type_id=29668, name="PLEX Vault", category="Services"),
    # Minerals
    PopularItem(type_id=34, name="Tritanium", category="Minerals"),
    PopularItem(type_id=35, name="Pyerite", category="Minerals"),
    PopularItem(type_id=36, name="Mexallon", category="Minerals"),
    PopularItem(type_id=37, name="Isogen", category="Minerals"),
    PopularItem(type_id=38, name="Nocxium", category="Minerals"),
    PopularItem(type_id=39, name="Zydrine", category="Minerals"),
    PopularItem(type_id=40, name="Megacyte", category="Minerals"),
    PopularItem(type_id=11399, name="Morphite", category="Minerals"),
    # Fuel
    PopularItem(type_id=16272, name="Heavy Water", category="Fuel"),
    PopularItem(type_id=16273, name="Liquid Ozone", category="Fuel"),
    PopularItem(type_id=16275, name="Strontium Clathrates", category="Fuel"),
    PopularItem(type_id=17888, name="Nitrogen Isotopes", category="Fuel"),
    PopularItem(type_id=17889, name="Hydrogen Isotopes", category="Fuel"),
    PopularItem(type_id=17887, name="Oxygen Isotopes", category="Fuel"),
    PopularItem(type_id=16274, name="Helium Isotopes", category="Fuel"),
    # Faction Modules
    PopularItem(
        type_id=14106, name="Caldari Navy Ballistic Control System", category="Faction Modules"
    ),
    PopularItem(type_id=15681, name="Republic Fleet Gyrostabilizer", category="Faction Modules"),
    PopularItem(type_id=15895, name="Dread Guristas Warp Disruptor", category="Faction Modules"),
    PopularItem(
        type_id=14670, name="Corpum A-Type Medium Armor Repairer", category="Faction Modules"
    ),
    # T2 Ships
    PopularItem(type_id=12005, name="Ishtar", category="T2 Ships"),
    PopularItem(type_id=22444, name="Deimos", category="T2 Ships"),
    PopularItem(type_id=12011, name="Cerberus", category="T2 Ships"),
    PopularItem(type_id=12023, name="Muninn", category="T2 Ships"),
    PopularItem(type_id=34562, name="Svipul", category="T2 Ships"),
]

# Name cache: type_id -> name
_name_cache: dict[int, str] = {item.type_id: item.name for item in POPULAR_ITEMS}


async def _resolve_type_name(type_id: int) -> str:
    """Resolve a type_id to its name via ESI.

    Args:
        type_id: EVE type ID.

    Returns:
        Item name, or a fallback string if resolution fails.
    """
    if type_id in _name_cache:
        return _name_cache[type_id]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                ESI_NAMES_URL,
                json=[type_id],
                params={"datasource": "tranquility"},
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                name = data[0].get("name", f"Type {type_id}")
                _name_cache[type_id] = name
                return name
    except httpx.HTTPError as exc:
        logger.warning("ESI name resolution failed for type_id=%d: %s", type_id, exc)

    return f"Type {type_id}"


async def _fetch_hub_orders(
    client: httpx.AsyncClient,
    region_id: int,
    type_id: int,
    system_id: int,
) -> tuple[float, float, int, int]:
    """Fetch market orders from ESI and extract best buy/sell for a hub system.

    Args:
        client: httpx async client.
        region_id: Region containing the trade hub.
        type_id: EVE item type ID.
        system_id: Trade hub solar system ID.

    Returns:
        Tuple of (best_buy, best_sell, buy_volume, sell_volume).
    """
    url = ESI_MARKET_ORDERS_URL.format(region_id=region_id)
    all_orders: list[dict] = []
    page = 1

    while True:
        try:
            resp = await client.get(
                url,
                params={
                    "datasource": "tranquility",
                    "type_id": type_id,
                    "order_type": "all",
                    "page": page,
                },
            )
            resp.raise_for_status()
            orders = resp.json()
            if not orders:
                break
            all_orders.extend(orders)

            # Check if more pages
            total_pages = int(resp.headers.get("x-pages", "1"))
            if page >= total_pages:
                break
            page += 1
        except httpx.HTTPError as exc:
            logger.warning(
                "ESI market orders fetch failed region=%d type=%d page=%d: %s",
                region_id,
                type_id,
                page,
                exc,
            )
            break

    # Filter to orders in the hub system
    hub_orders = [o for o in all_orders if o.get("system_id") == system_id]

    buy_orders = [o for o in hub_orders if o.get("is_buy_order")]
    sell_orders = [o for o in hub_orders if not o.get("is_buy_order")]

    best_buy = max((o.get("price", 0.0) for o in buy_orders), default=0.0)
    best_sell = min(
        (o.get("price", 0.0) for o in sell_orders if o.get("price", 0.0) > 0),
        default=0.0,
    )
    buy_volume = sum(o.get("volume_remain", 0) for o in buy_orders)
    sell_volume = sum(o.get("volume_remain", 0) for o in sell_orders)

    return best_buy, best_sell, buy_volume, sell_volume


async def compare_hubs(
    type_id: int,
    hub_system_ids: list[int] | None = None,
) -> ArbitrageCompareResponse:
    """Compare market prices for an item across trade hubs.

    Args:
        type_id: EVE item type ID.
        hub_system_ids: Optional list of hub system IDs to compare.
            Defaults to all 5 major hubs.

    Returns:
        ArbitrageCompareResponse with hub prices and arbitrage opportunities.
    """
    if hub_system_ids is None:
        hub_system_ids = list(TRADE_HUBS.keys())

    # Validate hub IDs
    hub_system_ids = [h for h in hub_system_ids if h in TRADE_HUBS]
    if not hub_system_ids:
        hub_system_ids = list(TRADE_HUBS.keys())

    # Check cache
    cache_key = f"{type_id}:{','.join(str(h) for h in sorted(hub_system_ids))}"
    now = time.time()
    if cache_key in _compare_cache:
        cached_time, cached_response = _compare_cache[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_response

    # Resolve type name
    type_name = await _resolve_type_name(type_id)

    # Fetch orders for each hub
    hub_prices: list[HubPriceData] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for system_id in hub_system_ids:
            system_name, region_id = TRADE_HUBS[system_id]
            best_buy, best_sell, buy_volume, sell_volume = await _fetch_hub_orders(
                client, region_id, type_id, system_id
            )

            # Calculate spread
            spread = 0.0
            if best_buy > 0 and best_sell > 0:
                spread = round(((best_sell - best_buy) / best_sell) * 100, 2)

            hub_prices.append(
                HubPriceData(
                    system_id=system_id,
                    system_name=system_name,
                    region_id=region_id,
                    best_buy=best_buy,
                    best_sell=best_sell,
                    spread=spread,
                    buy_volume=buy_volume,
                    sell_volume=sell_volume,
                )
            )

    # Calculate arbitrage opportunities
    # For each pair of hubs: buy at hub with lowest sell, sell at hub with highest buy
    opportunities: list[ArbitrageOpportunity] = []
    for buy_hub in hub_prices:
        if buy_hub.best_sell <= 0:
            continue
        for sell_hub in hub_prices:
            if sell_hub.system_id == buy_hub.system_id:
                continue
            if sell_hub.best_buy <= 0:
                continue

            profit = sell_hub.best_buy - buy_hub.best_sell
            if profit > 0:
                margin_pct = round((profit / buy_hub.best_sell) * 100, 2)
                opportunities.append(
                    ArbitrageOpportunity(
                        buy_hub=buy_hub.system_name,
                        buy_hub_id=buy_hub.system_id,
                        buy_price=buy_hub.best_sell,
                        sell_hub=sell_hub.system_name,
                        sell_hub_id=sell_hub.system_id,
                        sell_price=sell_hub.best_buy,
                        profit_per_unit=round(profit, 2),
                        margin_pct=margin_pct,
                    )
                )

    # Sort opportunities by margin descending
    opportunities.sort(key=lambda x: x.margin_pct, reverse=True)

    response = ArbitrageCompareResponse(
        type_id=type_id,
        type_name=type_name,
        hubs=hub_prices,
        opportunities=opportunities,
    )

    # Cache result
    _compare_cache[cache_key] = (now, response)

    return response


async def get_popular_items() -> PopularItemsResponse:
    """Get list of commonly traded items for quick arbitrage lookup.

    Returns:
        PopularItemsResponse with curated item list.
    """
    return PopularItemsResponse(
        items=POPULAR_ITEMS,
        count=len(POPULAR_ITEMS),
    )
