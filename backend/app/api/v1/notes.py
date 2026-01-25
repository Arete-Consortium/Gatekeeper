"""System notes API v1 endpoints.

Provides endpoints for managing user annotations on systems.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...services.system_notes import (
    NoteType,
    SystemNote,
    SystemNotesSummary,
    get_notes_store,
)

router = APIRouter(prefix="/notes", tags=["notes"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateNoteRequest(BaseModel):
    """Request to create a note."""

    system_name: str = Field(..., description="System to annotate")
    note_type: str = Field("info", description="Note type: info, warning, safe, fleet, bookmark, hostile, friendly")
    content: str = Field(..., min_length=1, max_length=1000, description="Note content")
    author: str | None = Field(None, description="Author name")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    is_shared: bool = Field(True, description="Whether note is visible to others")
    expires_at: datetime | None = Field(None, description="Optional expiry time")


class UpdateNoteRequest(BaseModel):
    """Request to update a note."""

    content: str | None = Field(None, max_length=1000, description="New content")
    note_type: str | None = Field(None, description="New type")
    tags: list[str] | None = Field(None, description="New tags")
    is_shared: bool | None = Field(None, description="New shared status")
    expires_at: datetime | None = Field(None, description="New expiry")


class SystemNoteResponse(BaseModel):
    """Response model for a system note."""

    note_id: str
    system_name: str
    note_type: str
    content: str
    author: str | None
    created_at: datetime
    updated_at: datetime | None
    tags: list[str]
    is_shared: bool
    expires_at: datetime | None
    age_seconds: float

    @classmethod
    def from_note(cls, note: SystemNote) -> "SystemNoteResponse":
        """Create from SystemNote."""
        return cls(
            note_id=note.note_id,
            system_name=note.system_name,
            note_type=note.note_type.value,
            content=note.content,
            author=note.author,
            created_at=note.created_at,
            updated_at=note.updated_at,
            tags=note.tags,
            is_shared=note.is_shared,
            expires_at=note.expires_at,
            age_seconds=note.age_seconds,
        )


class SystemNotesSummaryResponse(BaseModel):
    """Response model for system notes summary."""

    system_name: str
    total_notes: int
    note_types: dict[str, int]
    has_warnings: bool
    latest_note: SystemNoteResponse | None
    notes: list[SystemNoteResponse]

    @classmethod
    def from_summary(cls, summary: SystemNotesSummary) -> "SystemNotesSummaryResponse":
        """Create from SystemNotesSummary."""
        return cls(
            system_name=summary.system_name,
            total_notes=summary.total_notes,
            note_types=summary.note_types,
            has_warnings=summary.has_warnings,
            latest_note=SystemNoteResponse.from_note(summary.latest_note) if summary.latest_note else None,
            notes=[SystemNoteResponse.from_note(n) for n in summary.notes],
        )


class WarningsResponse(BaseModel):
    """Response with all warnings."""

    total_systems: int
    total_warnings: int
    systems: dict[str, list[SystemNoteResponse]]


class RouteNotesResponse(BaseModel):
    """Response with notes for a route."""

    total_systems_with_notes: int
    systems: dict[str, SystemNotesSummaryResponse]


class SearchNotesResponse(BaseModel):
    """Response for note search."""

    total: int
    notes: list[SystemNoteResponse]


class NoteTypesResponse(BaseModel):
    """Response listing available note types."""

    types: list[dict[str, str]]


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/",
    response_model=SystemNoteResponse,
    summary="Create a note",
    description="Add a note to a system.",
)
async def create_note(request: CreateNoteRequest) -> SystemNoteResponse:
    """
    Create a note for a system.

    Notes can be used for warnings, fleet contacts, bookmarks, etc.
    """
    try:
        note_type = NoteType(request.note_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid note type: {request.note_type}. Valid types: {[t.value for t in NoteType]}",
        )

    store = get_notes_store()
    note = store.add_note(
        system_name=request.system_name,
        note_type=note_type,
        content=request.content,
        author=request.author,
        tags=request.tags,
        is_shared=request.is_shared,
        expires_at=request.expires_at,
    )

    return SystemNoteResponse.from_note(note)


@router.get(
    "/types",
    response_model=NoteTypesResponse,
    summary="List note types",
    description="Get available note types.",
)
async def list_note_types() -> NoteTypesResponse:
    """List all available note types with descriptions."""
    descriptions = {
        "info": "General information",
        "warning": "Danger warning",
        "safe": "Safe haven indicator",
        "fleet": "Fleet staging/contact",
        "bookmark": "Notable location",
        "hostile": "Known hostile activity",
        "friendly": "Friendly space",
    }

    return NoteTypesResponse(
        types=[{"type": t.value, "description": descriptions.get(t.value, "")} for t in NoteType]
    )


@router.get(
    "/system/{system_name}",
    response_model=SystemNotesSummaryResponse,
    summary="Get system notes",
    description="Get all notes for a system.",
)
async def get_system_notes(
    system_name: str,
    note_type: str | None = Query(None, description="Filter by type"),
    author: str | None = Query(None, description="Filter by author"),
) -> SystemNotesSummaryResponse:
    """
    Get notes for a specific system.

    Returns a summary with all matching notes.
    """
    store = get_notes_store()

    if note_type:
        try:
            note_type_enum = NoteType(note_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid note type: {note_type}",
            )
        notes = store.get_system_notes(system_name, note_type=note_type_enum, author=author)
    else:
        notes = store.get_system_notes(system_name, author=author)

    # Build summary manually for filtered results
    type_counts: dict[str, int] = {}
    for note in notes:
        type_counts[note.note_type.value] = type_counts.get(note.note_type.value, 0) + 1

    has_warnings = any(
        n.note_type in (NoteType.WARNING, NoteType.HOSTILE) for n in notes
    )

    summary = SystemNotesSummary(
        system_name=system_name,
        total_notes=len(notes),
        note_types=type_counts,
        has_warnings=has_warnings,
        latest_note=notes[0] if notes else None,
        notes=notes,
    )

    return SystemNotesSummaryResponse.from_summary(summary)


@router.get(
    "/note/{note_id}",
    response_model=SystemNoteResponse,
    summary="Get a note",
    description="Get a specific note by ID.",
)
async def get_note(note_id: str) -> SystemNoteResponse:
    """Get a specific note by its ID."""
    store = get_notes_store()
    note = store.get_note(note_id)

    if not note:
        raise HTTPException(
            status_code=404,
            detail=f"Note not found: {note_id}",
        )

    return SystemNoteResponse.from_note(note)


@router.patch(
    "/note/{note_id}",
    response_model=SystemNoteResponse,
    summary="Update a note",
    description="Update an existing note.",
)
async def update_note(note_id: str, request: UpdateNoteRequest) -> SystemNoteResponse:
    """Update an existing note."""
    store = get_notes_store()

    note_type = None
    if request.note_type:
        try:
            note_type = NoteType(request.note_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid note type: {request.note_type}",
            )

    note = store.update_note(
        note_id=note_id,
        content=request.content,
        note_type=note_type,
        tags=request.tags,
        is_shared=request.is_shared,
        expires_at=request.expires_at,
    )

    if not note:
        raise HTTPException(
            status_code=404,
            detail=f"Note not found: {note_id}",
        )

    return SystemNoteResponse.from_note(note)


@router.delete(
    "/note/{note_id}",
    summary="Delete a note",
    description="Delete a note by ID.",
)
async def delete_note(note_id: str) -> dict[str, str]:
    """Delete a note by its ID."""
    store = get_notes_store()
    deleted = store.delete_note(note_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Note not found: {note_id}",
        )

    return {"status": "deleted", "note_id": note_id}


@router.get(
    "/warnings",
    response_model=WarningsResponse,
    summary="Get all warnings",
    description="Get all warning and hostile notes.",
)
async def get_all_warnings() -> WarningsResponse:
    """
    Get all warning and hostile notes.

    Useful for route planning to identify dangerous systems.
    """
    store = get_notes_store()
    warnings = store.get_all_warnings()

    systems = {
        name: [SystemNoteResponse.from_note(n) for n in notes]
        for name, notes in warnings.items()
    }

    total_warnings = sum(len(notes) for notes in warnings.values())

    return WarningsResponse(
        total_systems=len(systems),
        total_warnings=total_warnings,
        systems=systems,
    )


@router.post(
    "/route",
    response_model=RouteNotesResponse,
    summary="Get notes for route",
    description="Get note summaries for all systems in a route.",
)
async def get_route_notes(system_names: list[str]) -> RouteNotesResponse:
    """
    Get notes for all systems in a route.

    Pass a list of system names and get summaries for any that have notes.
    """
    store = get_notes_store()
    summaries = store.get_notes_for_route(system_names)

    systems = {
        name: SystemNotesSummaryResponse.from_summary(summary)
        for name, summary in summaries.items()
    }

    return RouteNotesResponse(
        total_systems_with_notes=len(systems),
        systems=systems,
    )


@router.get(
    "/search",
    response_model=SearchNotesResponse,
    summary="Search notes",
    description="Search notes by content.",
)
async def search_notes(
    query: str = Query(..., min_length=2, description="Search query"),
    note_type: str | None = Query(None, description="Filter by type"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
) -> SearchNotesResponse:
    """
    Search notes by content.

    Searches in content, system name, and tags.
    """
    note_type_enum = None
    if note_type:
        try:
            note_type_enum = NoteType(note_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid note type: {note_type}",
            )

    store = get_notes_store()
    notes = store.search_notes(query, note_type=note_type_enum, limit=limit)

    return SearchNotesResponse(
        total=len(notes),
        notes=[SystemNoteResponse.from_note(n) for n in notes],
    )


@router.delete(
    "/system/{system_name}",
    summary="Clear system notes",
    description="Delete all notes for a system.",
)
async def clear_system_notes(system_name: str) -> dict[str, str]:
    """Delete all notes for a system."""
    store = get_notes_store()
    store.clear_system(system_name)

    return {"status": "cleared", "system": system_name}
