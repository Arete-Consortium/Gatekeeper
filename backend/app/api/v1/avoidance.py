"""Avoidance list API v1 endpoints."""

from fastapi import APIRouter, HTTPException

from ...models.avoidance import (
    AvoidanceList,
    AvoidanceListCreateRequest,
    AvoidanceListUpdateRequest,
)
from ...services.avoidance import (
    clear_avoidance_cache,
    create_avoidance_list,
    delete_avoidance_list,
    get_avoidance_list,
    list_avoidance_lists,
    update_avoidance_list,
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[AvoidanceList],
    summary="List all avoidance lists",
    description="Returns all saved avoidance lists with names and system counts.",
)
def list_all() -> list[AvoidanceList]:
    """Get all avoidance lists."""
    return list_avoidance_lists()


@router.post(
    "/",
    response_model=AvoidanceList,
    status_code=201,
    summary="Create a new avoidance list",
    description="Create a named set of systems to avoid in routing.",
)
def create(request: AvoidanceListCreateRequest) -> AvoidanceList:
    """Create a new avoidance list."""
    clear_avoidance_cache()
    try:
        return create_avoidance_list(
            name=request.name,
            systems=request.systems,
            description=request.description,
        )
    except ValueError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e)) from None
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.get(
    "/{name}",
    response_model=AvoidanceList,
    summary="Get a specific avoidance list",
    description="Returns the full avoidance list with all systems.",
)
def get_one(name: str) -> AvoidanceList:
    """Get a specific avoidance list."""
    try:
        return get_avoidance_list(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.put(
    "/{name}",
    response_model=AvoidanceList,
    summary="Update an avoidance list",
    description="Update systems or description of an existing avoidance list.",
)
def update(name: str, request: AvoidanceListUpdateRequest) -> AvoidanceList:
    """Update an avoidance list."""
    clear_avoidance_cache()
    try:
        return update_avoidance_list(
            name=name,
            systems=request.systems,
            description=request.description,
            add_systems=request.add_systems,
            remove_systems=request.remove_systems,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.delete(
    "/{name}",
    summary="Delete an avoidance list",
    description="Delete a named avoidance list.",
)
def delete(name: str) -> dict:
    """Delete an avoidance list."""
    clear_avoidance_cache()
    try:
        delete_avoidance_list(name)
        return {"status": "ok", "deleted": name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
