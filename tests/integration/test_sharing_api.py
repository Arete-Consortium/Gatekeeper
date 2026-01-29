"""Integration tests for route sharing API endpoints."""

import pytest

from backend.app.services.route_sharing import reset_share_store


@pytest.fixture(autouse=True)
def reset_store():
    """Reset share store before each test."""
    reset_share_store()
    yield
    reset_share_store()


@pytest.fixture
def sample_route_data():
    """Sample route data for testing."""
    return {
        "from_system": "Jita",
        "to_system": "Amarr",
        "profile": "safer",
        "total_jumps": 15,
        "path": [
            {"system_name": "Jita", "security": 0.95},
            {"system_name": "Perimeter", "security": 0.94},
            {"system_name": "Urlen", "security": 0.87},
            {"system_name": "Amarr", "security": 1.0},
        ],
    }


class TestCreateShareEndpoint:
    """Tests for POST /api/v1/share/."""

    def test_create_share(self, test_client, sample_route_data):
        """Test creating a shared route."""
        response = test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data},
        )

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["from_system"] == "Jita"
        assert data["to_system"] == "Amarr"

    def test_create_share_with_creator(self, test_client, sample_route_data):
        """Test creating share with creator name."""
        response = test_client.post(
            "/api/v1/share/",
            json={
                "route_data": sample_route_data,
                "creator_name": "TestPilot",
                "description": "My favorite route",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["creator_name"] == "TestPilot"
        assert data["description"] == "My favorite route"

    def test_create_share_with_ttl(self, test_client, sample_route_data):
        """Test creating share with custom TTL."""
        response = test_client.post(
            "/api/v1/share/",
            json={
                "route_data": sample_route_data,
                "ttl_hours": 48,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is not None


class TestGetShareEndpoint:
    """Tests for GET /api/v1/share/{token}."""

    def test_get_share(self, test_client, sample_route_data):
        """Test getting a shared route."""
        # Create
        create_response = test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data},
        )
        token = create_response.json()["token"]

        # Get
        response = test_client.get(f"/api/v1/share/{token}")

        assert response.status_code == 200
        data = response.json()
        assert data["token"] == token
        assert "route_data" in data
        assert data["route_data"]["from_system"] == "Jita"

    def test_get_nonexistent_share(self, test_client):
        """Test getting nonexistent share returns 404."""
        response = test_client.get("/api/v1/share/nonexistent")

        assert response.status_code == 404

    def test_get_increments_access_count(self, test_client, sample_route_data):
        """Test that getting share increments access count."""
        # Create
        create_response = test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data},
        )
        token = create_response.json()["token"]

        # Get multiple times
        test_client.get(f"/api/v1/share/{token}")
        test_client.get(f"/api/v1/share/{token}")
        response = test_client.get(f"/api/v1/share/{token}")

        data = response.json()
        assert data["access_count"] == 3


class TestDeleteShareEndpoint:
    """Tests for DELETE /api/v1/share/{token}."""

    def test_delete_share(self, test_client, sample_route_data):
        """Test deleting a shared route."""
        # Create
        create_response = test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data},
        )
        token = create_response.json()["token"]

        # Delete
        response = test_client.delete(f"/api/v1/share/{token}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

        # Verify deleted
        get_response = test_client.get(f"/api/v1/share/{token}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_share(self, test_client):
        """Test deleting nonexistent share returns 404."""
        response = test_client.delete("/api/v1/share/nonexistent")

        assert response.status_code == 404


class TestListSharesEndpoint:
    """Tests for GET /api/v1/share/."""

    def test_list_shares_empty(self, test_client):
        """Test listing shares when empty."""
        response = test_client.get("/api/v1/share/")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_count"] == 0
        assert data["items"] == []

    def test_list_shares(self, test_client, sample_route_data):
        """Test listing shares."""
        # Create some shares
        test_client.post("/api/v1/share/", json={"route_data": sample_route_data})
        test_client.post("/api/v1/share/", json={"route_data": sample_route_data})
        test_client.post("/api/v1/share/", json={"route_data": sample_route_data})

        response = test_client.get("/api/v1/share/")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_count"] == 3

    def test_list_shares_by_creator(self, test_client, sample_route_data):
        """Test listing shares filtered by creator."""
        test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data, "creator_name": "Alice"},
        )
        test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data, "creator_name": "Bob"},
        )
        test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data, "creator_name": "Alice"},
        )

        response = test_client.get("/api/v1/share/?creator=Alice")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total_count"] == 2

    def test_list_shares_with_page_size(self, test_client, sample_route_data):
        """Test listing shares with page_size."""
        for _ in range(10):
            test_client.post("/api/v1/share/", json={"route_data": sample_route_data})

        response = test_client.get("/api/v1/share/?page_size=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["pagination"]["page_size"] == 5


class TestExportEndpoints:
    """Tests for export endpoints."""

    def test_export_text(self, test_client, sample_route_data):
        """Test exporting as text."""
        response = test_client.post(
            "/api/v1/share/export/text",
            json=sample_route_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "text"
        assert "Jita -> Amarr" in data["content"]

    def test_export_json(self, test_client, sample_route_data):
        """Test exporting as JSON."""
        response = test_client.post(
            "/api/v1/share/export/json",
            json=sample_route_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"

    def test_export_json_pretty(self, test_client, sample_route_data):
        """Test exporting as pretty JSON."""
        response = test_client.post(
            "/api/v1/share/export/json?pretty=true",
            json=sample_route_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "\n" in data["content"]  # Pretty has newlines

    def test_export_waypoints(self, test_client, sample_route_data):
        """Test exporting as waypoint list."""
        response = test_client.post(
            "/api/v1/share/export/waypoints",
            json=sample_route_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["systems"] == ["Jita", "Perimeter", "Urlen", "Amarr"]

    def test_export_dotlan(self, test_client, sample_route_data):
        """Test exporting as Dotlan URL."""
        response = test_client.post(
            "/api/v1/share/export/dotlan",
            json=sample_route_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "evemaps.dotlan.net" in data["content"]

    def test_export_eveeye(self, test_client, sample_route_data):
        """Test exporting as EVE Eye URL."""
        response = test_client.post(
            "/api/v1/share/export/eveeye",
            json=sample_route_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "eveeye.com" in data["content"]

    def test_export_all_formats(self, test_client, sample_route_data):
        """Test exporting in all formats."""
        response = test_client.post(
            "/api/v1/share/export/all",
            json=sample_route_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "json" in data
        assert "waypoint_systems" in data
        assert "dotlan_url" in data
        assert "eveeye_url" in data

    def test_export_shared_route(self, test_client, sample_route_data):
        """Test exporting a shared route."""
        # Create share
        create_response = test_client.post(
            "/api/v1/share/",
            json={"route_data": sample_route_data},
        )
        token = create_response.json()["token"]

        # Export
        response = test_client.get(f"/api/v1/share/{token}/export")

        assert response.status_code == 200
        data = response.json()
        assert "text" in data
        assert "Jita" in data["text"]

    def test_export_nonexistent_shared_route(self, test_client):
        """Test exporting nonexistent share returns 404."""
        response = test_client.get("/api/v1/share/nonexistent/export")

        assert response.status_code == 404
