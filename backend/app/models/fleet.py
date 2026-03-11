"""Pydantic models for fleet composition analysis."""

from pydantic import BaseModel, Field


class FleetAnalyzeRequest(BaseModel):
    """Request to analyze a fleet composition."""

    text: str = Field(
        ...,
        description="Fleet composition text (tab-separated or multiplied format)",
        min_length=1,
    )


class ShipEntry(BaseModel):
    """A single ship type in the fleet."""

    name: str
    count: int
    role: str


class FleetAnalysisResponse(BaseModel):
    """Response with fleet threat assessment."""

    total_pilots: int = Field(..., description="Total number of pilots/ships in fleet")
    total_ships: int = Field(..., description="Total number of ships (same as pilots)")
    threat_level: str = Field(
        ...,
        description="Overall threat: minimal, moderate, significant, critical, overwhelming",
    )
    composition: dict[str, int] = Field(
        ...,
        description="Ship role breakdown (role -> count)",
    )
    ship_list: list[ShipEntry] = Field(
        ...,
        description="Individual ship types with counts and roles",
    )
    has_logistics: bool = Field(..., description="Whether fleet has logistics ships")
    has_capitals: bool = Field(..., description="Whether fleet has capital ships")
    has_tackle: bool = Field(..., description="Whether fleet has tackle ships")
    estimated_dps_category: str = Field(
        ...,
        description="Estimated DPS output: low, medium, high, extreme",
    )
    advice: list[str] = Field(
        ...,
        description="Tactical advice based on fleet composition",
    )
