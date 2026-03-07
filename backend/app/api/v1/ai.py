"""AI route analysis API v1 endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from ...models.ai import (
    DangerThresholdsResponse,
    RouteAnalysisRequest,
    RouteAnalysisResponse,
)
from ...services.ai_analyzer import analyze_route, get_danger_thresholds
from .dependencies import AuthenticatedCharacter, require_pro

router = APIRouter()


@router.post(
    "/analyze-route",
    response_model=RouteAnalysisResponse,
    summary="Analyze route with AI-powered danger assessment",
    description="Analyzes a route and provides human-readable danger assessment, "
    "warnings for dangerous systems, and alternative route suggestions.",
)
def analyze_route_endpoint(
    request: RouteAnalysisRequest,
    _character: AuthenticatedCharacter = Depends(require_pro),
) -> RouteAnalysisResponse:
    """
    Analyze a route with AI-powered danger assessment.

    This endpoint provides:
    - **Overall danger level**: Worst-case danger along the route
    - **Human-readable assessment**: Plain English description of route risk
    - **System warnings**: Specific warnings for dangerous systems on the path
    - **Alternative routes**: Safer alternatives when dangerous systems detected

    Danger levels are based on recent kill activity (kills + pod kills in 24h):
    - **low**: < 5 kills
    - **medium**: 5-9 kills
    - **high**: 10-19 kills
    - **extreme**: 20+ kills
    """
    try:
        return analyze_route(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/thresholds",
    response_model=DangerThresholdsResponse,
    summary="Get danger threshold configuration",
    description="Returns the current danger threshold values used for classification.",
)
def get_thresholds() -> DangerThresholdsResponse:
    """
    Get current danger threshold configuration.

    Returns the kill count thresholds used to classify systems as
    medium, high, or extreme danger.
    """
    return get_danger_thresholds()
