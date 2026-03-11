"""Pydantic models for intel chat parsing feature."""

from pydantic import BaseModel, Field


class IntelParseRequest(BaseModel):
    """Request to parse intel chat text."""

    text: str = Field(..., description="Intel/local chat text to parse", min_length=1)


class ParsedSystem(BaseModel):
    """A system extracted from intel chat text."""

    system_name: str = Field(..., description="EVE solar system name")
    system_id: int = Field(..., description="EVE solar system ID")
    status: str = Field(..., description="System status: clear, hostile, or unknown")
    hostile_count: int = Field(0, description="Number of hostiles reported (0 if clear/unknown)")
    mentioned_at: str = Field(..., description="The raw line where this system was mentioned")


class IntelParseResponse(BaseModel):
    """Response from parsing intel chat text."""

    systems: list[ParsedSystem] = Field(
        default_factory=list,
        description="Systems extracted from the intel text",
    )
    unknown_lines: list[str] = Field(
        default_factory=list,
        description="Lines that could not be parsed into known systems",
    )
