"""Pagination utilities for API endpoints.

Provides reusable pagination parameters and response models.
"""

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

# Type variable for generic pagination
T = TypeVar("T")

# Pagination constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200
MIN_PAGE_SIZE = 1


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints.

    Supports both page-based (page/page_size) and offset-based (offset/limit) pagination.
    Default is page-based for cleaner URLs and easier client implementation.
    """

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    )

    @property
    def offset(self) -> int:
        """Calculate offset from page number."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size for offset-based access."""
        return self.page_size


class PaginationMeta(BaseModel):
    """Pagination metadata for responses."""

    total_count: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there's a next page")
    has_prev: bool = Field(..., description="Whether there's a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model.

    Usage:
        class SystemListResponse(PaginatedResponse[SystemSummary]):
            pass
    """

    items: list[T]
    pagination: PaginationMeta


def paginate(
    items: list[T],
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    total_count: int | None = None,
) -> tuple[list[T], PaginationMeta]:
    """Apply pagination to a list and return items with metadata.

    Args:
        items: Full list of items (or pre-sliced items if total_count provided)
        page: Page number (1-indexed)
        page_size: Items per page
        total_count: Total items count (if items are pre-sliced from DB)

    Returns:
        Tuple of (paginated items, pagination metadata)

    Example:
        systems = load_all_systems()
        paginated, meta = paginate(systems, page=2, page_size=50)
    """
    # Validate page_size
    page_size = min(max(page_size, MIN_PAGE_SIZE), MAX_PAGE_SIZE)

    # If total_count not provided, calculate from items list
    if total_count is None:
        total_count = len(items)
        # Apply pagination to the full list
        offset = (page - 1) * page_size
        paginated_items = items[offset : offset + page_size]
    else:
        # Items are already sliced (e.g., from DB query with LIMIT/OFFSET)
        paginated_items = items

    # Calculate pagination metadata
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1

    meta = PaginationMeta(
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )

    return paginated_items, meta


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=MIN_PAGE_SIZE,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE})",
    ),
) -> PaginationParams:
    """FastAPI dependency for pagination parameters.

    Usage:
        @router.get("/items")
        def list_items(pagination: PaginationParams = Depends(get_pagination_params)):
            items, meta = paginate(all_items, pagination.page, pagination.page_size)
            return {"items": items, "pagination": meta}
    """
    return PaginationParams(page=page, page_size=page_size)
