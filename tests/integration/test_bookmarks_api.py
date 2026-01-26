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
    """Tests for bookmark creation validation (before auth check)."""

    def test_create_bookmark_validation_missing_fields(self, test_client):
        """Test bookmark creation validates required fields."""
        # Missing required fields - validation fails before auth
        response = test_client.post("/api/v1/bookmarks/", json={})
        assert response.status_code == 422

    def test_create_bookmark_validation_missing_name(self, test_client):
        """Test bookmark creation requires name."""
        response = test_client.post(
            "/api/v1/bookmarks/",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
            }
        )
        assert response.status_code == 422

    def test_create_bookmark_validation_missing_from(self, test_client):
        """Test bookmark creation requires from_system."""
        response = test_client.post(
            "/api/v1/bookmarks/",
            json={
                "name": "Test",
                "to_system": "Perimeter",
            }
        )
        assert response.status_code == 422

    def test_create_bookmark_validation_missing_to(self, test_client):
        """Test bookmark creation requires to_system."""
        response = test_client.post(
            "/api/v1/bookmarks/",
            json={
                "name": "Test",
                "from_system": "Jita",
            }
        )
        assert response.status_code == 422


class TestBookmarksUpdateValidation:
    """Tests for bookmark update validation."""

    def test_update_bookmark_requires_auth(self, test_client):
        """Test that updating a bookmark requires authentication."""
        response = test_client.patch(
            "/api/v1/bookmarks/some-id",
            json={"name": "Updated Name"}
        )
        assert response.status_code in (401, 422)
