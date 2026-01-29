"""Integration tests for system notes API endpoints."""

import pytest

from backend.app.services.system_notes import reset_notes_store


@pytest.fixture(autouse=True)
def reset_store():
    """Reset notes store before each test."""
    reset_notes_store()
    yield
    reset_notes_store()


class TestCreateNoteEndpoint:
    """Tests for POST /api/v1/notes/."""

    def test_create_note(self, test_client):
        """Test creating a note."""
        response = test_client.post(
            "/api/v1/notes/",
            json={
                "system_name": "Jita",
                "note_type": "info",
                "content": "Major trade hub",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["system_name"] == "Jita"
        assert data["content"] == "Major trade hub"
        assert data["note_type"] == "info"

    def test_create_warning_note(self, test_client):
        """Test creating a warning note."""
        response = test_client.post(
            "/api/v1/notes/",
            json={
                "system_name": "Rancer",
                "note_type": "warning",
                "content": "Pirate gate camp!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["note_type"] == "warning"

    def test_create_note_with_author(self, test_client):
        """Test creating note with author."""
        response = test_client.post(
            "/api/v1/notes/",
            json={
                "system_name": "Jita",
                "note_type": "info",
                "content": "Test",
                "author": "TestPilot",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["author"] == "TestPilot"

    def test_create_note_with_tags(self, test_client):
        """Test creating note with tags."""
        response = test_client.post(
            "/api/v1/notes/",
            json={
                "system_name": "Jita",
                "note_type": "info",
                "content": "Test",
                "tags": ["trade", "hub"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "trade" in data["tags"]

    def test_create_note_invalid_type(self, test_client):
        """Test creating note with invalid type."""
        response = test_client.post(
            "/api/v1/notes/",
            json={
                "system_name": "Jita",
                "note_type": "invalid_type",
                "content": "Test",
            },
        )

        assert response.status_code == 400


class TestNoteTypesEndpoint:
    """Tests for GET /api/v1/notes/types."""

    def test_list_note_types(self, test_client):
        """Test listing available note types."""
        response = test_client.get("/api/v1/notes/types")

        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert len(data["types"]) >= 7

        type_values = [t["type"] for t in data["types"]]
        assert "info" in type_values
        assert "warning" in type_values


class TestGetSystemNotesEndpoint:
    """Tests for GET /api/v1/notes/system/{system_name}."""

    def test_get_system_notes_empty(self, test_client):
        """Test getting notes for system with no notes."""
        response = test_client.get("/api/v1/notes/system/Jita")

        assert response.status_code == 200
        data = response.json()
        assert data["total_notes"] == 0
        assert data["notes"] == []

    def test_get_system_notes(self, test_client):
        """Test getting notes for a system."""
        # Create notes
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Note 1"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "warning", "content": "Note 2"},
        )

        response = test_client.get("/api/v1/notes/system/Jita")

        assert response.status_code == 200
        data = response.json()
        assert data["total_notes"] == 2
        assert data["has_warnings"] is True

    def test_get_system_notes_by_type(self, test_client):
        """Test getting notes filtered by type."""
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Info"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "warning", "content": "Warning"},
        )

        response = test_client.get("/api/v1/notes/system/Jita?note_type=warning")

        assert response.status_code == 200
        data = response.json()
        assert data["total_notes"] == 1


class TestGetNoteEndpoint:
    """Tests for GET /api/v1/notes/note/{note_id}."""

    def test_get_note(self, test_client):
        """Test getting a specific note."""
        # Create
        create_response = test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Test"},
        )
        note_id = create_response.json()["note_id"]

        # Get
        response = test_client.get(f"/api/v1/notes/note/{note_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["note_id"] == note_id

    def test_get_nonexistent_note(self, test_client):
        """Test getting nonexistent note returns 404."""
        response = test_client.get("/api/v1/notes/note/nonexistent")

        assert response.status_code == 404


class TestUpdateNoteEndpoint:
    """Tests for PATCH /api/v1/notes/note/{note_id}."""

    def test_update_note_content(self, test_client):
        """Test updating note content."""
        # Create
        create_response = test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Original"},
        )
        note_id = create_response.json()["note_id"]

        # Update
        response = test_client.patch(
            f"/api/v1/notes/note/{note_id}",
            json={"content": "Updated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated"
        assert data["updated_at"] is not None

    def test_update_note_type(self, test_client):
        """Test updating note type."""
        create_response = test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Test"},
        )
        note_id = create_response.json()["note_id"]

        response = test_client.patch(
            f"/api/v1/notes/note/{note_id}",
            json={"note_type": "warning"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["note_type"] == "warning"

    def test_update_nonexistent_note(self, test_client):
        """Test updating nonexistent note returns 404."""
        response = test_client.patch(
            "/api/v1/notes/note/nonexistent",
            json={"content": "Test"},
        )

        assert response.status_code == 404


class TestDeleteNoteEndpoint:
    """Tests for DELETE /api/v1/notes/note/{note_id}."""

    def test_delete_note(self, test_client):
        """Test deleting a note."""
        create_response = test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Test"},
        )
        note_id = create_response.json()["note_id"]

        response = test_client.delete(f"/api/v1/notes/note/{note_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

        # Verify deleted
        get_response = test_client.get(f"/api/v1/notes/note/{note_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_note(self, test_client):
        """Test deleting nonexistent note returns 404."""
        response = test_client.delete("/api/v1/notes/note/nonexistent")

        assert response.status_code == 404


class TestWarningsEndpoint:
    """Tests for GET /api/v1/notes/warnings."""

    def test_get_warnings_empty(self, test_client):
        """Test getting warnings when none exist."""
        response = test_client.get("/api/v1/notes/warnings")

        assert response.status_code == 200
        data = response.json()
        assert data["total_systems"] == 0
        assert data["total_warnings"] == 0

    def test_get_warnings(self, test_client):
        """Test getting all warnings."""
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Rancer", "note_type": "warning", "content": "Gate camp"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Tama", "note_type": "hostile", "content": "Pirates"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Safe"},
        )

        response = test_client.get("/api/v1/notes/warnings")

        assert response.status_code == 200
        data = response.json()
        assert data["total_systems"] == 2
        assert "Rancer" in data["systems"]
        assert "Tama" in data["systems"]


class TestRouteNotesEndpoint:
    """Tests for POST /api/v1/notes/route."""

    def test_get_route_notes(self, test_client):
        """Test getting notes for a route."""
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Start"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Perimeter", "note_type": "warning", "content": "Camp"},
        )

        response = test_client.post(
            "/api/v1/notes/route",
            json=["Jita", "Perimeter", "Urlen", "Amarr"],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_systems_with_notes"] == 2
        assert "Jita" in data["systems"]
        assert "Perimeter" in data["systems"]


class TestSearchNotesEndpoint:
    """Tests for GET /api/v1/notes/search."""

    def test_search_notes(self, test_client):
        """Test searching notes."""
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Trade hub"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Amarr", "note_type": "info", "content": "Another trade hub"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Dodixie", "note_type": "info", "content": "Market"},
        )

        response = test_client.get("/api/v1/notes/search?query=trade")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_count"] == 2
        assert len(data["items"]) == 2

    def test_search_requires_query(self, test_client):
        """Test that search requires query parameter."""
        response = test_client.get("/api/v1/notes/search")

        assert response.status_code == 422


class TestClearSystemNotesEndpoint:
    """Tests for DELETE /api/v1/notes/system/{system_name}."""

    def test_clear_system_notes(self, test_client):
        """Test clearing all notes for a system."""
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Note 1"},
        )
        test_client.post(
            "/api/v1/notes/",
            json={"system_name": "Jita", "note_type": "info", "content": "Note 2"},
        )

        response = test_client.delete("/api/v1/notes/system/Jita")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"

        # Verify cleared
        get_response = test_client.get("/api/v1/notes/system/Jita")
        assert get_response.json()["total_notes"] == 0
