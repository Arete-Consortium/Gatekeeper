"""Integration tests for jump drive API endpoints."""

from fastapi.testclient import TestClient


class TestJumpRangeEndpoint:
    """Tests for GET /api/v1/jump/range."""

    def test_default_parameters(self, test_client: TestClient):
        """Should return jump range with default parameters."""
        response = test_client.get("/api/v1/jump/range")

        assert response.status_code == 200
        data = response.json()
        assert "ship_type" in data
        assert "base_range_ly" in data
        assert "max_range_ly" in data
        assert "jdc_level" in data
        assert "jfc_level" in data
        assert "fuel_per_ly" in data

    def test_jump_freighter_default(self, test_client: TestClient):
        """Default ship should be jump freighter."""
        response = test_client.get("/api/v1/jump/range")

        data = response.json()
        assert data["ship_type"] == "jump_freighter"

    def test_carrier_ship_type(self, test_client: TestClient):
        """Should accept carrier ship type."""
        response = test_client.get("/api/v1/jump/range?ship=carrier")

        assert response.status_code == 200
        data = response.json()
        assert data["ship_type"] == "carrier"

    def test_titan_ship_type(self, test_client: TestClient):
        """Should accept titan ship type."""
        response = test_client.get("/api/v1/jump/range?ship=titan")

        assert response.status_code == 200
        data = response.json()
        assert data["ship_type"] == "titan"

    def test_black_ops_ship_type(self, test_client: TestClient):
        """Should accept black ops ship type."""
        response = test_client.get("/api/v1/jump/range?ship=black_ops")

        assert response.status_code == 200
        data = response.json()
        assert data["ship_type"] == "black_ops"

    def test_jdc_level_affects_range(self, test_client: TestClient):
        """JDC level should affect max range."""
        response_0 = test_client.get("/api/v1/jump/range?jdc=0")
        response_5 = test_client.get("/api/v1/jump/range?jdc=5")

        data_0 = response_0.json()
        data_5 = response_5.json()

        assert data_5["max_range_ly"] > data_0["max_range_ly"]

    def test_jfc_level_affects_fuel(self, test_client: TestClient):
        """JFC level should affect fuel consumption."""
        response_0 = test_client.get("/api/v1/jump/range?jfc=0")
        response_5 = test_client.get("/api/v1/jump/range?jfc=5")

        data_0 = response_0.json()
        data_5 = response_5.json()

        assert data_5["fuel_per_ly"] < data_0["fuel_per_ly"]

    def test_invalid_jdc_level(self, test_client: TestClient):
        """Should reject invalid JDC level."""
        response = test_client.get("/api/v1/jump/range?jdc=6")
        assert response.status_code == 422

    def test_invalid_jfc_level(self, test_client: TestClient):
        """Should reject invalid JFC level."""
        response = test_client.get("/api/v1/jump/range?jfc=-1")
        assert response.status_code == 422

    def test_invalid_ship_type(self, test_client: TestClient):
        """Should reject invalid ship type."""
        response = test_client.get("/api/v1/jump/range?ship=invalid_ship")
        assert response.status_code == 422


class TestJumpDistanceEndpoint:
    """Tests for GET /api/v1/jump/distance."""

    def test_distance_between_systems(self, test_client: TestClient):
        """Should return distance between two systems."""
        response = test_client.get("/api/v1/jump/distance?from=Jita&to=Amarr")

        assert response.status_code == 200
        data = response.json()
        assert "from_system" in data
        assert "to_system" in data
        assert "distance_ly" in data
        assert data["from_system"] == "Jita"
        assert data["to_system"] == "Amarr"
        assert data["distance_ly"] > 0

    def test_same_system(self, test_client: TestClient):
        """Distance from system to itself should be 0."""
        response = test_client.get("/api/v1/jump/distance?from=Jita&to=Jita")

        assert response.status_code == 200
        data = response.json()
        assert data["distance_ly"] == 0

    def test_unknown_from_system(self, test_client: TestClient):
        """Should return error for unknown from system."""
        response = test_client.get("/api/v1/jump/distance?from=FakeSystem&to=Jita")

        assert response.status_code == 400
        assert "Unknown system" in response.json()["detail"]

    def test_unknown_to_system(self, test_client: TestClient):
        """Should return error for unknown to system."""
        response = test_client.get("/api/v1/jump/distance?from=Jita&to=FakeSystem")

        assert response.status_code == 400
        assert "Unknown system" in response.json()["detail"]

    def test_missing_from_parameter(self, test_client: TestClient):
        """Should require from parameter."""
        response = test_client.get("/api/v1/jump/distance?to=Amarr")
        assert response.status_code == 422

    def test_missing_to_parameter(self, test_client: TestClient):
        """Should require to parameter."""
        response = test_client.get("/api/v1/jump/distance?from=Jita")
        assert response.status_code == 422


