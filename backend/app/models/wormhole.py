"""Wormhole connection models."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class WormholeType(StrEnum):
    """Wormhole type classification."""

    # K-space to K-space
    K162 = "K162"  # Exit hole (generic)

    # C1-C6 statics
    H121 = "H121"  # C1
    C125 = "C125"  # C2
    O883 = "O883"  # C3
    M609 = "M609"  # C4
    L614 = "L614"  # C5
    S804 = "S804"  # C6

    # Highsec statics
    B274 = "B274"  # Highsec
    A239 = "A239"  # Lowsec
    E545 = "E545"  # Nullsec

    # Special
    FRIGATE = "FRIGATE"  # Frigate-only
    THERA = "THERA"  # Thera connection
    DRIFTER = "DRIFTER"  # Drifter wormhole

    UNKNOWN = "UNKNOWN"


class WormholeMass(StrEnum):
    """Wormhole mass status."""

    STABLE = "stable"  # > 50% mass remaining
    DESTAB = "destab"  # < 50% mass remaining
    CRITICAL = "critical"  # < 10% mass remaining
    UNKNOWN = "unknown"


class WormholeLife(StrEnum):
    """Wormhole time status."""

    STABLE = "stable"  # > 4 hours remaining
    EOL = "eol"  # End of life (< 4 hours)
    UNKNOWN = "unknown"


class WormholeConnection(BaseModel):
    """Represents a scanned wormhole connection."""

    id: str = Field(description="Unique connection ID")
    from_system: str = Field(description="Origin system name")
    to_system: str = Field(description="Destination system name")
    wormhole_type: WormholeType = Field(default=WormholeType.UNKNOWN)
    mass_status: WormholeMass = Field(default=WormholeMass.UNKNOWN)
    life_status: WormholeLife = Field(default=WormholeLife.UNKNOWN)
    bidirectional: bool = Field(default=True, description="Whether both sides are scanned")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = Field(default=None, description="Character name who added")
    expires_at: datetime | None = Field(default=None, description="Estimated expiry time")
    notes: str = Field(default="", description="User notes")

    # Signature info
    from_sig: str = Field(default="", description="Signature ID in origin system (e.g., ABC-123)")
    to_sig: str = Field(default="", description="Signature ID in destination system")


class WormholeConnectionCreate(BaseModel):
    """Request model for creating a wormhole connection."""

    from_system: str
    to_system: str
    wormhole_type: WormholeType = WormholeType.UNKNOWN
    mass_status: WormholeMass = WormholeMass.UNKNOWN
    life_status: WormholeLife = WormholeLife.UNKNOWN
    bidirectional: bool = True
    notes: str = ""
    from_sig: str = ""
    to_sig: str = ""
    expires_hours: float | None = Field(
        default=None, description="Hours until expiry (default: 16 for normal, 4 for frigate)"
    )


class WormholeConnectionUpdate(BaseModel):
    """Request model for updating a wormhole connection."""

    mass_status: WormholeMass | None = None
    life_status: WormholeLife | None = None
    notes: str | None = None
    from_sig: str | None = None
    to_sig: str | None = None
    expires_hours: float | None = None
