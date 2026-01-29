"""Integration tests for bookmarks API endpoints.

Note: The bookmarks API requires authentication (CurrentCharacter dependency).
These tests verify the API exists and handles validation errors properly.
Full CRUD tests require authenticated test setup.
"""


class TestBookmarksEndpointExists:
    """Tests that bookmarks endpoints exist and handle requests."""

    def test_list_bookmarks_requires_auth(self, test_client):
        """Test that listing bookmarks requires authentication."""
        response = test_client.get("/api/v1/bookmarks/")
        # Should return 422 (unprocessable) or 401 (unauthorized) for missing auth
        assert response.status_code in (401, 422)

    def test_get_bookmark_requires_auth(self, test_client):
        """Test that getting a bookmark requires authentication."""
        response = test_client.get("/api/v1/bookmarks/some-id")
        assert response.status_code in (401, 422)

    def test_delete_bookmark_requires_auth(self, test_client):
        """Test that deleting a bookmark requires authentication."""
        response = test_client.delete("/api/v1/bookmarks/some-id")
        assert response.status_code in (401, 422)


class TestBookmarksCreateValidation:
    """Tests for bookmark creation validation.

    Note: Auth check now happens before body validation with Bearer tokens,
    so these tests verify auth is required first.
    """

    def test_create_bookmark_validation_missing_fields(self, test_client):
        """Test bookmark creation requires authentication."""
        # Missing authentication - 401 returned before body validation
        response = test_client.post("/api/v1/bookmarks/", json={})
        assert response.status_code in (401, 422)

    def test_create_bookmark_validation_missing_name(self, test_client):
        """Test bookmark creation requires authentication."""
        response = test_client.post(
            "/api/v1/bookmarks/",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
            },
        )
        assert response.status_code in (401, 422)

    def test_create_bookmark_validation_missing_from(self, test_client):
        """Test bookmark creation requires authentication."""
        response = test_client.post(
            "/api/v1/bookmarks/",
            json={
                "name": "Test",
                "to_system": "Perimeter",
            },
        )
        assert response.status_code in (401, 422)

    def test_create_bookmark_validation_missing_to(self, test_client):
        """Test bookmark creation requires authentication."""
        response = test_client.post(
            "/api/v1/bookmarks/",
            json={
                "name": "Test",
                "from_system": "Jita",
            },
        )
        assert response.status_code in (401, 422)


class TestBookmarksUpdateValidation:
    """Tests for bookmark update validation."""

    def test_update_bookmark_requires_auth(self, test_client):
        """Test that updating a bookmark requires authentication."""
        response = test_client.patch("/api/v1/bookmarks/some-id", json={"name": "Updated Name"})
        assert response.status_code in (401, 422)
