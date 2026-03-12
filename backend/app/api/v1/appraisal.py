"""Appraisal API v1 endpoints.

Provides an endpoint for appraising EVE Online items with Jita market prices.
"""

import logging

from fastapi import APIRouter, HTTPException

from ...models.appraisal import AppraisalRequest, AppraisalResponse
from ...services.appraisal import appraise

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appraisal", tags=["appraisal"])


@router.post(
    "",
    response_model=AppraisalResponse,
    summary="Appraise EVE items",
    description="Parse pasted EVE items and return Jita market prices.",
)
async def appraise_items(request: AppraisalRequest) -> AppraisalResponse:
    """Appraise pasted EVE Online items.

    Accepts raw text (inventory copy, manual entry, etc.) and returns
    Jita 4-4 buy/sell prices for each resolved item.
    """
    if not request.raw_text.strip():
        raise HTTPException(status_code=400, detail="Empty appraisal text.")

    try:
        return await appraise(request.raw_text)
    except Exception as exc:
        logger.exception("Appraisal failed: %s", exc)
        raise HTTPException(status_code=500, detail="Appraisal failed. Please try again.") from exc
