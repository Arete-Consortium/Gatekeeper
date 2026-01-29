"""Integration tests for pagination across API endpoints."""


class TestSystemsPagination:
    """Tests for /api/v1/systems/ pagination."""

    def test_default_pagination(self, test_client):
        """Test systems endpoint returns paginated response by default."""
        response = test_client.get("/api/v1/systems/")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)

        pagination = data["pagination"]
        assert "total_count" in pagination
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_prev" in pagination

        # Default page is 1
        assert pagination["page"] == 1
        # Default page_size is 50
        assert pagination["page_size"] == 50
        # First page should not have prev
        assert pagination["has_prev"] is False

    def test_custom_page_size(self, test_client):
        """Test systems endpoint with custom page_size."""
        response = test_client.get("/api/v1/systems/?page_size=10")
        assert response.status_code == 200

        data = response.json()
        pagination = data["pagination"]
        assert pagination["page_size"] == 10
        # Should have at most 10 items
        assert len(data["items"]) <= 10

    def test_page_navigation(self, test_client):
        """Test navigating between pages."""
        # Get first page
        response1 = test_client.get("/api/v1/systems/?page=1&page_size=10")
        assert response1.status_code == 200
        data1 = response1.json()

        if data1["pagination"]["has_next"]:
            # Get second page
            response2 = test_client.get("/api/v1/systems/?page=2&page_size=10")
            assert response2.status_code == 200
            data2 = response2.json()

            assert data2["pagination"]["page"] == 2
            assert data2["pagination"]["has_prev"] is True

            # Items should be different
            ids1 = {item["name"] for item in data1["items"]}
            ids2 = {item["name"] for item in data2["items"]}
            assert ids1.isdisjoint(ids2)

    def test_page_size_max_limit(self, test_client):
        """Test that page_size is capped at max (200)."""
        response = test_client.get("/api/v1/systems/?page_size=500")
        # FastAPI validation should reject values over 200
        assert response.status_code == 422

    def test_page_size_min_limit(self, test_client):
        """Test that page_size must be at least 1."""
        response = test_client.get("/api/v1/systems/?page_size=0")
        assert response.status_code == 422

    def test_page_must_be_positive(self, test_client):
        """Test that page must be >= 1."""
        response = test_client.get("/api/v1/systems/?page=0")
        assert response.status_code == 422

        response = test_client.get("/api/v1/systems/?page=-1")
        assert response.status_code == 422

    def test_filter_with_pagination(self, test_client):
        """Test that filters work with pagination."""
        response = test_client.get("/api/v1/systems/?category=highsec&page_size=5")
        assert response.status_code == 200

        data = response.json()
        # All returned items should be highsec
        for item in data["items"]:
            assert item["category"] == "highsec"

        # Pagination should reflect filtered count
        assert data["pagination"]["total_count"] >= 0

    def test_search_with_pagination(self, test_client):
        """Test that search works with pagination."""
        response = test_client.get("/api/v1/systems/?search=Ji&page_size=5")
        assert response.status_code == 200

        data = response.json()
        # All returned items should match search
        for item in data["items"]:
            assert "Ji" in item["name"] or "ji" in item["name"].lower()


class TestRouteHistoryPagination:
    """Tests for /api/v1/route/history pagination."""

    def test_history_pagination_structure(self, test_client):
        """Test route history returns paginated response."""
        response = test_client.get("/api/v1/route/history")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_history_custom_page_size(self, test_client):
        """Test route history with custom page_size."""
        response = test_client.get("/api/v1/route/history?page_size=10")
        assert response.status_code == 200

        data = response.json()
        assert data["pagination"]["page_size"] == 10


class TestSharesPagination:
    """Tests for /api/v1/share/ pagination."""

    def test_shares_pagination_structure(self, test_client):
        """Test shared routes list returns paginated response."""
        response = test_client.get("/api/v1/share/")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_shares_custom_page_size(self, test_client):
        """Test shared routes with custom page_size."""
        response = test_client.get("/api/v1/share/?page_size=10")
        assert response.status_code == 200

        data = response.json()
        assert data["pagination"]["page_size"] == 10


class TestNoteSearchPagination:
    """Tests for /api/v1/notes/search pagination."""

    def test_search_pagination_structure(self, test_client):
        """Test notes search returns paginated response."""
        response = test_client.get("/api/v1/notes/search?query=test")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "pagination" in data

    def test_search_custom_page_size(self, test_client):
        """Test notes search with custom page_size."""
        response = test_client.get("/api/v1/notes/search?query=test&page_size=10")
        assert response.status_code == 200

        data = response.json()
        assert data["pagination"]["page_size"] == 10


class TestPaginationMetadata:
    """Tests for pagination metadata correctness."""

    def test_total_pages_calculation(self, test_client):
        """Test that total_pages is calculated correctly."""
        response = test_client.get("/api/v1/systems/?page_size=50")
        assert response.status_code == 200

        data = response.json()
        total = data["pagination"]["total_count"]
        page_size = data["pagination"]["page_size"]
        total_pages = data["pagination"]["total_pages"]

        # Calculate expected total_pages
        expected = (total + page_size - 1) // page_size if total > 0 else 1
        assert total_pages == expected

    def test_has_next_correctness(self, test_client):
        """Test that has_next is correct on last page."""
        # Get first page to find total pages
        response = test_client.get("/api/v1/systems/?page_size=10")
        assert response.status_code == 200
        data = response.json()
        total_pages = data["pagination"]["total_pages"]

        if total_pages > 1:
            # Get last page
            response = test_client.get(f"/api/v1/systems/?page={total_pages}&page_size=10")
            assert response.status_code == 200
            data = response.json()
            assert data["pagination"]["has_next"] is False

    def test_has_prev_correctness(self, test_client):
        """Test that has_prev is correct on first page."""
        response = test_client.get("/api/v1/systems/?page=1")
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["has_prev"] is False

        if data["pagination"]["has_next"]:
            response = test_client.get("/api/v1/systems/?page=2")
            assert response.status_code == 200
            data = response.json()
            assert data["pagination"]["has_prev"] is True