class TestSystemsInRangeEndpoint:
    """Tests for GET /api/v1/jump/systems-in-range."""

    def test_systems_in_range(self, test_client: TestClient):
        """Should return systems within jump range."""
        response = test_client.get("/api/v1/jump/systems-in-range?origin=Jita")

        assert response.status_code == 200
        data = response.json()
        assert "origin" in data
        assert "max_range_ly" in data
        assert "count" in data
        assert "systems" in data

    def test_origin_in_response(self, test_client: TestClient):
        """Origin system should be in response."""
        response = test_client.get("/api/v1/jump/systems-in-range?origin=Jita")

        data = response.json()
        assert data["origin"] == "Jita"

    def test_systems_have_required_fields(self, test_client: TestClient):
        """Each system should have required fields."""
        response = test_client.get("/api/v1/jump/systems-in-range?origin=Jita&limit=5")

        data = response.json()
        if data["count"] > 0:
            system = data["systems"][0]
            assert "name" in system
            assert "system_id" in system
            assert "distance_ly" in system
            assert "security" in system
            assert "category" in system
            assert "fuel_required" in system

    def test_respects_limit(self, test_client: TestClient):
        """Should respect limit parameter."""
        response = test_client.get("/api/v1/jump/systems-in-range?origin=Jita&limit=3")

        data = response.json()
        assert len(data["systems"]) <= 3

    def test_security_filter_lowsec(self, test_client: TestClient):
        """Should filter by lowsec security."""
        response = test_client.get("/api/v1/jump/systems-in-range?origin=Jita&security=lowsec")

        assert response.status_code == 200
        data = response.json()
        for system in data["systems"]:
            assert system["category"] == "lowsec"

    def test_security_filter_nullsec(self, test_client: TestClient):
        """Should filter by nullsec security."""
        response = test_client.get("/api/v1/jump/systems-in-range?origin=Jita&security=nullsec")

        assert response.status_code == 200
        data = response.json()
        for system in data["systems"]:
            assert system["category"] == "nullsec"

    def test_unknown_origin_system(self, test_client: TestClient):
        """Should return error for unknown origin."""
        response = test_client.get("/api/v1/jump/systems-in-range?origin=FakeSystem")

        assert response.status_code == 400

    def test_different_ship_types_different_ranges(self, test_client: TestClient):
        """Different ship types should have different max ranges."""
        response_jf = test_client.get(
            "/api/v1/jump/systems-in-range?origin=Jita&ship=jump_freighter"
        )
        response_blops = test_client.get("/api/v1/jump/systems-in-range?origin=Jita&ship=black_ops")

        data_jf = response_jf.json()
        data_blops = response_blops.json()

        # JF has longer range than blops
        assert data_jf["max_range_ly"] > data_blops["max_range_ly"]


class TestJumpRouteEndpoint:
    """Tests for GET /api/v1/jump/route."""

    def test_route_between_systems(self, test_client: TestClient):
        """Should return jump route between systems."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr")

        assert response.status_code == 200
        data = response.json()
        assert "from_system" in data
        assert "to_system" in data
        assert "ship_type" in data
        assert "total_jumps" in data
        assert "total_distance_ly" in data
        assert "total_fuel" in data
        assert "legs" in data

    def test_route_has_legs(self, test_client: TestClient):
        """Route should have at least one leg."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr")

        data = response.json()
        assert len(data["legs"]) >= 1

    def test_leg_structure(self, test_client: TestClient):
        """Each leg should have required fields."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr")

        data = response.json()
        if len(data["legs"]) > 0:
            leg = data["legs"][0]
            assert "from_system" in leg
            assert "to_system" in leg
            assert "distance_ly" in leg
            assert "fuel_required" in leg
            assert "fatigue_added_minutes" in leg
            assert "total_fatigue_minutes" in leg
            assert "wait_time_minutes" in leg

    def test_route_starts_at_origin(self, test_client: TestClient):
        """First leg should start at origin."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr")

        data = response.json()
        assert data["from_system"] == "Jita"
        assert data["legs"][0]["from_system"] == "Jita"

    def test_route_ends_at_destination(self, test_client: TestClient):
        """Last leg should end at destination."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr")

        data = response.json()
        assert data["to_system"] == "Amarr"
        assert data["legs"][-1]["to_system"] == "Amarr"

    def test_unknown_from_system(self, test_client: TestClient):
        """Should return error for unknown from system."""
        response = test_client.get("/api/v1/jump/route?from=FakeSystem&to=Amarr")

        assert response.status_code == 400

    def test_unknown_to_system(self, test_client: TestClient):
        """Should return error for unknown to system."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=FakeSystem")

        assert response.status_code == 400

    def test_different_ship_types(self, test_client: TestClient):
        """Should accept different ship types."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr&ship=titan")

        assert response.status_code == 200
        data = response.json()
        assert data["ship_type"] == "titan"

    def test_total_fuel_matches_legs(self, test_client: TestClient):
        """Total fuel should match sum of leg fuel."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr")

        data = response.json()
        leg_fuel_sum = sum(leg["fuel_required"] for leg in data["legs"])
        assert data["total_fuel"] == leg_fuel_sum

    def test_total_distance_matches_legs(self, test_client: TestClient):
        """Total distance should match sum of leg distances."""
        response = test_client.get("/api/v1/jump/route?from=Jita&to=Amarr")

        data = response.json()
        leg_distance_sum = sum(leg["distance_ly"] for leg in data["legs"])
        assert abs(data["total_distance_ly"] - leg_distance_sum) < 0.01
