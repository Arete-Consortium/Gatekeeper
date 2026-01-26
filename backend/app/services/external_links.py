"""External links service for generating URLs to EVE tools.

Generates links to popular EVE Online tools:
- Dotlan (maps, routes, statistics)
- zKillboard (kill statistics)
- EVE Eye (mapping)
- EVE Who (character lookup)
- ESI (official API)
"""

from urllib.parse import quote

# =============================================================================
# Dotlan Links
# =============================================================================


def dotlan_system_url(system_name: str) -> str:
    """Generate Dotlan system page URL."""
    return f"https://evemaps.dotlan.net/system/{quote(system_name)}"


def dotlan_region_url(region_name: str) -> str:
    """Generate Dotlan region page URL."""
    return f"https://evemaps.dotlan.net/map/{quote(region_name)}"


def dotlan_route_url(systems: list[str]) -> str:
    """Generate Dotlan route URL from list of systems."""
    if not systems:
        return "https://evemaps.dotlan.net/route"
    route_str = ":".join(quote(s) for s in systems)
    return f"https://evemaps.dotlan.net/route/{route_str}"


def dotlan_route_from_to_url(from_system: str, to_system: str) -> str:
    """Generate Dotlan route URL from origin to destination."""
    return f"https://evemaps.dotlan.net/route/{quote(from_system)}:{quote(to_system)}"


def dotlan_jump_url(systems: list[str]) -> str:
    """Generate Dotlan capital jump planner URL."""
    if not systems:
        return "https://evemaps.dotlan.net/jump"
    route_str = ":".join(quote(s) for s in systems)
    return f"https://evemaps.dotlan.net/jump/Anshar,544/{route_str}"


def dotlan_radar_url(system_name: str) -> str:
    """Generate Dotlan radar page URL (kills/jumps/ships)."""
    return f"https://evemaps.dotlan.net/system/{quote(system_name)}/radar"


# =============================================================================
# zKillboard Links
# =============================================================================


def zkillboard_system_url(system_id: int) -> str:
    """Generate zKillboard system page URL."""
    return f"https://zkillboard.com/system/{system_id}/"


def zkillboard_system_url_by_name(system_name: str) -> str:
    """Generate zKillboard system search URL by name."""
    return f"https://zkillboard.com/search/{quote(system_name)}/"


def zkillboard_character_url(character_id: int) -> str:
    """Generate zKillboard character page URL."""
    return f"https://zkillboard.com/character/{character_id}/"


def zkillboard_corporation_url(corporation_id: int) -> str:
    """Generate zKillboard corporation page URL."""
    return f"https://zkillboard.com/corporation/{corporation_id}/"


def zkillboard_alliance_url(alliance_id: int) -> str:
    """Generate zKillboard alliance page URL."""
    return f"https://zkillboard.com/alliance/{alliance_id}/"


def zkillboard_region_url(region_id: int) -> str:
    """Generate zKillboard region page URL."""
    return f"https://zkillboard.com/region/{region_id}/"


def zkillboard_ship_url(ship_type_id: int) -> str:
    """Generate zKillboard ship type page URL."""
    return f"https://zkillboard.com/ship/{ship_type_id}/"


# =============================================================================
# EVE Eye Links
# =============================================================================


def eveeye_system_url(system_name: str) -> str:
    """Generate EVE Eye system page URL."""
    return f"https://eveeye.com/?system={quote(system_name)}"


def eveeye_route_url(from_system: str, to_system: str) -> str:
    """Generate EVE Eye route URL."""
    return f"https://eveeye.com/?route={quote(from_system)}:{quote(to_system)}"


def eveeye_map_url(region_name: str) -> str:
    """Generate EVE Eye map URL."""
    return f"https://eveeye.com/?map={quote(region_name)}"


# =============================================================================
# EVE Who Links
# =============================================================================


def evewho_character_url(character_id: int) -> str:
    """Generate EVE Who character page URL."""
    return f"https://evewho.com/character/{character_id}"


def evewho_corporation_url(corporation_id: int) -> str:
    """Generate EVE Who corporation page URL."""
    return f"https://evewho.com/corporation/{corporation_id}"


def evewho_alliance_url(alliance_id: int) -> str:
    """Generate EVE Who alliance page URL."""
    return f"https://evewho.com/alliance/{alliance_id}"


