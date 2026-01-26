"""ESI endpoint wrappers with caching.

These functions provide high-level access to ESI endpoints
with automatic caching and error handling.
"""

from typing import Any, cast

from .cache import ESICache
from .client import ESIClient


async def get_system_kills(
    client: ESIClient,
    cache: ESICache | None = None,
) -> dict[int, dict[str, int]]:
    """Get system kill statistics.

    ESI: GET /universe/system_kills/
    TTL: 300 seconds (5 minutes)

    Returns:
        Dict mapping system_id to kill counts:
        {system_id: {"ship_kills": N, "npc_kills": N, "pod_kills": N}}
    """
    cache_key = "system_kills"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:  # Not expired
            return cast(dict[int, dict[str, int]], cached[0])

    data, headers = await client.get("/universe/system_kills/")

    # Transform to dict keyed by system_id
    result = {
        entry["system_id"]: {
            "ship_kills": entry.get("ship_kills", 0),
            "npc_kills": entry.get("npc_kills", 0),
            "pod_kills": entry.get("pod_kills", 0),
        }
        for entry in data
    }

    if cache:
        await cache.set(cache_key, "system_kills", result, etag=headers.get("etag"))

    return result


async def get_system_jumps(
    client: ESIClient,
    cache: ESICache | None = None,
) -> dict[int, int]:
    """Get system jump statistics.

    ESI: GET /universe/system_jumps/
    TTL: 300 seconds (5 minutes)

    Returns:
        Dict mapping system_id to jump count
    """
    cache_key = "system_jumps"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(dict[int, int], cached[0])

    data, headers = await client.get("/universe/system_jumps/")

    result = {entry["system_id"]: entry["ship_jumps"] for entry in data}

    if cache:
        await cache.set(cache_key, "system_jumps", result, etag=headers.get("etag"))

    return result


async def get_incursions(
    client: ESIClient,
    cache: ESICache | None = None,
) -> list[dict[str, Any]]:
    """Get active incursions.

    ESI: GET /incursions/
    TTL: 600 seconds (10 minutes)

    Returns:
        List of incursion data
    """
    cache_key = "incursions"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(list[dict[str, Any]], cached[0])

    data, headers = await client.get("/incursions/")

    if cache:
        await cache.set(cache_key, "incursions", data, etag=headers.get("etag"))

    return cast(list[dict[str, Any]], data)


async def get_sovereignty_map(
    client: ESIClient,
    cache: ESICache | None = None,
) -> dict[int, dict[str, Any]]:
    """Get sovereignty map.

    ESI: GET /sovereignty/map/
    TTL: 3600 seconds (1 hour)

    Returns:
        Dict mapping system_id to sovereignty data
    """
    cache_key = "sovereignty_map"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(dict[int, dict[str, Any]], cached[0])

    data, headers = await client.get("/sovereignty/map/")

    result = {
        entry["system_id"]: {
            "alliance_id": entry.get("alliance_id"),
            "corporation_id": entry.get("corporation_id"),
            "faction_id": entry.get("faction_id"),
        }
        for entry in data
    }

    if cache:
        await cache.set(cache_key, "sovereignty_map", result, etag=headers.get("etag"))

    return result


async def get_sovereignty_campaigns(
    client: ESIClient,
    cache: ESICache | None = None,
) -> list[dict[str, Any]]:
    """Get active sovereignty campaigns.

    ESI: GET /sovereignty/campaigns/
    TTL: 300 seconds (5 minutes)

    Returns:
        List of active campaigns
    """
    cache_key = "sovereignty_campaigns"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(list[dict[str, Any]], cached[0])

    data, headers = await client.get("/sovereignty/campaigns/")

    if cache:
        await cache.set(cache_key, "sovereignty_campaigns", data, etag=headers.get("etag"))

    return cast(list[dict[str, Any]], data)


