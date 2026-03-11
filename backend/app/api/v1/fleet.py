"""Fleet composition analysis API v1 endpoints.

Provides endpoints for parsing and analyzing EVE Online fleet compositions.
"""

from fastapi import APIRouter, HTTPException

from ...models.fleet import FleetAnalysisResponse, FleetAnalyzeRequest
from ...services.fleet_analyzer import analyze_fleet

router = APIRouter(prefix="/fleet", tags=["fleet"])


@router.post(
    "/analyze",
    response_model=FleetAnalysisResponse,
    summary="Analyze fleet composition",
    description="Parse a fleet composition and return a threat assessment.",
)
async def analyze_fleet_composition(
    request: FleetAnalyzeRequest,
) -> FleetAnalysisResponse:
    """Analyze a pasted fleet composition for threat assessment.

    Accepts tab-separated (EVE fleet window copy) or multiplied format
    (e.g., '2x Loki'). Returns threat level, composition breakdown,
    and tactical advice.
    """
    try:
        result = analyze_fleet(request.text)
        return FleetAnalysisResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse fleet composition: {exc}",
        ) from exc
