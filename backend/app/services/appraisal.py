"""Appraisal service for EVE Online item price lookups.

Parses item paste formats, resolves names via ESI, and fetches
Jita market prices from the Fuzzwork market API.
"""

import logging
import re
import time
from collections import defaultdict

import httpx

from ..models.appraisal import AppraisalItem, AppraisalResponse

logger = logging.getLogger(__name__)

# Module-level caches
_name_cache: dict[str, int] = {}  # lowercase name -> type_id
_price_cache: dict[int, tuple[float, float]] = {}  # type_id -> (buy, sell)
_price_cache_time: dict[int, float] = {}  # type_id -> timestamp

PRICE_CACHE_TTL = 300  # 5 minutes
JITA_STATION_ID = 60003760
ESI_IDS_URL = "https://esi.evetech.net/latest/universe/ids/"
FUZZWORK_URL = "https://market.fuzzwork.co.uk/aggregates/"
BATCH_SIZE = 100


def parse_items(raw_text: str) -> list[tuple[str, int]]:
    """Parse EVE item paste text into (name, quantity) pairs.

    Supports formats:
        - Tab-separated: ``Tritanium\\t1,000``
        - Quantity prefix: ``1000 Tritanium``
        - Quantity suffix: ``Tritanium 1000``
        - Multiplier: ``Tritanium x1000`` or ``Tritanium x 1000``
        - Name only: ``Tritanium`` (quantity defaults to 1)
        - Fitting headers (lines starting with ``[``) are skipped

    Args:
        raw_text: Raw pasted text from EVE Online.

    Returns:
        List of (item_name, quantity) tuples.
    """
    results: list[tuple[str, int]] = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("["):
            continue

        # Tab-separated: "Tritanium\t1,000" or "Tritanium\t1,000\textra fields"
        if "\t" in line:
            parts = line.split("\t")
            name = parts[0].strip()
            qty = 1
            if len(parts) > 1:
                qty_str = parts[1].strip().replace(",", "")
                try:
                    qty = int(qty_str)
                except ValueError:
                    qty = 1
            if name:
                results.append((name, qty))
            continue

        # Multiplier: "Tritanium x1000" or "Tritanium x 1000"
        mult_match = re.match(
            r"^(.+?)\s+x\s*(\d[\d,]*)\s*$", line, re.IGNORECASE
        )
        if mult_match:
            name = mult_match.group(1).strip()
            qty = int(mult_match.group(2).replace(",", ""))
            if name:
                results.append((name, qty))
            continue

        # Quantity prefix: "1000 Tritanium"
        prefix_match = re.match(r"^(\d[\d,]*)\s+(.+)$", line)
        if prefix_match:
            qty = int(prefix_match.group(1).replace(",", ""))
            name = prefix_match.group(2).strip()
            if name:
                results.append((name, qty))
            continue

        # Quantity suffix: "Tritanium 1000" (last token is a number)
        parts = line.rsplit(None, 1)
        if len(parts) == 2:
            potential_qty = parts[1].replace(",", "")
            if potential_qty.isdigit():
                name = parts[0].strip()
                qty = int(potential_qty)
                if name:
                    results.append((name, qty))
                continue

        # Name only — quantity = 1
        results.append((line, 1))

    return results


