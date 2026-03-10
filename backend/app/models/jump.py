"""Pydantic models for jump drive operations."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ShipType(StrEnum):
    """Capital ship types with jump drives."""

    JUMP_FREIGHTER = "jump_freighter"
    CARRIER = "carrier"
    DREADNOUGHT = "dreadnought"
    FORCE_AUXILIARY = "force_auxiliary"
    SUPERCARRIER = "supercarrier"
    TITAN = "titan"
    RORQUAL = "rorqual"
    BLOPS = "black_ops"


class FuelType(StrEnum):
    """Fuel isotope types for capital ships."""

    NITROGEN = "nitrogen"
    HELIUM = "helium"
    OXYGEN = "oxygen"
    HYDROGEN = "hydrogen"


class JumpRangeResponse(BaseModel):
    """Jump range calculation response."""

    ship_type: str
    base_range_ly: float = Field(..., description="Base jump range before skills")
    max_range_ly: float = Field(..., description="Max range with current skills")
    jdc_level: int = Field(..., description="Jump Drive Calibration level")
    jfc_level: int = Field(..., description="Jump Fuel Conservation level")
    fuel_per_ly: int = Field(..., description="Fuel consumption per light year")


class SystemInRangeResponse(BaseModel):
    """A system within jump range."""

    name: str
    system_id: int
    distance_ly: float
    security: float
    category: str
    fuel_required: int = 0


class JumpLegResponse(BaseModel):
    """A single jump leg in a route."""

    from_system: str
    to_system: str
    distance_ly: float
    fuel_required: int
    fatigue_added_minutes: float
    total_fatigue_minutes: float
    wait_time_minutes: float


class JumpRouteResponse(BaseModel):
    """Complete jump route response."""

    from_system: str
    to_system: str
    ship_type: str
    total_jumps: int
    total_distance_ly: float
    total_fuel: int
    total_fatigue_minutes: float
    total_travel_time_minutes: float
    legs: list[JumpLegResponse]
    fuel_type_id: int = Field(0, description="EVE type ID of fuel isotope")
    fuel_type_name: str = Field("", description="Name of fuel isotope")
    fuel_unit_cost: float = Field(0.0, description="Jita sell price per unit of fuel")
    total_fuel_cost: float = Field(0.0, description="Total ISK cost of fuel at Jita prices")


class SystemsInRangeResponse(BaseModel):
    """Response for systems in range query."""

    origin: str
    max_range_ly: float
    count: int
    systems: list[SystemInRangeResponse]
