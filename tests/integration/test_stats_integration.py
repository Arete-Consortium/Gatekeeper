"""Integration tests for stats API endpoints."""


class TestSystemStatsEndpoint:
    """Tests for /api/v1/stats/system/{name} endpoint."""

    def test_get_system_stats(self, test_client):
        """Test getting stats for a system."""
        response = test_client.get("/api/v1/stats/system/Jita")
        assert response.status_code == 200

        data = response.json()
        assert data["system_name"] == "Jita"
        assert "system_id" in data
        assert "stats" in data
        assert "recent_kills" in data["stats"]
        assert "recent_pods" in data["stats"]
        assert "hours" in data

    def test_get_system_stats_custom_hours(self, test_client):
        """Test getting stats with custom time window."""
        response = test_client.get("/api/v1/stats/system/Jita?hours=48")
        assert response.status_code == 200

        data = response.json()
        assert data["hours"] == 48

    def test_get_system_stats_not_found(self, test_client):
        """Test getting stats for nonexistent system returns 404."""
        response = test_client.get("/api/v1/stats/system/NonExistentSystem")
        assert response.status_code == 404


class TestBulkStatsEndpoint:
    """Tests for /api/v1/stats/bulk endpoint."""

    def test_bulk_stats(self, test_client):
        """Test getting stats for multiple systems."""
        response = test_client.post("/api/v1/stats/bulk", json={"systems": ["Jita", "Perimeter"]})
        assert response.status_code == 200

        data = response.json()
        assert "stats" in data
        assert "Jita" in data["stats"]
        assert "Perimeter" in data["stats"]

    def test_bulk_stats_with_hours(self, test_client):
        """Test bulk stats with custom hours."""
        response = test_client.post("/api/v1/stats/bulk", json={"systems": ["Jita"], "hours": 12})
        assert response.status_code == 200
        assert response.json()["hours"] == 12

    def test_bulk_stats_empty_list_validation(self, test_client):
        """Test bulk stats requires at least one system."""
        response = test_client.post("/api/v1/stats/bulk", json={"systems": []})
        # Validation error - min_length=1
        assert response.status_code == 422

    def test_bulk_stats_rejects_unknown_system(self, test_client):
        """Test that bulk stats rejects unknown systems."""
        response = test_client.post(
            "/api/v1/stats/bulk", json={"systems": ["Jita", "NonExistentSystem"]}
        )
        # Returns 400 for unknown system
        assert response.status_code == 400

    def test_bulk_stats_response_structure(self, test_client):
        """Test bulk stats response has correct structure."""
        response = test_client.post("/api/v1/stats/bulk", json={"systems": ["Jita"]})
        assert response.status_code == 200

        data = response.json()
        assert "hours" in data
        assert "total_systems" in data
        assert "stats" in data


class TestHotSystemsEndpoint:
    """Tests for /api/v1/stats/hot endpoint."""

    def test_get_hot_systems(self, test_client):
        """Test getting hot systems."""
        response = test_client.get("/api/v1/stats/hot")
        assert response.status_code == 200

        data = response.json()
        assert "systems" in data
        assert isinstance(data["systems"], list)

    def test_hot_systems_with_custom_hours(self, test_client):
        """Test hot systems with custom hours."""
        response = test_client.get("/api/v1/stats/hot?hours=48")
        assert response.status_code == 200
        assert response.json()["hours"] == 48

    def test_hot_systems_have_required_fields(self, test_client):
        """Test that hot systems have required fields."""
        response = test_client.get("/api/v1/stats/hot")
        data = response.json()

        for system in data["systems"]:
            assert "system_id" in system
            assert "system_name" in system
            assert "security" in system
            assert "category" in system
            assert "recent_kills" in system
            assert "recent_pods" in system
            assert "total_activity" in system
            assert system["category"] in ("high_sec", "low_sec", "null_sec")

    def test_hot_systems_sorted_by_activity(self, test_client):
        """Test that hot systems are sorted by activity descending."""
        response = test_client.get("/api/v1/stats/hot")
        data = response.json()

        systems = data["systems"]
        if len(systems) >= 2:
            for i in range(len(systems) - 1):
                assert systems[i]["total_activity"] >= systems[i + 1]["total_activity"]
