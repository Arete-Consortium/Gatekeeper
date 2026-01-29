"""Integration tests for systems API endpoints."""


class TestSystemsListEndpoint:
    """Tests for /api/v1/systems/ endpoint."""

    def test_list_systems(self, test_client):
        """Test listing all systems with pagination."""
        response = test_client.get("/api/v1/systems/")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        assert "pagination" in data
        assert isinstance(data["items"], list)
        assert data["pagination"]["total_count"] >= 3  # At least Jita, Perimeter, Niarja

    def test_list_systems_has_required_fields(self, test_client):
        """Test that systems have required fields."""
        response = test_client.get("/api/v1/systems/")
        data = response.json()

        for system in data["items"]:
            assert "name" in system
            assert "security" in system
            assert "category" in system
            assert "region_id" in system


class TestSystemDetailEndpoint:
    """Tests for /api/v1/systems/{name} endpoint."""

    def test_get_system_jita(self, test_client):
        """Test getting Jita system details."""
        response = test_client.get("/api/v1/systems/Jita")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Jita"
        assert data["category"] == "highsec"

    def test_get_system_not_found(self, test_client):
        """Test getting nonexistent system returns 404."""
        response = test_client.get("/api/v1/systems/NonExistent")
        assert response.status_code == 404


class TestSystemRiskEndpoint:
    """Tests for /api/v1/systems/{name}/risk endpoint."""

    def test_get_system_risk(self, test_client):
        """Test getting system risk report."""
        response = test_client.get("/api/v1/systems/Jita/risk")
        assert response.status_code == 200

        data = response.json()
        assert data["system_name"] == "Jita"
        assert "score" in data
        assert "breakdown" in data
        assert 0 <= data["score"] <= 100

    def test_get_system_risk_not_found(self, test_client):
        """Test getting risk for nonexistent system returns 404."""
        response = test_client.get("/api/v1/systems/NonExistent/risk")
        assert response.status_code == 404


class TestSystemNeighborsEndpoint:
    """Tests for /api/v1/systems/{name}/neighbors endpoint."""

    def test_get_system_neighbors(self, test_client):
        """Test getting system neighbors."""
        response = test_client.get("/api/v1/systems/Jita/neighbors")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert "Perimeter" in data

    def test_get_system_neighbors_not_found(self, test_client):
        """Test getting neighbors for nonexistent system returns 404."""
        response = test_client.get("/api/v1/systems/NonExistent/neighbors")
        assert response.status_code == 404
