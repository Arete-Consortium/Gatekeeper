"""Market arbitrage API v1 endpoints.

Provides endpoints for comparing market prices across EVE trade hubs
and identifying profitable arbitrage opportunities.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from ...models.arbitrage import ArbitrageCompareResponse, PopularItemsResponse
from ...services.arbitrage import compare_hubs, get_popular_items

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arbitrage", tags=["arbitrage"])


@router.get(
    "/compare",
    response_model=ArbitrageCompareResponse,
    summary="Compare prices across trade hubs",
    description=(
        "Fetches live market orders from ESI for each trade hub, "
        "compares buy/sell prices, and identifies arbitrage opportunities."
    ),
)
async def arbitrage_compare(
    type_id: int = Query(..., description="EVE type ID to compare"),
    hubs: str | None = Query(
        None,
        description=(
            "Comma-separated hub system IDs to compare. "
            "Defaults to all 5 major hubs (Jita, Amarr, Dodixie, Rens, Hek)."
        ),
    ),
) -> ArbitrageCompareResponse:
    """Compare market prices for an item across trade hubs.

    Args:
        type_id: EVE item type ID.
        hubs: Optional comma-separated hub system IDs.
    """
    if type_id <= 0:
        raise HTTPException(status_code=400, detail="type_id must be a positive integer.")

    hub_ids: list[int] | None = None
    if hubs:
        try:
            hub_ids = [int(h.strip()) for h in hubs.split(",") if h.strip()]
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="hubs must be comma-separated integers.",
            ) from exc

    try:
        return await compare_hubs(type_id, hub_ids)
    except Exception as exc:
        logger.exception("Arbitrage compare failed for type_id=%d: %s", type_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Arbitrage comparison failed. Please try again.",
        ) from exc


@router.get(
    "/popular",
    response_model=PopularItemsResponse,
    summary="Get popular traded items",
    description="Returns a curated list of commonly traded items for quick arbitrage lookup.",
)
async def popular_items() -> PopularItemsResponse:
    """Get list of commonly traded items."""
    try:
        return await get_popular_items()
    except Exception as exc:
        logger.exception("Popular items fetch failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Could not fetch popular items.",
        ) from exc