# =============================================================================
# ESI (Official API) Links
# =============================================================================


def esi_system_url(system_id: int) -> str:
    """Generate ESI system info URL."""
    return f"https://esi.evetech.net/latest/universe/systems/{system_id}/"


def esi_character_url(character_id: int) -> str:
    """Generate ESI character public info URL."""
    return f"https://esi.evetech.net/latest/characters/{character_id}/"


def esi_corporation_url(corporation_id: int) -> str:
    """Generate ESI corporation public info URL."""
    return f"https://esi.evetech.net/latest/corporations/{corporation_id}/"


def esi_alliance_url(alliance_id: int) -> str:
    """Generate ESI alliance public info URL."""
    return f"https://esi.evetech.net/latest/alliances/{alliance_id}/"


def esi_type_url(type_id: int) -> str:
    """Generate ESI type info URL."""
    return f"https://esi.evetech.net/latest/universe/types/{type_id}/"


# =============================================================================
# Aggregated Link Generators
# =============================================================================


def get_system_links(
    system_name: str,
    system_id: int | None = None,
    region_name: str | None = None,
    region_id: int | None = None,
) -> dict[str, str]:
    """
    Generate all available links for a system.

    Args:
        system_name: System name
        system_id: Optional system ID for ID-based links
        region_name: Optional region name
        region_id: Optional region ID

    Returns:
        Dict of link names to URLs
    """
    links = {
        "dotlan": dotlan_system_url(system_name),
        "dotlan_radar": dotlan_radar_url(system_name),
        "eveeye": eveeye_system_url(system_name),
    }

    if system_id:
        links["zkillboard"] = zkillboard_system_url(system_id)
        links["esi"] = esi_system_url(system_id)
    else:
        links["zkillboard_search"] = zkillboard_system_url_by_name(system_name)

    if region_name:
        links["dotlan_region"] = dotlan_region_url(region_name)
        links["eveeye_map"] = eveeye_map_url(region_name)

    if region_id:
        links["zkillboard_region"] = zkillboard_region_url(region_id)

    return links


def get_character_links(character_id: int) -> dict[str, str]:
    """
    Generate all available links for a character.

    Args:
        character_id: Character ID

    Returns:
        Dict of link names to URLs
    """
    return {
        "zkillboard": zkillboard_character_url(character_id),
        "evewho": evewho_character_url(character_id),
        "esi": esi_character_url(character_id),
    }


def get_corporation_links(corporation_id: int) -> dict[str, str]:
    """
    Generate all available links for a corporation.

    Args:
        corporation_id: Corporation ID

    Returns:
        Dict of link names to URLs
    """
    return {
        "zkillboard": zkillboard_corporation_url(corporation_id),
        "evewho": evewho_corporation_url(corporation_id),
        "esi": esi_corporation_url(corporation_id),
    }


def get_alliance_links(alliance_id: int) -> dict[str, str]:
    """
    Generate all available links for an alliance.

    Args:
        alliance_id: Alliance ID

    Returns:
        Dict of link names to URLs
    """
    return {
        "zkillboard": zkillboard_alliance_url(alliance_id),
        "evewho": evewho_alliance_url(alliance_id),
        "esi": esi_alliance_url(alliance_id),
    }


def get_route_links(
    from_system: str,
    to_system: str,
    full_path: list[str] | None = None,
) -> dict[str, str]:
    """
    Generate all available links for a route.

    Args:
        from_system: Origin system
        to_system: Destination system
        full_path: Optional full path for detailed route links

    Returns:
        Dict of link names to URLs
    """
    links = {
        "dotlan": dotlan_route_from_to_url(from_system, to_system),
        "eveeye": eveeye_route_url(from_system, to_system),
    }

    if full_path and len(full_path) >= 2:
        links["dotlan_full"] = dotlan_route_url(full_path)
        links["dotlan_jump"] = dotlan_jump_url(full_path)

    return links


def get_ship_links(ship_type_id: int) -> dict[str, str]:
    """
    Generate all available links for a ship type.

    Args:
        ship_type_id: Ship type ID

    Returns:
        Dict of link names to URLs
    """
    return {
        "zkillboard": zkillboard_ship_url(ship_type_id),
        "esi": esi_type_url(ship_type_id),
    }
