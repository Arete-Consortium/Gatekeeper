"""Thera wormhole connection API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from ...models.thera import TheraConnectionsResponse, TheraStatusResponse
from ...services.thera import (
    get_active_thera,
    get_thera_cache_age,
    get_thera_last_error,
)

router = APIRouter()


@router.get(
    "/",
    response_model=TheraConnectionsResponse,
    summary="List active Thera connections",
    description="Returns currently active Thera wormhole connections from EVE-Scout.",
)
def list_thera_connections(
    max_ship_size: str | None = Query(
        None, description="Filter by max ship size (e.g. 'frigate', 'battleship')"
    ),
) -> TheraConnectionsResponse:
    """List active Thera wormhole connections."""
    connections = get_active_thera()

    if max_ship_size:
        connections = [c for c in connections if c.max_ship_size == max_ship_size]

    return TheraConnectionsResponse(
        connections=connections,
        total=len(connections),
        last_updated=datetime.now(UTC),
    )


@router.get(
    "/status",
    response_model=TheraStatusResponse,
    summary="Thera cache status",
    description="Returns cache health and EVE-Scout API status.",
)
def thera_status() -> TheraStatusResponse:
    """Check Thera connection cache status."""
    cache_age = get_thera_cache_age()
    last_error = get_thera_last_error()

    return TheraStatusResponse(
        cache_age_seconds=round(cache_age, 1) if cache_age is not None else None,
        connection_count=len(get_active_thera()),
        api_healthy=last_error is None,
        last_error=last_error,
    )
