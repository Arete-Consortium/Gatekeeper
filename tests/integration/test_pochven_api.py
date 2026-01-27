"""Integration tests for Pochven filament routing API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.services.pochven import _state


@pytest.fixture(autouse=True)
def _reset_pochven():
    """Reset Pochven state before each test."""
    _state["enabled"] = True
    yield
    _state["enabled"] = True


class TestListPochvenEndpoint:
    """Tests for GET /api/v1/pochven/."""

    def test_returns_connections(self, test_client: TestClient):
        response = test_client.get("/api/v1/pochven/")
        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        assert "enabled" in data
        assert isinstance(data["connections"], list)
        assert len(data["connections"]) > 0

    def test_connections_have_required_fields(self, test_client: TestClient):
        response = test_client.get("/api/v1/pochven/")
        data = response.json()
        for conn in data["connections"]:
            assert "from_system" in conn
            assert "to_system" in conn
            assert "connection_type" in conn
            assert "bidirectional" in conn


class TestPochvenStatusEndpoint:
    """Tests for GET /api/v1/pochven/status."""

    def test_status_enabled(self, test_client: TestClient):
        response = test_client.get("/api/v1/pochven/status")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["connection_count"] > 0
        assert data["system_count"] > 0

    def test_status_after_disable(self, test_client: TestClient):
        test_client.patch("/api/v1/pochven/", json={"enabled": False})
        response = test_client.get("/api/v1/pochven/status")
        assert response.status_code == 200
        assert response.json()["enabled"] is False


class TestTogglePochvenEndpoint:
    """Tests for PATCH /api/v1/pochven/."""

    def test_disable(self, test_client: TestClient):
        response = test_client.patch("/api/v1/pochven/", json={"enabled": False})
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_enable(self, test_client: TestClient):
        test_client.patch("/api/v1/pochven/", json={"enabled": False})
        response = test_client.patch("/api/v1/pochven/", json={"enabled": True})
        assert response.status_code == 200
        assert response.json()["enabled"] is True


class TestRoutingWithPochven:
    """Tests for routing with pochven=true parameter."""

    def test_route_with_pochven_param(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/route/",
            params={"from": "Jita", "to": "Perimeter", "pochven": True},
        )
        assert response.status_code == 200

    def test_route_without_pochven_default(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/route/",
            params={"from": "Jita", "to": "Perimeter"},
        )
        assert response.status_code == 200
        assert "pochven_used" in response.json()
        assert response.json()["pochven_used"] == 0

    def test_route_response_has_pochven_used(self, test_client: TestClient):
        response = test_client.get(
            "/api/v1/route/",
            params={"from": "Jita", "to": "Perimeter", "pochven": True},
        )
        assert response.status_code == 200
        assert "pochven_used" in response.json()

    def test_compare_routes_with_pochven(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
                "profiles": ["shortest"],
                "use_pochven": True,
            },
        )
        assert response.status_code == 200

    def test_bulk_routes_with_pochven(self, test_client: TestClient):
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Perimeter"],
                "use_pochven": True,
            },
        )
        assert response.status_code == 200
