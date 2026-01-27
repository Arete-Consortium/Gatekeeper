"""Pochven filament routing models."""

from pydantic import BaseModel, Field


class PochvenConnection(BaseModel):
    """A connection between a Pochven system and k-space (or internal)."""

    from_system: str
    to_system: str
    connection_type: str = Field(
        "internal", description="Connection type: 'internal', 'entry', or 'exit'"
    )
    bidirectional: bool = True


class PochvenNetwork(BaseModel):
    """The Pochven filament network state."""

    connections: list[PochvenConnection]
    enabled: bool = True


class PochvenStatusResponse(BaseModel):
    """Status of the Pochven network."""

    enabled: bool = Field(True, description="Whether Pochven routing is enabled")
    connection_count: int = Field(0, description="Number of active connections")
    system_count: int = Field(0, description="Number of Pochven systems in network")


class PochvenToggleRequest(BaseModel):
    """Request to toggle Pochven routing."""

    enabled: bool = Field(..., description="Whether to enable Pochven routing")
