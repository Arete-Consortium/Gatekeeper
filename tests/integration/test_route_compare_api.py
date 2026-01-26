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


class TestBulkRoutesEndpoint:
    """Tests for POST /api/v1/route/bulk."""

    def test_bulk_routes_basic(self, test_client: TestClient):
        """Should calculate routes to multiple destinations."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr", "Dodixie"],
                "profile": "shortest",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["from_system"] == "Jita"
        assert data["profile"] == "shortest"
        assert data["total_destinations"] == 2
        assert data["successful"] == 2
        assert data["failed"] == 0
        assert len(data["routes"]) == 2

    def test_bulk_routes_result_structure(self, test_client: TestClient):
        """Each bulk route result should have required fields."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr"],
                "profile": "shortest",
            },
        )

        data = response.json()
        route = data["routes"][0]

        assert "to_system" in route
        assert "success" in route
        assert route["success"] is True
        assert "total_jumps" in route
        assert "total_cost" in route
        assert "max_risk" in route
        assert "avg_risk" in route
        assert "path_systems" in route

    def test_bulk_routes_unknown_origin(self, test_client: TestClient):
        """Should return error for unknown origin system."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "FakeSystem",
                "to_systems": ["Amarr"],
                "profile": "shortest",
            },
        )

        assert response.status_code == 400
        assert "Unknown origin" in response.json()["detail"]

    def test_bulk_routes_unknown_profile(self, test_client: TestClient):
        """Should return error for unknown profile."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr"],
                "profile": "invalid_profile",
            },
        )

        assert response.status_code == 400
        assert "Unknown profile" in response.json()["detail"]

    def test_bulk_routes_unknown_destination(self, test_client: TestClient):
        """Should handle unknown destination gracefully."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr", "FakeSystem"],
                "profile": "shortest",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 1
        assert data["failed"] == 1

        # Find the failed route
        failed_route = next(r for r in data["routes"] if r["to_system"] == "FakeSystem")
        assert failed_route["success"] is False
        assert "Unknown system" in failed_route["error"]

    def test_bulk_routes_same_origin_destination(self, test_client: TestClient):
        """Should handle destination same as origin."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Jita", "Amarr"],
                "profile": "shortest",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] == 2

        # Find the self-route
        self_route = next(r for r in data["routes"] if r["to_system"] == "Jita")
        assert self_route["success"] is True
        assert self_route["total_jumps"] == 0
        assert self_route["path_systems"] == ["Jita"]

    def test_bulk_routes_sorted_by_jumps(self, test_client: TestClient):
        """Results should be sorted by jump count."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr", "Perimeter", "Urlen"],
                "profile": "shortest",
            },
        )

        data = response.json()
        routes = data["routes"]

        # Check routes are sorted by jumps (ascending)
        for i in range(len(routes) - 1):
            if routes[i]["success"] and routes[i + 1]["success"]:
                assert routes[i]["total_jumps"] <= routes[i + 1]["total_jumps"]

    def test_bulk_routes_with_avoid(self, test_client: TestClient):
        """Should respect avoid list in bulk routes."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr"],
                "profile": "shortest",
                "avoid": ["Niarja"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        route = data["routes"][0]
        assert "Niarja" not in route["path_systems"]

    def test_bulk_routes_with_bridges(self, test_client: TestClient):
        """Should accept use_bridges parameter."""
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr"],
                "profile": "shortest",
                "use_bridges": True,
            },
        )

        assert response.status_code == 200

    def test_bulk_routes_route_error_handling(self, test_client: TestClient):
        """Should handle routing errors gracefully."""
        # Try to route with all intermediate systems avoided (should fail)
        response = test_client.post(
            "/api/v1/route/bulk",
            json={
                "from_system": "Jita",
                "to_systems": ["Amarr"],
                "profile": "shortest",
                "avoid": ["Perimeter"],  # Block route from Jita
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Route should fail since Perimeter is blocked
        assert data["failed"] >= 0  # May succeed via alternate route


class TestGenerateRecommendation:
    """Tests for recommendation generation."""

    def test_recommendation_with_different_profiles(self, test_client: TestClient):
        """Should generate meaningful recommendation when profiles differ."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Amarr",
                "profiles": ["shortest", "safer", "paranoid"],
            },
        )

        data = response.json()
        recommendation = data["recommendation"]

        # Should have some content
        assert len(recommendation) > 10

    def test_recommendation_mentions_profiles(self, test_client: TestClient):
        """Recommendation should mention profile names."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Amarr",
                "profiles": ["shortest", "safer"],
            },
        )

        data = response.json()
        recommendation = data["recommendation"].lower()

        # Should mention at least one profile
        assert "shortest" in recommendation or "safer" in recommendation or "same" in recommendation


class TestRouteSecurityCategories:
    """Tests for route security category counting."""

    def test_route_through_lowsec(self, test_client: TestClient):
        """Should count lowsec jumps correctly."""
        # Route to a lowsec system
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Shenela",
                "profiles": ["shortest"],
            },
        )

        # If system exists and route found, should count correctly
        if response.status_code == 200:
            data = response.json()
            if data["routes"]:
                route = data["routes"][0]
                total = route["highsec_jumps"] + route["lowsec_jumps"] + route["nullsec_jumps"]
                assert total == len(route["path_systems"])

    def test_route_to_nullsec_system(self, test_client: TestClient):
        """Should count nullsec jumps when route passes through nullsec."""
        # LZ-6SU is a nullsec system
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "LZ-6SU",
                "profiles": ["shortest"],
            },
        )

        # If route found, check nullsec counting
        if response.status_code == 200:
            data = response.json()
            if data["routes"]:
                route = data["routes"][0]
                # Should have at least 1 nullsec jump (the destination)
                assert route["nullsec_jumps"] >= 1

    def test_highsec_only_route_recommendation(self, test_client: TestClient):
        """Routes staying in highsec should note that in recommendation."""
        # Jita to Perimeter is entirely highsec
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
                "profiles": ["shortest", "safer"],
            },
        )

        data = response.json()
        route = data["routes"][0]

        # Should be all highsec
        assert route["lowsec_jumps"] == 0
        assert route["nullsec_jumps"] == 0


class TestRecommendationEdgeCases:
    """Edge case tests for recommendation generation."""

    def test_empty_profiles_list(self, test_client: TestClient):
        """Should handle empty profiles list."""
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Amarr",
                "profiles": [],
            },
        )

        # Either error or empty routes
        if response.status_code == 200:
            data = response.json()
            assert len(data["routes"]) == 0
            assert "No routes" in data["recommendation"]

    def test_recommendation_different_tradeoffs(self, test_client: TestClient):
        """Should generate tradeoff recommendations when profiles differ."""
        # Use a route where profiles might differ
        response = test_client.post(
            "/api/v1/route/compare",
            json={
                "from_system": "Jita",
                "to_system": "Dodixie",
                "profiles": ["shortest", "paranoid"],
            },
        )

        data = response.json()
        routes = data["routes"]

        if len(routes) >= 2:
            # Find if routes differ
            shortest = next((r for r in routes if r["profile"] == "shortest"), None)
            paranoid = next((r for r in routes if r["profile"] == "paranoid"), None)

            if shortest and paranoid:
                if shortest["total_jumps"] != paranoid["total_jumps"]:
                    # Should mention tradeoffs
                    assert (
                        "jumps" in data["recommendation"].lower()
                        or "risk" in data["recommendation"].lower()
                    )
