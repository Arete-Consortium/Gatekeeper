"""Fitting API v1 endpoints.

Provides endpoints for parsing ship fittings and travel analysis.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...services.fitting import (
    ParsedFitting,
    ShipCategory,
    TravelRecommendation,
    get_ship_info,
    get_travel_recommendation,
    list_jump_capable_ships,
    list_ships_by_category,
    parse_eft_fitting,
)

router = APIRouter(prefix="/fitting", tags=["fitting"])


# =============================================================================
# Request/Response Models
# =============================================================================


class ParseFittingRequest(BaseModel):
    """Request to parse a fitting."""

    eft_text: str = Field(..., description="EFT format fitting text")


class ParsedFittingResponse(BaseModel):
    """Response with parsed fitting data."""

    ship_name: str
    ship_category: str
    jump_capability: str
    modules: list[str]
    cargo: list[str]
    drones: list[str]
    charges: list[str]
    is_covert_capable: bool
    is_cloak_capable: bool
    has_warp_stabs: bool
    is_bubble_immune: bool
    has_align_mods: bool
    has_warp_speed_mods: bool

    @classmethod
    def from_fitting(cls, fit: ParsedFitting) -> "ParsedFittingResponse":
        return cls(
            ship_name=fit.ship_name,
            ship_category=fit.ship_category.value,
            jump_capability=fit.jump_capability.value,
            modules=fit.modules,
            cargo=fit.cargo,
            drones=fit.drones,
            charges=fit.charges,
            is_covert_capable=fit.is_covert_capable,
            is_cloak_capable=fit.is_cloak_capable,
            has_warp_stabs=fit.has_warp_stabs,
            is_bubble_immune=fit.is_bubble_immune,
            has_align_mods=fit.has_align_mods,
            has_warp_speed_mods=fit.has_warp_speed_mods,
        )


class TravelRecommendationResponse(BaseModel):
    """Response with travel recommendation."""

    ship_name: str
    category: str
    can_use_gates: bool
    can_use_jump_bridges: bool
    can_jump: bool
    can_bridge_others: bool
    can_covert_bridge: bool
    recommended_profile: str
    warnings: list[str]
    tips: list[str]

    @classmethod
    def from_recommendation(cls, rec: TravelRecommendation) -> "TravelRecommendationResponse":
        return cls(
            ship_name=rec.ship_name,
            category=rec.category.value,
            can_use_gates=rec.can_use_gates,
            can_use_jump_bridges=rec.can_use_jump_bridges,
            can_jump=rec.can_jump,
            can_bridge_others=rec.can_bridge_others,
            can_covert_bridge=rec.can_covert_bridge,
            recommended_profile=rec.recommended_profile,
            warnings=rec.warnings,
            tips=rec.tips,
        )


class AnalyzeFittingResponse(BaseModel):
    """Response with fitting analysis and travel recommendation."""

    fitting: ParsedFittingResponse
    travel: TravelRecommendationResponse


class ShipInfoResponse(BaseModel):
    """Response with ship info."""

    name: str
    category: str
    jump_capability: str


class ShipListResponse(BaseModel):
    """Response listing ships."""

    total: int
    ships: list[str]


class CategoryListResponse(BaseModel):
    """Response listing categories."""

    categories: list[str]


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/parse",
    response_model=ParsedFittingResponse,
    summary="Parse EFT fitting",
    description="Parse an EFT format fitting and extract components.",
)
async def parse_fitting(request: ParseFittingRequest) -> ParsedFittingResponse:
    """
    Parse an EFT format fitting.

    EFT format starts with [ShipName, FitName] followed by modules.
    """
    fitting = parse_eft_fitting(request.eft_text)
    if not fitting:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse fitting. Ensure it's in valid EFT format.",
        )
    return ParsedFittingResponse.from_fitting(fitting)


@router.post(
    "/analyze",
    response_model=AnalyzeFittingResponse,
    summary="Analyze fitting for travel",
    description="Parse fitting and get travel recommendations.",
)
async def analyze_fitting(request: ParseFittingRequest) -> AnalyzeFittingResponse:
    """
    Parse a fitting and provide travel recommendations.

    Analyzes the ship type and modules to recommend routing profiles
    and provide travel safety tips.
    """
    fitting = parse_eft_fitting(request.eft_text)
    if not fitting:
        raise HTTPException(
            status_code=400,
            detail="Failed to parse fitting. Ensure it's in valid EFT format.",
        )

    recommendation = get_travel_recommendation(fitting)

    return AnalyzeFittingResponse(
        fitting=ParsedFittingResponse.from_fitting(fitting),
        travel=TravelRecommendationResponse.from_recommendation(recommendation),
    )


@router.get(
    "/ship/{ship_name}",
    response_model=ShipInfoResponse,
    summary="Get ship info",
    description="Get information about a ship type.",
)
async def get_ship(ship_name: str) -> ShipInfoResponse:
    """Get ship category and jump capability."""
    info = get_ship_info(ship_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Ship not found: {ship_name}")

    return ShipInfoResponse(
        name=ship_name,
        category=info["category"].value,
        jump_capability=info["jump"].value,
    )


@router.get(
    "/ships/jump-capable",
    response_model=ShipListResponse,
    summary="List jump-capable ships",
    description="List all ships with jump drive capability.",
)
async def list_jump_ships() -> ShipListResponse:
    """List all ships that can jump."""
    ships = list_jump_capable_ships()
    return ShipListResponse(total=len(ships), ships=sorted(ships))


@router.get(
    "/ships/category/{category}",
    response_model=ShipListResponse,
    summary="List ships by category",
    description="List all ships in a category.",
)
async def list_ships_in_category(category: str) -> ShipListResponse:
    """List all ships in a category."""
    try:
        cat = ShipCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {category}. Valid: {[c.value for c in ShipCategory]}",
        ) from None

    ships = list_ships_by_category(cat)
    return ShipListResponse(total=len(ships), ships=sorted(ships))


@router.get(
    "/categories",
    response_model=CategoryListResponse,
    summary="List ship categories",
    description="List all ship categories.",
)
async def list_categories() -> CategoryListResponse:
    """List all ship categories."""
    return CategoryListResponse(categories=[c.value for c in ShipCategory])
