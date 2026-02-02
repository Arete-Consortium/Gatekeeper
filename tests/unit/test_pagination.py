"""Unit tests for pagination utilities."""

import pytest

from backend.app.core.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
    PaginationMeta,
    PaginationParams,
    paginate,
)


class TestPaginationParams:
    """Tests for PaginationParams model."""

    def test_default_values(self):
        """Test default pagination parameters."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == DEFAULT_PAGE_SIZE

    def test_offset_calculation(self):
        """Test offset calculation from page number."""
        params = PaginationParams(page=1, page_size=50)
        assert params.offset == 0

        params = PaginationParams(page=2, page_size=50)
        assert params.offset == 50

        params = PaginationParams(page=3, page_size=25)
        assert params.offset == 50

    def test_limit_alias(self):
        """Test limit alias for page_size."""
        params = PaginationParams(page_size=75)
        assert params.limit == 75

    def test_page_must_be_positive(self):
        """Test that page must be >= 1."""
        with pytest.raises(ValueError):
            PaginationParams(page=0)

        with pytest.raises(ValueError):
            PaginationParams(page=-1)

    def test_page_size_bounds(self):
        """Test page_size must be within bounds."""
        with pytest.raises(ValueError):
            PaginationParams(page_size=0)

        with pytest.raises(ValueError):
            PaginationParams(page_size=MAX_PAGE_SIZE + 1)


class TestPaginationMeta:
    """Tests for PaginationMeta model."""

    def test_meta_fields(self):
        """Test all metadata fields are present."""
        meta = PaginationMeta(
            total_count=100,
            page=1,
            page_size=50,
            total_pages=2,
            has_next=True,
            has_prev=False,
        )
        assert meta.total_count == 100
        assert meta.page == 1
        assert meta.page_size == 50
        assert meta.total_pages == 2
        assert meta.has_next is True
        assert meta.has_prev is False


class TestPaginate:
    """Tests for paginate function."""

    @pytest.fixture
    def sample_items(self) -> list[dict]:
        """Create sample items for testing."""
        return [{"id": i, "name": f"Item {i}"} for i in range(150)]

    def test_first_page(self, sample_items):
        """Test getting the first page."""
        items, meta = paginate(sample_items, page=1, page_size=50)

        assert len(items) == 50
        assert items[0]["id"] == 0
        assert items[49]["id"] == 49
        assert meta.total_count == 150
        assert meta.page == 1
        assert meta.total_pages == 3
        assert meta.has_next is True
        assert meta.has_prev is False

    def test_middle_page(self, sample_items):
        """Test getting a middle page."""
        items, meta = paginate(sample_items, page=2, page_size=50)

        assert len(items) == 50
        assert items[0]["id"] == 50
        assert items[49]["id"] == 99
        assert meta.page == 2
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_last_page(self, sample_items):
        """Test getting the last page."""
        items, meta = paginate(sample_items, page=3, page_size=50)

        assert len(items) == 50
        assert items[0]["id"] == 100
        assert items[49]["id"] == 149
        assert meta.page == 3
        assert meta.has_next is False
        assert meta.has_prev is True

    def test_partial_last_page(self):
        """Test last page with fewer items than page_size."""
        items_list = [{"id": i} for i in range(125)]
        items, meta = paginate(items_list, page=3, page_size=50)

        assert len(items) == 25
        assert items[0]["id"] == 100
        assert items[-1]["id"] == 124
        assert meta.total_count == 125
        assert meta.total_pages == 3
        assert meta.has_next is False

    def test_empty_list(self):
        """Test pagination of empty list."""
        items, meta = paginate([], page=1, page_size=50)

        assert len(items) == 0
        assert meta.total_count == 0
        assert meta.total_pages == 1  # Always at least 1 page
        assert meta.has_next is False
        assert meta.has_prev is False

    def test_single_page(self):
        """Test when all items fit on one page."""
        items_list = [{"id": i} for i in range(25)]
        items, meta = paginate(items_list, page=1, page_size=50)

        assert len(items) == 25
        assert meta.total_count == 25
        assert meta.total_pages == 1
        assert meta.has_next is False
        assert meta.has_prev is False

    def test_exact_page_boundary(self):
        """Test when items exactly fill pages."""
        items_list = [{"id": i} for i in range(100)]
        items, meta = paginate(items_list, page=2, page_size=50)

        assert len(items) == 50
        assert meta.total_count == 100
        assert meta.total_pages == 2
        assert meta.has_next is False
        assert meta.has_prev is True

    def test_page_beyond_range(self, sample_items):
        """Test requesting a page beyond available data."""
        items, meta = paginate(sample_items, page=10, page_size=50)

        assert len(items) == 0
        assert meta.total_count == 150
        assert meta.page == 10
        assert meta.has_next is False
        assert meta.has_prev is True

    def test_page_size_clamping(self, sample_items):
        """Test that page_size is clamped to valid range."""
        # Test min clamping
        items, meta = paginate(sample_items, page=1, page_size=-5)
        assert meta.page_size == MIN_PAGE_SIZE

        # Test max clamping
        items, meta = paginate(sample_items, page=1, page_size=500)
        assert meta.page_size == MAX_PAGE_SIZE

    def test_with_total_count_provided(self):
        """Test pagination with pre-sliced items and total_count."""
        # Simulate DB query with LIMIT/OFFSET already applied
        pre_sliced = [{"id": i} for i in range(50, 100)]  # Already sliced for page 2
        total_in_db = 250

        items, meta = paginate(pre_sliced, page=2, page_size=50, total_count=total_in_db)

        # Items are already sliced, so should be returned as-is
        assert len(items) == 50
        assert meta.total_count == 250
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_custom_page_size(self, sample_items):
        """Test with non-default page size."""
        items, meta = paginate(sample_items, page=1, page_size=25)

        assert len(items) == 25
        assert meta.page_size == 25
        assert meta.total_pages == 6  # 150 / 25 = 6

    def test_page_size_one(self):
        """Test with page_size of 1."""
        items_list = [{"id": i} for i in range(5)]
        items, meta = paginate(items_list, page=3, page_size=1)

        assert len(items) == 1
        assert items[0]["id"] == 2
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_prev is True
