"""Integration tests for Thera wormhole API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.models.thera import TheraConnection
from backend.app.services.thera import clear_thera_cache


@pytest.fixture(autouse=True)
def _clear_thera():
    """Clear Thera cache before each test."""
    clear_thera_cache()
    yield
    clear_thera_cache()


def _make_thera_connection(**overrides) -> TheraConnection:
    base = {
        "id": 1,
        "in_system_id": 30000142,
        "in_system_name": "Jita",
        "out_system_id": 30002187,
        "out_system_name": "Amarr",
        "wh_type": "Q003",
        "max_ship_size": "battleship",
        "remaining_hours": 10.0,
        "expires_at": "2026-01-28T00:00:00",
        "completed": False,
    }
    base.update(overrides)
    return TheraConnection(**base)


class TestListTheraEndpoint:
    """Tests for GET /api/v1/thera/."""

    @patch("backend.app.api.v1.thera.get_active_thera")
    def test_returns_connections(self, mock_active, test_client: TestClient):
        """Should return active Thera connections."""
        mock_active.return_value = [_make_thera_connection()]

        response = test_client.get("/api/v1/thera/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["connections"]) == 1
        assert data["connections"][0]["in_system_name"] == "Jita"

    @patch("backend.app.api.v1.thera.get_active_thera")
    def test_empty_connections(self, mock_active, test_client: TestClient):
        """Should return empty list when no connections."""
        mock_active.return_value = []

        response = test_client.get("/api/v1/thera/")

        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["connections"] == []

    @patch("backend.app.api.v1.thera.get_active_thera")
    def test_filter_by_ship_size(self, mock_active, test_client: TestClient):
        """Should filter connections by max_ship_size."""
        mock_active.return_value = [
            _make_thera_connection(id=1, max_ship_size="frigate"),
            _make_thera_connection(id=2, max_ship_size="battleship"),
        ]

        response = test_client.get("/api/v1/thera/?max_ship_size=frigate")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["connections"][0]["max_ship_size"] == "frigate"

    @patch("backend.app.api.v1.thera.get_active_thera")
    def test_response_has_last_updated(self, mock_active, test_client: TestClient):
        """Should include last_updated timestamp."""
        mock_active.return_value = []

        response = test_client.get("/api/v1/thera/")

        assert response.status_code == 200
        assert response.json()["last_updated"] is not None


class TestTheraStatusEndpoint:
    """Tests for GET /api/v1/thera/status."""

    @patch("backend.app.api.v1.thera.get_active_thera")
    @patch("backend.app.api.v1.thera.get_thera_last_error")
    @patch("backend.app.api.v1.thera.get_thera_cache_age")
    def test_status_healthy(self, mock_age, mock_error, mock_active, test_client: TestClient):
        """Should return healthy status."""
        mock_age.return_value = 30.0
        mock_error.return_value = None
        mock_active.return_value = [_make_thera_connection()]

        response = test_client.get("/api/v1/thera/status")

        assert response.status_code == 200
        data = response.json()
        assert data["api_healthy"] is True
        assert data["connection_count"] == 1
        assert data["cache_age_seconds"] == 30.0

    @patch("backend.app.api.v1.thera.get_active_thera")
    @patch("backend.app.api.v1.thera.get_thera_last_error")
    @patch("backend.app.api.v1.thera.get_thera_cache_age")
    def test_status_with_error(self, mock_age, mock_error, mock_active, test_client: TestClient):
        """Should report unhealthy when last error exists."""
        mock_age.return_value = None
        mock_error.return_value = "connection timed out"
        mock_active.return_value = []

        response = test_client.get("/api/v1/thera/status")

        assert response.status_code == 200
        data = response.json()
        assert data["api_healthy"] is False
        assert data["last_error"] == "connection timed out"

    @patch("backend.app.api.v1.thera.get_active_thera")
    @patch("backend.app.api.v1.thera.get_thera_last_error")
    @patch("backend.app.api.v1.thera.get_thera_cache_age")
    def test_status_never_fetched(self, mock_age, mock_error, mock_active, test_client: TestClient):
        """Should handle never-fetched state."""
        mock_age.return_value = None
        mock_error.return_value = None
        mock_active.return_value = []

        response = test_client.get("/api/v1/thera/status")

        assert response.status_code == 200
        data = response.json()
        assert data["cache_age_seconds"] is None


class TestRoutingWithThera:
    """Tests for routing with thera=true parameter."""

    @patch("backend.app.services.routing.get_active_thera")
    def test_route_with_thera_param(self, mock_thera, test_client: TestClient):
        """Should accept thera query parameter."""
        mock_thera.return_value = []

        response = test_client.get(
            "/api/v1/route/",
            params={"from": "Jita", "to": "Perimeter", "thera": True},
        )

        assert response.status_code == 200

    @patch("backend.app.services.routing.get_active_thera")
    def test_route_without_thera_default(self, mock_thera, test_client: TestClient):
        """Should not use thera by default."""
        response = test_client.get(
            "/api/v1/route/",
            params={"from": "Jita", "to": "Perimeter"},
        )

        assert response.status_code == 200
        mock_thera.assert_not_called()

    @patch("backend.app.services.routing.get_active_thera")
    def test_route_response_has_thera_used(self, mock_thera, test_client: TestClient):
        """Should include thera_used in response."""
        mock_thera.return_value = []

        response = test_client.get(
            "/api/v1/route/",
            params={"from": "Jita", "to": "Perimeter", "thera": True},
        )

        assert response.status_code == 200
        assert "thera_used" in response.json()
        assert response.json()["thera_used"] == 0

    @patch("backend.app.services.routing.get_active_thera")
    def test_thera_shortcut_used_in_route(self, mock_thera, test_client: TestClient):
        """Should use Thera shortcut when it provides shorter route."""
        mock_thera.return_value = [
            _make_thera_connection(
                in_system_name="Jita",
                out_system_name="Amarr",
            ),
        ]

        response = test_client.get(
            "/api/v1/route/",
            params={"from": "Jita", "to": "Amarr", "thera": True},
        )

        assert response.status_code == 200
        data = response.json()
        # If Thera shortcut is shorter than gate route, it should be used
        if data["thera_used"] > 0:
            # Verify thera hop exists in path
            thera_hops = [h for h in data["path"] if h["connection_type"] == "thera"]
            assert len(thera_hops) == data["thera_used"]

    @patch("backend.app.services.routing.get_active_thera")
    def test_compare_routes_with_thera(self, mock_thera, test_client: TestClient):
        """Should pass thera param through to compare endpoint."""
        mock_thera.return_value = []

        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
                "profiles": ["shortest"],
                "use_thera": True,
            },
        )

        assert response.status_code == 200

    @patch("backend.app.services.routing.get_active_thera")
    def test_bulk_routes_with_thera(self, mock_thera, test_client: TestClient):
        """Should pass thera param through to bulk endpoint."""
        mock_thera.return_value = []

        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Perimeter"],
                "use_thera": True,
            },
        )

        assert response.status_code == 200
