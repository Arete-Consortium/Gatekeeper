"""Market ticker API v1 endpoints.

Provides real-time market price data for commonly traded EVE Online items
across the 5 major trade hub regions.
"""

import logging

from fastapi import APIRouter, HTTPException

from ...models.market_ticker import MarketTickerHistoryResponse, MarketTickerResponse
from ...services.market_ticker import TRACKED_ITEMS, get_item_history, get_market_ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


@router.get(
    "/ticker",
    response_model=MarketTickerResponse,
    summary="Get market ticker",
    description="Returns latest prices for all tracked items across major trade hub regions.",
)
async def market_ticker() -> MarketTickerResponse:
    """Get the market ticker with latest prices for tracked items."""
    try:
        return await get_market_ticker()
    except Exception as exc:
        logger.exception("Market ticker fetch failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Market ticker unavailable. Please try again."
        ) from exc


@router.get(
    "/ticker/{type_id}",
    response_model=MarketTickerHistoryResponse,
    summary="Get item market history",
    description="Returns market history for a specific item across all trade hub regions.",
)
async def item_ticker(type_id: int) -> MarketTickerHistoryResponse:
    """Get market history for a specific item.

    Args:
        type_id: EVE type ID to look up.
    """
    if type_id not in TRACKED_ITEMS:
        raise HTTPException(
            status_code=404,
            detail=f"Item {type_id} is not in the tracked items list.",
        )

    try:
        return await get_item_history(type_id)
    except Exception as exc:
        logger.exception("Market ticker item fetch failed: %s", exc)
        raise HTTPException(
            status_code=500, detail="Market data unavailable. Please try again."
        ) from exc
