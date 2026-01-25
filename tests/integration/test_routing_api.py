"""Integration tests for routing API endpoints."""


class TestRouteEndpoint:
    """Tests for /api/v1/route/ endpoint."""

    def test_calculate_route(self, test_client):
        """Test calculating a basic route."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Perimeter&profile=shortest")
        assert response.status_code == 200

        data = response.json()
        assert data["from_system"] == "Jita"
        assert data["to_system"] == "Perimeter"
        assert data["profile"] == "shortest"
        assert data["total_jumps"] == 1

    def test_calculate_route_multi_hop(self, test_client):
        """Test calculating a multi-hop route."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Urlen&profile=shortest")
        assert response.status_code == 200

        data = response.json()
        assert data["total_jumps"] == 2
        assert len(data["path"]) == 3

    def test_calculate_route_path_structure(self, test_client):
        """Test that route path has proper structure."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Urlen&profile=shortest")
        data = response.json()

        for hop in data["path"]:
            assert "system_name" in hop
            assert "system_id" in hop
            assert "cumulative_jumps" in hop
            assert "risk_score" in hop

    def test_calculate_route_different_profiles(self, test_client):
        """Test calculating routes with different profiles."""
        shortest = test_client.get("/api/v1/route/?from=Jita&to=Urlen&profile=shortest").json()
        safer = test_client.get("/api/v1/route/?from=Jita&to=Urlen&profile=safer").json()
        paranoid = test_client.get("/api/v1/route/?from=Jita&to=Urlen&profile=paranoid").json()

        # All should complete successfully
        assert shortest["total_jumps"] >= 1
        assert safer["total_jumps"] >= 1
        assert paranoid["total_jumps"] >= 1

    def test_calculate_route_unknown_from(self, test_client):
        """Test route with unknown origin returns 400."""
        response = test_client.get("/api/v1/route/?from=NonExistent&to=Jita&profile=shortest")
        assert response.status_code == 400

    def test_calculate_route_unknown_to(self, test_client):
        """Test route with unknown destination returns 400."""
        response = test_client.get("/api/v1/route/?from=Jita&to=NonExistent&profile=shortest")
        assert response.status_code == 400

    def test_calculate_route_unknown_profile(self, test_client):
        """Test route with unknown profile returns 400."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Perimeter&profile=invalid")
        assert response.status_code == 400

    def test_calculate_route_with_avoid_single(self, test_client):
        """Test route with single system to avoid."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Urlen&profile=shortest&avoid=Perimeter")
        assert response.status_code == 200

        data = response.json()
        # Perimeter should not be in path
        path_names = [hop["system_name"] for hop in data["path"]]
        assert "Perimeter" not in path_names

    def test_calculate_route_with_avoid_comma_separated(self, test_client):
        """Test route with comma-separated avoid list."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Urlen&profile=shortest&avoid=Perimeter,Niyabainen")
        assert response.status_code == 200
        data = response.json()
        path_names = [hop["system_name"] for hop in data["path"]]
        assert "Perimeter" not in path_names

    def test_calculate_route_with_bridges_disabled(self, test_client):
        """Test route with bridges disabled (default)."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Perimeter&profile=shortest&bridges=false")
        assert response.status_code == 200

    def test_calculate_route_with_bridges_enabled(self, test_client):
        """Test route with bridges enabled."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Perimeter&profile=shortest&bridges=true")
        assert response.status_code == 200

    def test_route_same_system(self, test_client):
        """Test route from system to itself."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Jita&profile=shortest")
        assert response.status_code == 200
        data = response.json()
        assert data["total_jumps"] == 0


class TestMapConfigEndpoint:
    """Tests for /api/v1/route/config endpoint."""

    def test_get_map_config(self, test_client):
        """Test getting map configuration."""
        response = test_client.get("/api/v1/route/config")
        assert response.status_code == 200

        data = response.json()
        assert "metadata" in data
        assert "systems" in data
        assert "layers" in data

    def test_map_config_systems(self, test_client):
        """Test that map config contains system data."""
        response = test_client.get("/api/v1/route/config")
        data = response.json()

        assert "Jita" in data["systems"]
        jita = data["systems"]["Jita"]
        assert "risk_score" in jita
        assert "risk_color" in jita
        assert "security" in jita

    def test_map_config_routing_profiles(self, test_client):
        """Test that map config includes routing profiles."""
        response = test_client.get("/api/v1/route/config")
        data = response.json()

        assert "routing_profiles" in data
        assert "shortest" in data["routing_profiles"]
        assert "safer" in data["routing_profiles"]
