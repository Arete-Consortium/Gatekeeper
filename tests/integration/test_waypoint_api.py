"""Integration tests for waypoint routing API endpoint."""


class TestWaypointEndpoint:
    """Tests for POST /api/v1/route/waypoints endpoint."""

    def test_waypoint_route_valid_request(self, test_client):
        """Test valid waypoint route request."""
        response = test_client.post(
            "/api/v1/route/waypoints",
            json={
                "from_system": "Jita",
                "waypoints": ["Perimeter", "Urlen"],
                "profile": "shortest",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["from_system"] == "Jita"
        assert data["waypoints"] == ["Perimeter", "Urlen"]
        assert len(data["legs"]) == 2
        assert data["total_jumps"] >= 2

    def test_waypoint_response_has_legs_structure(self, test_client):
        """Test response legs have proper structure."""
        response = test_client.post(
            "/api/v1/route/waypoints",
            json={
                "from_system": "Jita",
                "waypoints": ["Perimeter"],
            },
        )
        data = response.json()
        leg = data["legs"][0]

        assert "from_system" in leg
        assert "to_system" in leg
        assert "jumps" in leg
        assert "cost" in leg
        assert "path_systems" in leg
        assert "bridges_used" in leg
        assert "thera_used" in leg

    def test_waypoint_optimize_flag(self, test_client):
        """Test optimize flag is reflected in response."""
        response = test_client.post(
            "/api/v1/route/waypoints",
            json={
                "from_system": "Jita",
                "waypoints": ["Perimeter", "Urlen"],
                "optimize": True,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["optimized"] is True
        assert data["original_order"] == ["Perimeter", "Urlen"]

    def test_waypoint_unknown_system_400(self, test_client):
        """Test unknown system returns 400."""
        response = test_client.post(
            "/api/v1/route/waypoints",
            json={
                "from_system": "Jita",
                "waypoints": ["NonExistentSystem"],
            },
        )
        assert response.status_code == 400

    def test_waypoint_unknown_profile_400(self, test_client):
        """Test unknown profile returns 400."""
        response = test_client.post(
            "/api/v1/route/waypoints",
            json={
                "from_system": "Jita",
                "waypoints": ["Perimeter"],
                "profile": "invalid_profile",
            },
        )
        assert response.status_code == 400

    def test_waypoint_empty_waypoints_422(self, test_client):
        """Test empty waypoints list returns 422 validation error."""
        response = test_client.post(
            "/api/v1/route/waypoints",
            json={
                "from_system": "Jita",
                "waypoints": [],
            },
        )
        assert response.status_code == 422

    def test_waypoint_too_many_waypoints_422(self, test_client):
        """Test exceeding max waypoints returns 422 validation error."""
        response = test_client.post(
            "/api/v1/route/waypoints",
            json={
                "from_system": "Jita",
                "waypoints": [f"System{i}" for i in range(21)],
            },
        )
        assert response.status_code == 422
