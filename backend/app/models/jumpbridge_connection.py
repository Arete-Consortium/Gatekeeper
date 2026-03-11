"""Pydantic models for user-submitted jump bridge connections.

These represent community-contributed Ansiblex jump bridge data with
status tracking and DB persistence — distinct from the file-based
JumpBridgeConfig used for static network imports.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JumpBridgeStatus(StrEnum):
    """Operational status of a jump bridge."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class JumpBridgeConnection(BaseModel):
    """A user-submitted Ansiblex jump bridge connection."""

    id: str = Field(description="Unique bridge ID")
    from_system: str = Field(description="Origin system name")
    from_system_id: int = Field(description="Origin system ID")
    to_system: str = Field(description="Destination system name")
    to_system_id: int = Field(description="Destination system ID")
    owner_alliance: str | None = Field(default=None, description="Alliance that owns the bridge")
    status: JumpBridgeStatus = Field(default=JumpBridgeStatus.UNKNOWN)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = Field(default=None, description="Character name who added")
    notes: str = Field(default="", description="User notes")


class JumpBridgeConnectionCreate(BaseModel):
    """Request model for creating a jump bridge connection."""

    from_system: str
    to_system: str
    owner_alliance: str | None = None
    notes: str = ""


class JumpBridgeConnectionUpdate(BaseModel):
    """Request model for updating a jump bridge connection."""

    status: JumpBridgeStatus | None = None
    owner_alliance: str | None = None
    notes: str | None = None


class JumpBridgeImportLine(BaseModel):
    """A single parsed import line result."""

    from_system: str
    to_system: str
    success: bool
    error: str | None = None


class JumpBridgeImportRequest(BaseModel):
    """Request to bulk-import jump bridges from text paste."""

    text: str = Field(
        ...,
        description='Jump bridge data, one per line. Format: "System A \u00bb System B"',
    )


class JumpBridgeImportResponse(BaseModel):
    """Response from bulk import."""

    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
    bridges: list[JumpBridgeConnection] = Field(default_factory=list)


class JumpBridgeListResponse(BaseModel):
    """Response for listing jump bridge connections."""

    bridges: list[JumpBridgeConnection]
    total: int