async def get_route(
    client: ESIClient,
    origin: int,
    destination: int,
    flag: str = "shortest",
    avoid: list[int] | None = None,
    connections: list[tuple[int, int]] | None = None,
    cache: ESICache | None = None,
) -> list[int]:
    """Get route between two systems using ESI.

    ESI: GET /route/{origin}/{destination}/
    Note: No caching by default as routes are user-specific

    Args:
        client: ESI client
        origin: Origin system ID
        destination: Destination system ID
        flag: Route preference ('shortest', 'secure', 'insecure')
        avoid: List of system IDs to avoid
        connections: List of (from, to) pairs for additional connections

    Returns:
        List of system IDs forming the route
    """
    params: dict[str, Any] = {"flag": flag}

    if avoid:
        params["avoid"] = avoid
    if connections:
        params["connections"] = [f"{a}|{b}" for a, b in connections]

    data, _ = await client.get(f"/route/{origin}/{destination}/", params=params)

    return cast(list[int], data)


# ============================================================================
# Authenticated Endpoints
# ============================================================================


async def get_character_location(
    client: ESIClient,
    character_id: int,
) -> dict[str, Any]:
    """Get character's current location.

    ESI: GET /characters/{character_id}/location/
    Scope: esi-location.read_location.v1

    Returns:
        Location data including solar_system_id, station_id, structure_id
    """
    data, _ = await client.get(
        f"/characters/{character_id}/location/",
        authenticated=True,
    )
    return cast(dict[str, Any], data)


async def get_character_online(
    client: ESIClient,
    character_id: int,
) -> dict[str, Any]:
    """Get character's online status.

    ESI: GET /characters/{character_id}/online/
    Scope: esi-location.read_online.v1

    Returns:
        Online status data
    """
    data, _ = await client.get(
        f"/characters/{character_id}/online/",
        authenticated=True,
    )
    return cast(dict[str, Any], data)


async def set_waypoint(
    client: ESIClient,
    destination_id: int,
    add_to_beginning: bool = False,
    clear_other_waypoints: bool = False,
) -> bool:
    """Set an in-game autopilot waypoint.

    ESI: POST /ui/autopilot/waypoint/
    Scope: esi-ui.write_waypoint.v1

    Args:
        destination_id: The destination to set (system, station, or structure)
        add_to_beginning: Add to beginning of route instead of end
        clear_other_waypoints: Clear existing waypoints

    Returns:
        True if successful
    """
    # Note: This is a POST endpoint, would need to be implemented differently
    # For now, return True as placeholder
    return True


async def get_character_assets(
    client: ESIClient,
    character_id: int,
    cache: ESICache | None = None,
) -> list[dict[str, Any]]:
    """Get character's assets.

    ESI: GET /characters/{character_id}/assets/
    Scope: esi-assets.read_assets.v1

    Returns:
        List of all character assets
    """
    cache_key = f"character_assets_{character_id}"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(list[dict[str, Any]], cached[0])

    data = await client.get_paginated(
        f"/characters/{character_id}/assets/",
        authenticated=True,
    )

    if cache:
        await cache.set(cache_key, "character_assets", data, ttl=300)

    return cast(list[dict[str, Any]], data)


async def get_character_standings(
    client: ESIClient,
    character_id: int,
    cache: ESICache | None = None,
) -> list[dict[str, Any]]:
    """Get character's standings.

    ESI: GET /characters/{character_id}/standings/
    Scope: esi-characters.read_standings.v1

    Returns:
        List of standings with factions, corporations, agents
    """
    cache_key = f"character_standings_{character_id}"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(list[dict[str, Any]], cached[0])

    data, _ = await client.get(
        f"/characters/{character_id}/standings/",
        authenticated=True,
    )

    if cache:
        await cache.set(cache_key, "character_standings", data, ttl=3600)

    return cast(list[dict[str, Any]], data)


# ============================================================================
# Universe Data Endpoints
# ============================================================================


async def get_type_info(
    client: ESIClient,
    type_id: int,
    cache: ESICache | None = None,
) -> dict[str, Any]:
    """Get type information (for ship attributes, etc.).

    ESI: GET /universe/types/{type_id}/
    TTL: 604800 seconds (1 week)

    Returns:
        Type data including dogma_attributes
    """
    cache_key = f"type_{type_id}"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(dict[str, Any], cached[0])

    data, headers = await client.get(f"/universe/types/{type_id}/")

    if cache:
        await cache.set(
            cache_key,
            "universe_types",
            data,
            ttl=604800,
            etag=headers.get("etag"),
        )

    return cast(dict[str, Any], data)


