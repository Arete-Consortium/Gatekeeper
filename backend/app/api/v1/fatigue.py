"""Jump fatigue API v1 endpoints.

Provides endpoints for calculating and tracking jump fatigue.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.jump_fatigue import (
    FatigueState,
    JumpFatigueResult,
    RouteFatigueResult,
    calculate_route_fatigue,
    calculate_single_jump_fatigue,
    format_timer,
    get_fatigue_tracker,
)

router = APIRouter(prefix="/fatigue", tags=["fatigue"])


# =============================================================================
# Request/Response Models
# =============================================================================


class FatigueStateResponse(BaseModel):
    """Current fatigue state."""

    character_id: int | None
    character_name: str | None
    blue_timer_seconds: float
    blue_timer_formatted: str
    blue_timer_expires: datetime | None
    red_timer_seconds: float
    red_timer_formatted: str
    red_timer_expires: datetime | None
    can_jump: bool
    time_until_jump_seconds: float
    time_until_clear_seconds: float
    last_updated: datetime

    @classmethod
    def from_state(cls, state: FatigueState) -> "FatigueStateResponse":
        """Create from FatigueState."""
        decayed = state.decay_to_now()
        return cls(
            character_id=decayed.character_id,
            character_name=decayed.character_name,
            blue_timer_seconds=round(decayed.blue_timer_seconds, 1),
            blue_timer_formatted=format_timer(decayed.blue_timer_seconds),
            blue_timer_expires=decayed.blue_timer_expires,
            red_timer_seconds=round(decayed.red_timer_seconds, 1),
            red_timer_formatted=format_timer(decayed.red_timer_seconds),
            red_timer_expires=decayed.red_timer_expires,
            can_jump=decayed.can_jump,
            time_until_jump_seconds=round(decayed.time_until_jump, 1),
            time_until_clear_seconds=round(decayed.time_until_clear, 1),
            last_updated=decayed.last_updated,
        )


class JumpFatigueResponse(BaseModel):
    """Fatigue calculation for a single jump."""

    from_system: str
    to_system: str
    distance_ly: float
    blue_timer_before: float
    red_timer_before: float
    blue_timer_added: float
    red_timer_added: float
    blue_timer_after: float
    blue_timer_after_formatted: str
    red_timer_after: float
    red_timer_after_formatted: str
    wait_time_seconds: float
    wait_time_formatted: str
    fatigue_multiplier: float

    @classmethod
    def from_result(cls, result: JumpFatigueResult) -> "JumpFatigueResponse":
        """Create from JumpFatigueResult."""
        return cls(
            from_system=result.from_system,
            to_system=result.to_system,
            distance_ly=result.distance_ly,
            blue_timer_before=result.blue_timer_before,
            red_timer_before=result.red_timer_before,
            blue_timer_added=result.blue_timer_added,
            red_timer_added=result.red_timer_added,
            blue_timer_after=result.blue_timer_after,
            blue_timer_after_formatted=format_timer(result.blue_timer_after),
            red_timer_after=result.red_timer_after,
            red_timer_after_formatted=format_timer(result.red_timer_after),
            wait_time_seconds=result.wait_time_seconds,
            wait_time_formatted=format_timer(result.wait_time_seconds),
            fatigue_multiplier=result.fatigue_multiplier,
        )


class RouteFatigueResponse(BaseModel):
    """Fatigue calculation for a route."""

    from_system: str
    to_system: str
    total_jumps: int
    total_distance_ly: float
    final_blue_timer: float
    final_blue_timer_formatted: str
    final_red_timer: float
    final_red_timer_formatted: str
    total_wait_time_seconds: float
    total_wait_time_formatted: str
    total_time_seconds: float
    total_time_formatted: str
    legs: list[JumpFatigueResponse]

    @classmethod
    def from_result(cls, result: RouteFatigueResult) -> "RouteFatigueResponse":
        """Create from RouteFatigueResult."""
        return cls(
            from_system=result.from_system,
            to_system=result.to_system,
            total_jumps=result.total_jumps,
            total_distance_ly=result.total_distance_ly,
            final_blue_timer=result.final_blue_timer,
            final_blue_timer_formatted=format_timer(result.final_blue_timer),
            final_red_timer=result.final_red_timer,
            final_red_timer_formatted=format_timer(result.final_red_timer),
            total_wait_time_seconds=result.total_wait_time_seconds,
            total_wait_time_formatted=format_timer(result.total_wait_time_seconds),
            total_time_seconds=result.total_time_seconds,
            total_time_formatted=format_timer(result.total_time_seconds),
            legs=[JumpFatigueResponse.from_result(leg) for leg in result.legs],
        )


class SetFatigueRequest(BaseModel):
    """Request to set fatigue state."""

    blue_timer_seconds: float = Field(..., ge=0, description="Blue timer in seconds")
    red_timer_seconds: float = Field(..., ge=0, description="Red timer in seconds")
    character_name: str | None = Field(None, description="Character name")


class RecordJumpRequest(BaseModel):
    """Request to record a jump."""

    from_system: str = Field(..., description="Origin system")
    to_system: str = Field(..., description="Destination system")


class RouteRequest(BaseModel):
    """Request to calculate route fatigue."""

    waypoints: list[str] = Field(..., min_length=2, description="System names in order")
    character_id: int | None = Field(None, description="Character ID to use current fatigue")
    wait_between_jumps: bool = Field(True, description="Assume waiting for blue timer")


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/calculate",
    response_model=JumpFatigueResponse,
    summary="Calculate jump fatigue",
    description="Calculate fatigue for a single jump without tracking.",
)
async def calculate_jump(
    from_system: str = Query(..., alias="from", description="Origin system"),
    to_system: str = Query(..., alias="to", description="Destination system"),
    blue_timer: float = Query(0, ge=0, description="Current blue timer seconds"),
    red_timer: float = Query(0, ge=0, description="Current red timer seconds"),
) -> JumpFatigueResponse:
    """
    Calculate fatigue for a single jump.

    Doesn't track or store the result - just calculates.
    """
    state = None
    if blue_timer > 0 or red_timer > 0:
        state = FatigueState(
            blue_timer_seconds=blue_timer,
            red_timer_seconds=red_timer,
        )

    try:
        result = calculate_single_jump_fatigue(from_system, to_system, state)
        return JumpFatigueResponse.from_result(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post(
    "/route",
    response_model=RouteFatigueResponse,
    summary="Calculate route fatigue",
    description="Calculate cumulative fatigue for a multi-jump route.",
)
async def calculate_route(request: RouteRequest) -> RouteFatigueResponse:
    """
    Calculate fatigue for a complete route.

    Optionally uses a character's current fatigue state as starting point.
    """
    current_state = None
    if request.character_id:
        tracker = get_fatigue_tracker()
        current_state = tracker.get_state(request.character_id)

    try:
        result = calculate_route_fatigue(
            request.waypoints,
            current_state=current_state,
            wait_between_jumps=request.wait_between_jumps,
        )
        return RouteFatigueResponse.from_result(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/character/{character_id}",
    response_model=FatigueStateResponse,
    summary="Get character fatigue",
    description="Get current fatigue state for a character.",
)
async def get_character_fatigue(character_id: int) -> FatigueStateResponse:
    """
    Get current fatigue state for a character.

    State is automatically decayed to current time.
    """
    tracker = get_fatigue_tracker()
    state = tracker.get_state(character_id)
    return FatigueStateResponse.from_state(state)


@router.put(
    "/character/{character_id}",
    response_model=FatigueStateResponse,
    summary="Set character fatigue",
    description="Set fatigue state for a character (e.g., from ESI or manual entry).",
)
async def set_character_fatigue(
    character_id: int,
    request: SetFatigueRequest,
) -> FatigueStateResponse:
    """
    Set fatigue state for a character.

    Use this to sync with ESI data or manually input current timers.
    """
    tracker = get_fatigue_tracker()
    state = tracker.set_state(
        character_id,
        blue_timer_seconds=request.blue_timer_seconds,
        red_timer_seconds=request.red_timer_seconds,
        character_name=request.character_name,
    )
    return FatigueStateResponse.from_state(state)


@router.post(
    "/character/{character_id}/jump",
    response_model=FatigueStateResponse,
    summary="Record a jump",
    description="Record a jump and update character's fatigue state.",
)
async def record_character_jump(
    character_id: int,
    request: RecordJumpRequest,
) -> FatigueStateResponse:
    """
    Record a jump for a character.

    Updates their fatigue state based on the jump distance.
    """
    tracker = get_fatigue_tracker()

    try:
        state = tracker.record_jump(
            character_id,
            request.from_system,
            request.to_system,
        )
        return FatigueStateResponse.from_state(state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.delete(
    "/character/{character_id}",
    summary="Clear character fatigue",
    description="Clear fatigue tracking for a character.",
)
async def clear_character_fatigue(character_id: int) -> dict[str, str]:
    """
    Clear fatigue tracking for a character.

    Use when fatigue naturally decays to zero or to reset tracking.
    """
    tracker = get_fatigue_tracker()
    tracker.clear_state(character_id)
    return {"status": "cleared", "character_id": str(character_id)}


@router.get(
    "/format",
    summary="Format timer",
    description="Format seconds as human-readable timer string.",
)
async def format_timer_endpoint(
    seconds: float = Query(..., ge=0, description="Seconds to format"),
) -> dict[str, str]:
    """
    Format seconds as a timer string.

    Returns format like "1:23:45" (hours:minutes:seconds) or "5:30" (minutes:seconds).
    """
    return {
        "seconds": str(round(seconds, 1)),
        "formatted": format_timer(seconds),
    }
