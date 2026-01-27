"""Integration tests for avoidance list API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolate_avoidance(tmp_path, monkeypatch):
    """Isolate avoidance config to tmp_path for each test."""
    from backend.app.services.avoidance import clear_avoidance_cache

    config_path = tmp_path / "avoidance_lists.json"
    monkeypatch.setattr(
        "backend.app.services.avoidance.get_avoidance_config_path",
        lambda: config_path,
    )
    clear_avoidance_cache()
    yield
    clear_avoidance_cache()


class TestListAvoidanceLists:
    """Tests for GET /api/v1/avoidance/."""

    def test_list_empty(self, test_client: TestClient):
        response = test_client.get("/api/v1/avoidance/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_after_create(self, test_client: TestClient):
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "gatecamps", "systems": ["Tama", "Rancer"]},
        )
        response = test_client.get("/api/v1/avoidance/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "gatecamps"


class TestCreateAvoidanceList:
    """Tests for POST /api/v1/avoidance/."""

    def test_create(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/avoidance/",
            json={"name": "gatecamps", "systems": ["Tama", "Rancer"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "gatecamps"
        assert set(data["systems"]) == {"Tama", "Rancer"}

    def test_create_duplicate_returns_409(self, test_client: TestClient):
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "gatecamps", "systems": ["Tama"]},
        )
        response = test_client.post(
            "/api/v1/avoidance/",
            json={"name": "gatecamps", "systems": ["Rancer"]},
        )
        assert response.status_code == 409

    def test_create_with_description(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/avoidance/",
            json={
                "name": "pipe",
                "systems": ["Tama"],
                "description": "Lowsec pipe",
            },
        )
        assert response.status_code == 201
        assert response.json()["description"] == "Lowsec pipe"

    def test_create_empty_name_rejected(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/avoidance/",
            json={"name": "", "systems": ["Tama"]},
        )
        assert response.status_code == 422

    def test_create_empty_systems_rejected(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/avoidance/",
            json={"name": "test", "systems": []},
        )
        assert response.status_code == 422


class TestGetAvoidanceList:
    """Tests for GET /api/v1/avoidance/{name}."""

    def test_get_existing(self, test_client: TestClient):
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "gatecamps", "systems": ["Tama", "Rancer"]},
        )
        response = test_client.get("/api/v1/avoidance/gatecamps")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "gatecamps"
        assert set(data["systems"]) == {"Tama", "Rancer"}

    def test_get_nonexistent_returns_404(self, test_client: TestClient):
        response = test_client.get("/api/v1/avoidance/nonexistent")
        assert response.status_code == 404


class TestUpdateAvoidanceList:
    """Tests for PUT /api/v1/avoidance/{name}."""

    def test_update_systems(self, test_client: TestClient):
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "test", "systems": ["Tama"]},
        )
        response = test_client.put(
            "/api/v1/avoidance/test",
            json={"systems": ["Rancer", "Amamake"]},
        )
        assert response.status_code == 200
        assert set(response.json()["systems"]) == {"Rancer", "Amamake"}

    def test_update_add_systems(self, test_client: TestClient):
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "test", "systems": ["Tama"]},
        )
        response = test_client.put(
            "/api/v1/avoidance/test",
            json={"add_systems": ["Rancer"]},
        )
        assert response.status_code == 200
        assert set(response.json()["systems"]) == {"Tama", "Rancer"}

    def test_update_remove_systems(self, test_client: TestClient):
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "test", "systems": ["Tama", "Rancer"]},
        )
        response = test_client.put(
            "/api/v1/avoidance/test",
            json={"remove_systems": ["Tama"]},
        )
        assert response.status_code == 200
        assert response.json()["systems"] == ["Rancer"]

    def test_update_nonexistent_returns_404(self, test_client: TestClient):
        response = test_client.put(
            "/api/v1/avoidance/nonexistent",
            json={"systems": ["Tama"]},
        )
        assert response.status_code == 404


class TestDeleteAvoidanceList:
    """Tests for DELETE /api/v1/avoidance/{name}."""

    def test_delete_existing(self, test_client: TestClient):
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "test", "systems": ["Tama"]},
        )
        response = test_client.delete("/api/v1/avoidance/test")
        assert response.status_code == 200
        assert response.json()["deleted"] == "test"

        # Verify deleted
        assert test_client.get("/api/v1/avoidance/test").status_code == 404

    def test_delete_nonexistent_returns_404(self, test_client: TestClient):
        response = test_client.delete("/api/v1/avoidance/nonexistent")
        assert response.status_code == 404


class TestRoutingWithAvoidLists:
    """Tests for routing integration with avoid_lists parameter."""

    def test_route_with_avoid_lists_param(self, test_client: TestClient):
        """Should accept avoid_lists query parameter."""
        # Create an avoidance list
        test_client.post(
            "/api/v1/avoidance/",
            json={"name": "gatecamps", "systems": ["Rancer"]},
        )

        # Use it in routing
        response = test_client.get("/api/v1/route/?from=Jita&to=Amarr&avoid_lists=gatecamps")
        # Should succeed (200) or 400 if route blocked, but not 422
        assert response.status_code in (200, 400)

    def test_route_with_unknown_avoid_list(self, test_client: TestClient):
        """Should return 400 for unknown avoidance list."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Amarr&avoid_lists=nonexistent")
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()
