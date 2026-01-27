"""Pydantic models for named avoidance lists."""

from datetime import datetime

from pydantic import BaseModel, Field


class AvoidanceList(BaseModel):
    """A named set of systems to avoid."""

    name: str = Field(..., description="List name (e.g., 'gatecamps')")
    systems: list[str] = Field(default_factory=list, description="System names to avoid")
    description: str = Field("", description="Optional description")
    created_at: datetime
    updated_at: datetime


class AvoidanceConfig(BaseModel):
    """All saved avoidance lists."""

    lists: list[AvoidanceList] = Field(default_factory=list)


class AvoidanceListCreateRequest(BaseModel):
    """Request to create a new avoidance list."""

    name: str = Field(..., min_length=1, max_length=50)
    systems: list[str] = Field(..., min_length=1)
    description: str = Field("")


class AvoidanceListUpdateRequest(BaseModel):
    """Request to update an existing avoidance list."""

    systems: list[str] | None = None
    description: str | None = None
    add_systems: list[str] | None = Field(None, description="Systems to add to list")
    remove_systems: list[str] | None = Field(None, description="Systems to remove from list")
