"""External links API v1 endpoints.

Provides endpoints for generating links to external EVE tools.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from ...services.external_links import (
    get_alliance_links,
    get_character_links,
    get_corporation_links,
    get_route_links,
    get_ship_links,
    get_system_links,
)

router = APIRouter(prefix="/links", tags=["links"])


# =============================================================================
# Response Models
# =============================================================================


class SystemLinksResponse(BaseModel):
    """Response with links for a system."""

    system_name: str
    system_id: int | None
    links: dict[str, str]


class CharacterLinksResponse(BaseModel):
    """Response with links for a character."""

    character_id: int
    links: dict[str, str]


class CorporationLinksResponse(BaseModel):
    """Response with links for a corporation."""

    corporation_id: int
    links: dict[str, str]


class AllianceLinksResponse(BaseModel):
    """Response with links for an alliance."""

    alliance_id: int
    links: dict[str, str]


class RouteLinksResponse(BaseModel):
    """Response with links for a route."""

    from_system: str
    to_system: str
    links: dict[str, str]


class ShipLinksResponse(BaseModel):
    """Response with links for a ship type."""

    ship_type_id: int
    links: dict[str, str]


class AvailableToolsResponse(BaseModel):
    """Response listing available external tools."""

    tools: list[dict[str, str]]


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/tools",
    response_model=AvailableToolsResponse,
    summary="List available tools",
    description="List all external EVE tools with links.",
)
async def list_available_tools() -> AvailableToolsResponse:
    """
    List available external tools.

    Returns information about each supported external tool.
    """
    tools = [
        {
            "name": "Dotlan",
            "url": "https://evemaps.dotlan.net",
            "description": "EVE Maps - system info, routes, jump planners, sovereignty",
        },
        {
            "name": "zKillboard",
            "url": "https://zkillboard.com",
            "description": "Kill statistics - systems, characters, corporations, alliances",
        },
        {
            "name": "EVE Eye",
            "url": "https://eveeye.com",
            "description": "Mapping tool - wormhole connections, route planning",
        },
        {
            "name": "EVE Who",
            "url": "https://evewho.com",
            "description": "Character/corporation/alliance lookup and history",
        },
        {
            "name": "ESI",
            "url": "https://esi.evetech.net",
            "description": "Official EVE Swagger Interface API",
        },
    ]

    return AvailableToolsResponse(tools=tools)


@router.get(
    "/system/{system_name}",
    response_model=SystemLinksResponse,
    summary="Get system links",
    description="Get external tool links for a system.",
)
async def get_system_external_links(
    system_name: str,
    system_id: int | None = Query(None, description="System ID for ID-based links"),
    region_name: str | None = Query(None, description="Region name"),
    region_id: int | None = Query(None, description="Region ID"),
) -> SystemLinksResponse:
    """
    Get external tool links for a system.

    Provides links to Dotlan, zKillboard, EVE Eye, and ESI.
    Include system_id for more accurate links.
    """
    links = get_system_links(
        system_name=system_name,
        system_id=system_id,
        region_name=region_name,
        region_id=region_id,
    )

    return SystemLinksResponse(
        system_name=system_name,
        system_id=system_id,
        links=links,
    )


@router.get(
    "/character/{character_id}",
    response_model=CharacterLinksResponse,
    summary="Get character links",
    description="Get external tool links for a character.",
)
async def get_character_external_links(character_id: int) -> CharacterLinksResponse:
    """
    Get external tool links for a character.

    Provides links to zKillboard, EVE Who, and ESI.
    """
    links = get_character_links(character_id)

    return CharacterLinksResponse(
        character_id=character_id,
        links=links,
    )


@router.get(
    "/corporation/{corporation_id}",
    response_model=CorporationLinksResponse,
    summary="Get corporation links",
    description="Get external tool links for a corporation.",
)
async def get_corporation_external_links(corporation_id: int) -> CorporationLinksResponse:
    """
    Get external tool links for a corporation.

    Provides links to zKillboard, EVE Who, and ESI.
    """
    links = get_corporation_links(corporation_id)

    return CorporationLinksResponse(
        corporation_id=corporation_id,
        links=links,
    )


@router.get(
    "/alliance/{alliance_id}",
    response_model=AllianceLinksResponse,
    summary="Get alliance links",
    description="Get external tool links for an alliance.",
)
async def get_alliance_external_links(alliance_id: int) -> AllianceLinksResponse:
    """
    Get external tool links for an alliance.

    Provides links to zKillboard, EVE Who, and ESI.
    """
    links = get_alliance_links(alliance_id)

    return AllianceLinksResponse(
        alliance_id=alliance_id,
        links=links,
    )


@router.get(
    "/route",
    response_model=RouteLinksResponse,
    summary="Get route links",
    description="Get external tool links for a route.",
)
async def get_route_external_links(
    from_system: str = Query(..., alias="from", description="Origin system"),
    to_system: str = Query(..., alias="to", description="Destination system"),
    path: list[str] | None = Query(None, description="Full route path"),
) -> RouteLinksResponse:
    """
    Get external tool links for a route.

    Provides links to Dotlan and EVE Eye route planners.
    Include full path for detailed route links.
    """
    links = get_route_links(
        from_system=from_system,
        to_system=to_system,
        full_path=path,
    )

    return RouteLinksResponse(
        from_system=from_system,
        to_system=to_system,
        links=links,
    )


@router.get(
    "/ship/{ship_type_id}",
    response_model=ShipLinksResponse,
    summary="Get ship type links",
    description="Get external tool links for a ship type.",
)
async def get_ship_external_links(ship_type_id: int) -> ShipLinksResponse:
    """
    Get external tool links for a ship type.

    Provides links to zKillboard and ESI.
    """
    links = get_ship_links(ship_type_id)

    return ShipLinksResponse(
        ship_type_id=ship_type_id,
        links=links,
    )