async def resolve_names(names: list[str]) -> dict[str, int]:
    """Resolve item names to EVE type IDs via ESI.

    Uses a module-level cache to avoid redundant lookups.
    Matching is case-insensitive.

    Args:
        names: List of item type names.

    Returns:
        Mapping of original name -> type_id for resolved items.
    """
    result: dict[str, int] = {}
    to_resolve: list[str] = []

    for name in names:
        cached_id = _name_cache.get(name.lower())
        if cached_id is not None:
            result[name] = cached_id
        else:
            to_resolve.append(name)

    if not to_resolve:
        return result

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                ESI_IDS_URL,
                json=to_resolve,
                params={"datasource": "tranquility", "language": "en"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("ESI name resolution failed: %s", exc)
        return result

    esi_types = data.get("inventory_types", [])
    # Build lowercase lookup from ESI response
    esi_map: dict[str, int] = {}
    for item in esi_types:
        esi_map[item["name"].lower()] = item["id"]

    for name in to_resolve:
        type_id = esi_map.get(name.lower())
        if type_id is not None:
            result[name] = type_id
            _name_cache[name.lower()] = type_id

    return result


async def get_jita_prices(
    type_ids: list[int],
) -> dict[int, tuple[float, float]]:
    """Fetch Jita 4-4 market prices from Fuzzwork.

    Batches requests in groups of 100 and caches results for 5 minutes.

    Args:
        type_ids: List of EVE type IDs to price.

    Returns:
        Mapping of type_id -> (buy_max, sell_min).
    """
    result: dict[int, tuple[float, float]] = {}
    now = time.time()
    to_fetch: list[int] = []

    for tid in type_ids:
        cached_time = _price_cache_time.get(tid, 0)
        if now - cached_time < PRICE_CACHE_TTL and tid in _price_cache:
            result[tid] = _price_cache[tid]
        else:
            to_fetch.append(tid)

    if not to_fetch:
        return result

    # Batch in groups of BATCH_SIZE
    async with httpx.AsyncClient(timeout=15.0) as client:
        for i in range(0, len(to_fetch), BATCH_SIZE):
            batch = to_fetch[i : i + BATCH_SIZE]
            types_param = ",".join(str(t) for t in batch)
            try:
                resp = await client.get(
                    FUZZWORK_URL,
                    params={
                        "station": JITA_STATION_ID,
                        "types": types_param,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as exc:
                logger.error("Fuzzwork price fetch failed: %s", exc)
                continue

            for tid in batch:
                tid_str = str(tid)
                if tid_str in data:
                    buy_max = float(data[tid_str]["buy"]["max"])
                    sell_min = float(data[tid_str]["sell"]["min"])
                    result[tid] = (buy_max, sell_min)
                    _price_cache[tid] = (buy_max, sell_min)
                    _price_cache_time[tid] = now

    return result


async def appraise(raw_text: str) -> AppraisalResponse:
    """Appraise pasted EVE items with Jita market prices.

    Parses the text, resolves item names to type IDs, fetches prices,
    and returns a full appraisal response sorted by sell value descending.

    Args:
        raw_text: Raw pasted text from EVE Online.

    Returns:
        AppraisalResponse with priced items and totals.
    """
    parsed = parse_items(raw_text)
    if not parsed:
        return AppraisalResponse()

    # Aggregate duplicate items
    aggregated: dict[str, int] = defaultdict(int)
    for name, qty in parsed:
        aggregated[name] += qty

    unique_names = list(aggregated.keys())
    name_to_id = await resolve_names(unique_names)

    # Split resolved vs unknown
    resolved_names = [n for n in unique_names if n in name_to_id]
    unknown_items = [n for n in unique_names if n not in name_to_id]

    if unknown_items:
        logger.warning("Could not resolve items: %s", unknown_items)

    # Fetch prices
    type_ids = [name_to_id[n] for n in resolved_names]
    prices = await get_jita_prices(type_ids) if type_ids else {}

    # Build items
    items: list[AppraisalItem] = []
    for name in resolved_names:
        tid = name_to_id[name]
        qty = aggregated[name]
        buy_price, sell_price = prices.get(tid, (0.0, 0.0))
        items.append(
            AppraisalItem(
                name=name,
                type_id=tid,
                quantity=qty,
                buy_price=buy_price,
                sell_price=sell_price,
                buy_total=buy_price * qty,
                sell_total=sell_price * qty,
            )
        )

    # Sort by sell_total descending
    items.sort(key=lambda x: x.sell_total, reverse=True)

    total_buy = sum(i.buy_total for i in items)
    total_sell = sum(i.sell_total for i in items)

    return AppraisalResponse(
        items=items,
        total_buy=total_buy,
        total_sell=total_sell,
        unknown_items=unknown_items,
        item_count=len(items),
    )
