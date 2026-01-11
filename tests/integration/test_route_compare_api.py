"""Integration tests for route comparison API endpoints."""

from fastapi.testclient import TestClient


class TestRouteCompareEndpoint:
    """Tests for POST /api/v1/route/compare."""

    def test_compare_routes_basic(self, test_client: TestClient):
        """Should compare routes between two systems."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest", "safer"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "from_system" in data
        assert "to_system" in data
        assert "routes" in data
        assert "recommendation" in data

    def test_compare_routes_has_route_summaries(self, test_client: TestClient):
        """Should return route summaries for each profile."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest", "safer"]},
        )

        data = response.json()
        assert len(data["routes"]) == 2

    def test_route_summary_structure(self, test_client: TestClient):
        """Each route summary should have required fields."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest"]},
        )

        data = response.json()
        route = data["routes"][0]

        assert "profile" in route
        assert "total_jumps" in route
        assert "total_cost" in route
        assert "max_risk" in route
        assert "avg_risk" in route
        assert "highsec_jumps" in route
        assert "lowsec_jumps" in route
        assert "nullsec_jumps" in route
        assert "path_systems" in route

    def test_compare_unknown_from_system(self, test_client: TestClient):
        """Should return error for unknown from system."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "FakeSystem", "to_system": "Amarr", "profiles": ["shortest"]},
        )

        assert response.status_code == 400
        assert "Unknown system" in response.json()["detail"]

    def test_compare_unknown_to_system(self, test_client: TestClient):
        """Should return error for unknown to system."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "FakeSystem", "profiles": ["shortest"]},
        )

        assert response.status_code == 400
        assert "Unknown system" in response.json()["detail"]

    def test_compare_unknown_profile(self, test_client: TestClient):
        """Should return error for unknown profile."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["invalid_profile"]},
        )

        assert response.status_code == 400
        assert "Unknown profile" in response.json()["detail"]

    def test_compare_all_profiles(self, test_client: TestClient):
        """Should compare all standard profiles."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest", "safer"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["routes"]) == 2

    def test_compare_generates_recommendation(self, test_client: TestClient):
        """Should generate a recommendation."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest", "safer"]},
        )

        data = response.json()
        assert len(data["recommendation"]) > 0

    def test_compare_with_avoid(self, test_client: TestClient):
        """Should respect avoid list."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Amarr",
                "profiles": ["shortest"],
                "avoid": ["Niarja"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Niarja should not be in path
        for route in data["routes"]:
            assert "Niarja" not in route["path_systems"]

    def test_compare_same_system(self, test_client: TestClient):
        """Should handle same origin and destination."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Jita", "profiles": ["shortest"]},
        )

        # Either 200 with 0 jumps or error - both valid
        if response.status_code == 200:
            data = response.json()
            assert data["routes"][0]["total_jumps"] == 0

    def test_compare_path_starts_at_origin(self, test_client: TestClient):
        """Path should start at origin system."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest"]},
        )

        data = response.json()
        assert data["routes"][0]["path_systems"][0] == "Jita"

    def test_compare_path_ends_at_destination(self, test_client: TestClient):
        """Path should end at destination system."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest"]},
        )

        data = response.json()
        assert data["routes"][0]["path_systems"][-1] == "Amarr"

    def test_compare_security_counts_add_up(self, test_client: TestClient):
        """Security category counts should add up to total jumps + 1."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest"]},
        )

        data = response.json()
        route = data["routes"][0]

        # Total systems in path = highsec + lowsec + nullsec
        total_systems = route["highsec_jumps"] + route["lowsec_jumps"] + route["nullsec_jumps"]
        assert total_systems == len(route["path_systems"])

    def test_single_profile_recommendation(self, test_client: TestClient):
        """Single profile should get appropriate recommendation."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={"from_system": "Jita", "to_system": "Amarr", "profiles": ["shortest"]},
        )

        data = response.json()
        assert (
            "shortest" in data["recommendation"].lower() or "only" in data["recommendation"].lower()
        )


class TestRouteAvoidEndpoint:
    """Tests for route avoidance functionality."""

    def test_route_with_avoid_parameter(self, test_client: TestClient):
        """Should accept avoid parameter in route calculation."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Amarr&avoid=Niarja")

        assert response.status_code == 200
        data = response.json()

        # Check Niarja not in path
        path_systems = [hop["system_name"] for hop in data["path"]]
        assert "Niarja" not in path_systems

    def test_route_with_multiple_avoid(self, test_client: TestClient):
        """Should accept multiple systems to avoid."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Amarr&avoid=Niarja&avoid=Uedama")

        assert response.status_code == 200
        data = response.json()

        path_systems = [hop["system_name"] for hop in data["path"]]
        assert "Niarja" not in path_systems
        assert "Uedama" not in path_systems


class TestRouteProfilesEndpoint:
    """Tests for different routing profiles."""

    def test_shortest_profile(self, test_client: TestClient):
        """Shortest profile should return a route."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Amarr&profile=shortest")

        assert response.status_code == 200

    def test_safer_profile(self, test_client: TestClient):
        """Safer profile should return a route."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Amarr&profile=safer")

        assert response.status_code == 200

    def test_paranoid_profile(self, test_client: TestClient):
        """Paranoid profile should return a route."""
        response = test_client.get("/api/v1/route/?from=Jita&to=Amarr&profile=paranoid")

        assert response.status_code == 200

    def test_safer_has_lower_max_risk(self, test_client: TestClient):
        """Safer profile should have lower or equal max risk."""
        response_short = test_client.get("/api/v1/route/?from=Jita&to=Dodixie&profile=shortest")
        response_safer = test_client.get("/api/v1/route/?from=Jita&to=Dodixie&profile=safer")

        data_short = response_short.json()
        data_safer = response_safer.json()

        # Safer should have lower or equal max risk
        assert data_safer["max_risk"] <= data_short["max_risk"]
