"""Thera wormhole connection models."""

from datetime import datetime

from pydantic import BaseModel, Field


class TheraConnection(BaseModel):
    """A single Thera wormhole connection from EVE-Scout."""

    id: int
    in_system_id: int
    in_system_name: str
    out_system_id: int
    out_system_name: str
    wh_type: str = ""
    max_ship_size: str = ""
    remaining_hours: float = 0.0
    expires_at: datetime | None = None
    completed: bool = False


class TheraConnectionsResponse(BaseModel):
    """Response for listing active Thera connections."""

    connections: list[TheraConnection]
    total: int
    last_updated: datetime | None = None


class TheraStatusResponse(BaseModel):
    """Status of the Thera connection cache."""

    cache_age_seconds: float | None = Field(None, description="Seconds since last cache refresh")
    connection_count: int = Field(0, description="Number of active connections")
    api_healthy: bool = Field(True, description="Whether EVE-Scout API is reachable")
    last_error: str | None = None
