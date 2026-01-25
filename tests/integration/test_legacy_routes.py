"""Integration tests for legacy /systems and /map routes."""

import pytest


class TestLegacySystemsRoutes:
    """Tests for /systems legacy endpoints."""

    def test_list_systems(self, test_client):
        """Test GET /systems/ returns list of systems."""
        response = test_client.get("/systems/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check structure of first system
        system = data[0]
        assert "name" in system
        assert "security" in system
        assert "category" in system
        assert "region_id" in system

    def test_system_risk(self, test_client):
        """Test GET /systems/{name}/risk returns risk report."""
        response = test_client.get("/systems/Jita/risk")

        assert response.status_code == 200
        data = response.json()
        assert "system_name" in data
        assert "score" in data  # Risk score field
        assert "category" in data
        assert "breakdown" in data

    def test_system_risk_not_found(self, test_client):
        """Test GET /systems/{name}/risk returns 404 for unknown system."""
        response = test_client.get("/systems/NotARealSystem/risk")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_system_neighbors(self, test_client):
        """Test GET /systems/{name}/neighbors returns list of connected systems."""
        response = test_client.get("/systems/Jita/neighbors")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Jita should have neighbors
        assert len(data) > 0
        # All items should be strings (system names)
        assert all(isinstance(name, str) for name in data)

    def test_system_neighbors_not_found(self, test_client):
        """Test GET /systems/{name}/neighbors returns 404 for unknown system."""
        response = test_client.get("/systems/FakeSystem/neighbors")

        assert response.status_code == 404


class TestLegacyMapRoutes:
    """Tests for /map legacy endpoints."""

    def test_map_config(self, test_client):
        """Test GET /map/config returns map configuration."""
        response = test_client.get("/map/config")

        assert response.status_code == 200
        data = response.json()

        assert "metadata" in data
        assert "systems" in data
        assert "layers" in data

        # Check metadata structure
        assert "version" in data["metadata"]

        # Check systems have expected fields
        if data["systems"]:
            system = list(data["systems"].values())[0]
            assert "id" in system
            assert "security" in system
            assert "risk_score" in system
            assert "risk_color" in system

    def test_map_route_shortest(self, test_client):
        """Test GET /map/route with shortest profile."""
        response = test_client.get("/map/route", params={
            "from": "Jita",
            "to": "Amarr",
            "profile": "shortest",
        })

        assert response.status_code == 200
        data = response.json()

        assert "path" in data
        assert isinstance(data["path"], list)
        assert len(data["path"]) >= 2
        # Path contains system info objects
        assert data["path"][0]["system_name"] == "Jita"
        assert data["path"][-1]["system_name"] == "Amarr"

    def test_map_route_safer(self, test_client):
        """Test GET /map/route with safer profile."""
        response = test_client.get("/map/route", params={
            "from": "Jita",
            "to": "Amarr",
            "profile": "safer",
        })

        assert response.status_code == 200
        data = response.json()
        assert "path" in data

    def test_map_route_paranoid(self, test_client):
        """Test GET /map/route with paranoid profile."""
        response = test_client.get("/map/route", params={
            "from": "Jita",
            "to": "Amarr",
            "profile": "paranoid",
        })

        assert response.status_code == 200
        data = response.json()
        assert "path" in data

    def test_map_route_invalid_profile(self, test_client):
        """Test GET /map/route with invalid profile returns 400."""
        response = test_client.get("/map/route", params={
            "from": "Jita",
            "to": "Amarr",
            "profile": "invalid_profile",
        })

        assert response.status_code == 400
        assert "Unknown routing profile" in response.json()["detail"]

    def test_map_route_invalid_system(self, test_client):
        """Test GET /map/route with invalid system returns 400."""
        response = test_client.get("/map/route", params={
            "from": "FakeSystem",
            "to": "Amarr",
            "profile": "shortest",
        })

        assert response.status_code == 400
