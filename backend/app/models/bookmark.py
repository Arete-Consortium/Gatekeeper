"""Pydantic models for route bookmarks."""

from datetime import datetime

from pydantic import BaseModel, Field


class BookmarkCreate(BaseModel):
    """Request to create a new bookmark."""

    name: str = Field(..., min_length=1, max_length=100, description="Bookmark name")
    from_system: str = Field(..., description="Origin system name")
    to_system: str = Field(..., description="Destination system name")
    profile: str = Field("shortest", description="Routing profile to use")
    avoid_systems: list[str] = Field(default_factory=list, description="Systems to avoid")
    use_bridges: bool = Field(False, description="Use jump bridges in routing")
    notes: str | None = Field(None, max_length=500, description="Optional notes")


class BookmarkUpdate(BaseModel):
    """Request to update an existing bookmark."""

    name: str | None = Field(None, min_length=1, max_length=100)
    from_system: str | None = None
    to_system: str | None = None
    profile: str | None = None
    avoid_systems: list[str] | None = None
    use_bridges: bool | None = None
    notes: str | None = Field(None, max_length=500)


class BookmarkResponse(BaseModel):
    """Response model for a bookmark."""

    id: int
    character_id: int
    name: str
    from_system: str
    to_system: str
    profile: str
    avoid_systems: list[str]
    use_bridges: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookmarkListResponse(BaseModel):
    """Response for listing bookmarks."""

    bookmarks: list[BookmarkResponse]
    total: int
