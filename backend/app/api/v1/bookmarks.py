"""Route bookmark API endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_db
from ...db.models import RouteBookmark
from ...models.bookmark import (
    BookmarkCreate,
    BookmarkListResponse,
    BookmarkResponse,
    BookmarkUpdate,
)
from ...services.data_loader import load_risk_config, load_universe
from .dependencies import CurrentCharacter

router = APIRouter()


def _bookmark_to_response(bookmark: RouteBookmark) -> BookmarkResponse:
    """Convert database model to response model."""
    avoid = []
    if bookmark.avoid_systems:
        try:
            avoid = json.loads(bookmark.avoid_systems)
        except json.JSONDecodeError:
            avoid = []

    return BookmarkResponse(
        id=bookmark.id,
        character_id=bookmark.character_id,
        name=bookmark.name,
        from_system=bookmark.from_system,
        to_system=bookmark.to_system,
        profile=bookmark.profile,
        avoid_systems=avoid,
        use_bridges=bookmark.use_bridges,
        notes=bookmark.notes,
        created_at=bookmark.created_at,
        updated_at=bookmark.updated_at,
    )


@router.get(
    "/",
    response_model=BookmarkListResponse,
    summary="List route bookmarks",
    description="Get all bookmarks for the authenticated character.",
)
async def list_bookmarks(
    character: CurrentCharacter,
    db: AsyncSession = Depends(get_db),
) -> BookmarkListResponse:
    """List all bookmarks for the current character."""
    result = await db.execute(
        select(RouteBookmark)
        .where(RouteBookmark.character_id == character.character_id)
        .order_by(RouteBookmark.updated_at.desc())
    )
    bookmarks = result.scalars().all()

    return BookmarkListResponse(
        bookmarks=[_bookmark_to_response(b) for b in bookmarks],
        total=len(bookmarks),
    )


@router.post(
    "/",
    response_model=BookmarkResponse,
    status_code=201,
    summary="Create route bookmark",
    description="Save a new route bookmark.",
)
async def create_bookmark(
    request: BookmarkCreate,
    character: CurrentCharacter,
    db: AsyncSession = Depends(get_db),
) -> BookmarkResponse:
    """Create a new bookmark for the current character."""
    universe = load_universe()
    cfg = load_risk_config()

    # Validate systems exist
    if request.from_system not in universe.systems:
        raise HTTPException(status_code=400, detail=f"Unknown system: {request.from_system}")
    if request.to_system not in universe.systems:
        raise HTTPException(status_code=400, detail=f"Unknown system: {request.to_system}")

    # Validate profile
    if request.profile not in cfg.routing_profiles:
        available = ", ".join(cfg.routing_profiles.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown profile: '{request.profile}'. Available: {available}",
        )

    # Validate avoid systems
    for sys in request.avoid_systems:
        if sys not in universe.systems:
            raise HTTPException(status_code=400, detail=f"Unknown avoid system: {sys}")

    bookmark = RouteBookmark(
        character_id=character.character_id,
        name=request.name,
        from_system=request.from_system,
        to_system=request.to_system,
        profile=request.profile,
        avoid_systems=json.dumps(request.avoid_systems) if request.avoid_systems else None,
        use_bridges=request.use_bridges,
        notes=request.notes,
    )

    db.add(bookmark)
    await db.flush()
    await db.refresh(bookmark)

    return _bookmark_to_response(bookmark)


@router.get(
    "/{bookmark_id}",
    response_model=BookmarkResponse,
    summary="Get bookmark",
    description="Get a specific bookmark by ID.",
)
async def get_bookmark(
    bookmark_id: int,
    character: CurrentCharacter,
    db: AsyncSession = Depends(get_db),
) -> BookmarkResponse:
    """Get a specific bookmark."""
    result = await db.execute(
        select(RouteBookmark).where(
            RouteBookmark.id == bookmark_id,
            RouteBookmark.character_id == character.character_id,
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    return _bookmark_to_response(bookmark)


@router.patch(
    "/{bookmark_id}",
    response_model=BookmarkResponse,
    summary="Update bookmark",
    description="Update an existing bookmark.",
)
async def update_bookmark(
    bookmark_id: int,
    request: BookmarkUpdate,
    character: CurrentCharacter,
    db: AsyncSession = Depends(get_db),
) -> BookmarkResponse:
    """Update a bookmark."""
    result = await db.execute(
        select(RouteBookmark).where(
            RouteBookmark.id == bookmark_id,
            RouteBookmark.character_id == character.character_id,
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    universe = load_universe()
    cfg = load_risk_config()

    # Update fields if provided
    if request.name is not None:
        bookmark.name = request.name

    if request.from_system is not None:
        if request.from_system not in universe.systems:
            raise HTTPException(status_code=400, detail=f"Unknown system: {request.from_system}")
        bookmark.from_system = request.from_system

    if request.to_system is not None:
        if request.to_system not in universe.systems:
            raise HTTPException(status_code=400, detail=f"Unknown system: {request.to_system}")
        bookmark.to_system = request.to_system

    if request.profile is not None:
        if request.profile not in cfg.routing_profiles:
            available = ", ".join(cfg.routing_profiles.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Unknown profile: '{request.profile}'. Available: {available}",
            )
        bookmark.profile = request.profile

    if request.avoid_systems is not None:
        for sys in request.avoid_systems:
            if sys not in universe.systems:
                raise HTTPException(status_code=400, detail=f"Unknown avoid system: {sys}")
        bookmark.avoid_systems = (
            json.dumps(request.avoid_systems) if request.avoid_systems else None
        )

    if request.use_bridges is not None:
        bookmark.use_bridges = request.use_bridges

    if request.notes is not None:
        bookmark.notes = request.notes

    await db.flush()
    await db.refresh(bookmark)

    return _bookmark_to_response(bookmark)


@router.delete(
    "/{bookmark_id}",
    status_code=204,
    summary="Delete bookmark",
    description="Delete a bookmark.",
)
async def delete_bookmark(
    bookmark_id: int,
    character: CurrentCharacter,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a bookmark."""
    result = await db.execute(
        select(RouteBookmark).where(
            RouteBookmark.id == bookmark_id,
            RouteBookmark.character_id == character.character_id,
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.delete(bookmark)
