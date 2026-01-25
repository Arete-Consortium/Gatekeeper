"""Integration tests for ship profiles API endpoints."""


class TestShipProfilesEndpoint:
    """Tests for /api/v1/systems/profiles/ships endpoint."""

    def test_list_ship_profiles(self, test_client):
        """Test listing all ship profiles."""
        response = test_client.get("/api/v1/systems/profiles/ships")
        assert response.status_code == 200

        data = response.json()
        assert "profiles" in data
        assert isinstance(data["profiles"], list)
        assert len(data["profiles"]) >= 8

    def test_ship_profiles_have_required_fields(self, test_client):
        """Test that ship profiles have all required fields."""
        response = test_client.get("/api/v1/systems/profiles/ships")
        data = response.json()

        for profile in data["profiles"]:
            assert "name" in profile
            assert "description" in profile
            assert "highsec_multiplier" in profile
            assert "lowsec_multiplier" in profile
            assert "nullsec_multiplier" in profile
            assert "kills_multiplier" in profile
            assert "pods_multiplier" in profile

    def test_ship_profiles_contains_expected_profiles(self, test_client):
        """Test that expected ship profiles exist."""
        response = test_client.get("/api/v1/systems/profiles/ships")
        data = response.json()

        profile_names = [p["name"] for p in data["profiles"]]
        expected = ["default", "hauler", "frigate", "cruiser", "battleship", "mining", "capital", "cloaky"]

        for name in expected:
            assert name in profile_names, f"Profile {name} not found"

    def test_hauler_profile_has_high_highsec_multiplier(self, test_client):
        """Test that hauler profile has increased highsec risk."""
        response = test_client.get("/api/v1/systems/profiles/ships")
        data = response.json()

        hauler = next(p for p in data["profiles"] if p["name"] == "hauler")
        assert hauler["highsec_multiplier"] > 1.0

    def test_cloaky_profile_has_low_multipliers(self, test_client):
        """Test that cloaky profile has reduced risk multipliers."""
        response = test_client.get("/api/v1/systems/profiles/ships")
        data = response.json()

        cloaky = next(p for p in data["profiles"] if p["name"] == "cloaky")
        assert cloaky["highsec_multiplier"] < 1.0
        assert cloaky["lowsec_multiplier"] < 1.0
        assert cloaky["nullsec_multiplier"] < 1.0


class TestSystemRiskWithShipProfile:
    """Tests for /api/v1/systems/{name}/risk with ship_profile parameter."""

    def test_get_risk_with_default_profile(self, test_client):
        """Test getting risk with default profile."""
        response = test_client.get("/api/v1/systems/Jita/risk?ship_profile=default")
        assert response.status_code == 200

        data = response.json()
        assert data["ship_profile"] == "default"

    def test_get_risk_with_hauler_profile(self, test_client):
        """Test getting risk with hauler profile."""
        response = test_client.get("/api/v1/systems/Jita/risk?ship_profile=hauler")
        assert response.status_code == 200

        data = response.json()
        assert data["ship_profile"] == "hauler"

    def test_get_risk_with_cloaky_profile(self, test_client):
        """Test getting risk with cloaky profile."""
        response = test_client.get("/api/v1/systems/Jita/risk?ship_profile=cloaky")
        assert response.status_code == 200

        data = response.json()
        assert data["ship_profile"] == "cloaky"

    def test_get_risk_with_invalid_profile(self, test_client):
        """Test getting risk with invalid profile returns 400."""
        response = test_client.get("/api/v1/systems/Jita/risk?ship_profile=invalid_profile")
        assert response.status_code == 400
        assert "Unknown ship profile" in response.json()["detail"]

    def test_hauler_has_higher_risk_than_default(self, test_client):
        """Test that hauler profile results in higher risk than default."""
        default_response = test_client.get("/api/v1/systems/Jita/risk?live=false")
        hauler_response = test_client.get("/api/v1/systems/Jita/risk?ship_profile=hauler&live=false")

        default_data = default_response.json()
        hauler_data = hauler_response.json()

        # Hauler should have higher or equal risk in highsec
        assert hauler_data["score"] >= default_data["score"]

    def test_cloaky_has_lower_risk_than_default(self, test_client):
        """Test that cloaky profile results in lower risk than default."""
        default_response = test_client.get("/api/v1/systems/Jita/risk?live=false")
        cloaky_response = test_client.get("/api/v1/systems/Jita/risk?ship_profile=cloaky&live=false")

        default_data = default_response.json()
        cloaky_data = cloaky_response.json()

        # Cloaky should have lower or equal risk
        assert cloaky_data["score"] <= default_data["score"]