async def search_universe(
    client: ESIClient,
    search: str,
    categories: list[str] | None = None,
    strict: bool = False,
) -> dict[str, list[int]]:
    """Search the EVE universe.

    ESI: GET /search/
    No caching - search is dynamic

    Args:
        search: Search string
        categories: Categories to search (solar_system, region, etc.)
        strict: Exact match only

    Returns:
        Dict of category -> list of IDs
    """
    if categories is None:
        categories = ["solar_system", "region", "constellation"]

    params = {
        "search": search,
        "categories": ",".join(categories),
        "strict": str(strict).lower(),
    }

    data, _ = await client.get("/search/", params=params)
    return cast(dict[str, list[int]], data)


# ============================================================================
# Structure Endpoints
# ============================================================================

# Ansiblex Jump Gate type ID
ANSIBLEX_TYPE_ID = 35841


async def get_structure_info(
    client: ESIClient,
    structure_id: int,
    cache: ESICache | None = None,
) -> dict[str, Any]:
    """Get public information about a structure.

    ESI: GET /universe/structures/{structure_id}/
    Scope: esi-universe.read_structures.v1 (for private structures)

    Note: Public structures (e.g., Ansiblex) may be accessible without auth.

    Args:
        structure_id: The structure ID to look up

    Returns:
        Structure info including name, type_id, solar_system_id
    """
    cache_key = f"structure_{structure_id}"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(dict[str, Any], cached[0])

    try:
        data, headers = await client.get(
            f"/universe/structures/{structure_id}/",
            authenticated=True,  # Usually requires auth
        )

        if cache:
            await cache.set(
                cache_key,
                "universe_structures",
                data,
                ttl=3600,  # 1 hour cache
                etag=headers.get("etag"),
            )

        return cast(dict[str, Any], data)
    except Exception:
        # Structure not accessible (forbidden or not found)
        return {}


async def get_corporation_structures(
    client: ESIClient,
    corporation_id: int,
    cache: ESICache | None = None,
) -> list[dict[str, Any]]:
    """Get corporation's structures.

    ESI: GET /corporations/{corporation_id}/structures/
    Scope: esi-corporations.read_structures.v1

    Note: Requires character to be a director of the corporation.

    Returns:
        List of corporation structures including Ansiblex jump gates
    """
    cache_key = f"corp_structures_{corporation_id}"

    if cache:
        cached = await cache.get(cache_key)
        if cached and not cached[1]:
            return cast(list[dict[str, Any]], cached[0])

    try:
        data = await client.get_paginated(
            f"/corporations/{corporation_id}/structures/",
            authenticated=True,
        )

        if cache:
            await cache.set(cache_key, "corp_structures", data, ttl=300)

        return cast(list[dict[str, Any]], data)
    except Exception:
        return []


async def get_alliance_structures(
    client: ESIClient,
    alliance_id: int,
    corporation_ids: list[int],
    cache: ESICache | None = None,
) -> list[dict[str, Any]]:
    """Get all structures from alliance corporations.

    This aggregates structures from multiple corporations in an alliance.
    Requires director access to each corporation.

    Args:
        alliance_id: The alliance ID (for cache key)
        corporation_ids: List of corporation IDs to query

    Returns:
        Combined list of structures from all corporations
    """
    all_structures: list[dict[str, Any]] = []

    for corp_id in corporation_ids:
        structures = await get_corporation_structures(client, corp_id, cache)
        all_structures.extend(structures)

    return all_structures


def filter_ansiblex_structures(
    structures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Filter structures to only include Ansiblex jump gates.

    Args:
        structures: List of structure data from ESI

    Returns:
        Only structures with type_id == 35841 (Ansiblex)
    """
    return [s for s in structures if s.get("type_id") == ANSIBLEX_TYPE_ID]
