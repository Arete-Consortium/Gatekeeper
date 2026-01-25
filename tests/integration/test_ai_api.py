"""Integration tests for AI API endpoints."""


class TestAnalyzeRouteEndpoint:
    """Tests for POST /api/v1/ai/analyze-route endpoint."""

    def test_analyze_route_basic(self, test_client):
        """Test basic route analysis."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["from_system"] == "Jita"
        assert data["to_system"] == "Perimeter"
        assert data["profile"] == "shortest"  # Default
        assert data["total_jumps"] == 1
        assert data["overall_danger"] in ["low", "medium", "high", "extreme"]
        assert "assessment" in data
        assert "path_danger" in data

    def test_analyze_route_with_profile(self, test_client):
        """Test route analysis with specific profile."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Urlen",
                "profile": "safer",
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["profile"] == "safer"

    def test_analyze_route_response_structure(self, test_client):
        """Test that response has all expected fields."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Urlen",
            },
        )
        data = response.json()

        # Required fields
        assert "from_system" in data
        assert "to_system" in data
        assert "profile" in data
        assert "total_jumps" in data
        assert "overall_danger" in data
        assert "assessment" in data
        assert "warnings" in data
        assert "alternatives" in data
        assert "path_danger" in data

    def test_analyze_route_path_danger_structure(self, test_client):
        """Test path_danger has correct structure."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
            },
        )
        data = response.json()

        assert len(data["path_danger"]) >= 2
        for pd in data["path_danger"]:
            assert "system_name" in pd
            assert "danger_level" in pd
            assert "recent_kills" in pd
            assert pd["danger_level"] in ["low", "medium", "high", "extreme"]

    def test_analyze_route_unknown_from_system(self, test_client):
        """Test route analysis with unknown origin returns 400."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "NonExistent",
                "to_system": "Jita",
            },
        )
        assert response.status_code == 400
        assert "Unknown system" in response.json()["detail"]

    def test_analyze_route_unknown_to_system(self, test_client):
        """Test route analysis with unknown destination returns 400."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "NonExistent",
            },
        )
        assert response.status_code == 400
        assert "Unknown system" in response.json()["detail"]

    def test_analyze_route_unknown_profile(self, test_client):
        """Test route analysis with unknown profile returns 400."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
                "profile": "invalid_profile",
            },
        )
        assert response.status_code == 400
        assert "Unknown profile" in response.json()["detail"]

    def test_analyze_route_with_avoid(self, test_client):
        """Test route analysis with systems to avoid."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Urlen",
                "avoid": ["Perimeter"],
            },
        )
        # May fail if no alternate route exists, or succeed with different path
        # Just ensure it doesn't crash
        assert response.status_code in [200, 400]

    def test_analyze_route_include_alternatives_false(self, test_client):
        """Test route analysis without alternatives."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
                "include_alternatives": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["alternatives"] == []

    def test_analyze_route_missing_required_fields(self, test_client):
        """Test route analysis with missing required fields returns 422."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                # Missing to_system
            },
        )
        assert response.status_code == 422

    def test_analyze_route_same_origin_destination(self, test_client):
        """Test route analysis when origin equals destination."""
        response = test_client.post(
            "/api/v1/ai/analyze-route",
            json={
                "from_system": "Jita",
                "to_system": "Jita",
            },
        )
        # Should either succeed with 0 jumps or fail gracefully
        assert response.status_code in [200, 400]


class TestThresholdsEndpoint:
    """Tests for GET /api/v1/ai/thresholds endpoint."""

    def test_get_thresholds(self, test_client):
        """Test getting danger thresholds."""
        response = test_client.get("/api/v1/ai/thresholds")
        assert response.status_code == 200

        data = response.json()
        assert "medium" in data
        assert "high" in data
        assert "extreme" in data
        assert "description" in data

    def test_thresholds_are_integers(self, test_client):
        """Test that threshold values are integers."""
        response = test_client.get("/api/v1/ai/thresholds")
        data = response.json()

        assert isinstance(data["medium"], int)
        assert isinstance(data["high"], int)
        assert isinstance(data["extreme"], int)

    def test_thresholds_are_ordered(self, test_client):
        """Test that thresholds are properly ordered."""
        response = test_client.get("/api/v1/ai/thresholds")
        data = response.json()

        assert data["medium"] < data["high"]
        assert data["high"] < data["extreme"]

    def test_thresholds_default_values(self, test_client):
        """Test default threshold values match config."""
        response = test_client.get("/api/v1/ai/thresholds")
        data = response.json()

        assert data["medium"] == 5
        assert data["high"] == 10
        assert data["extreme"] == 20

    def test_thresholds_has_description(self, test_client):
        """Test that thresholds include description."""
        response = test_client.get("/api/v1/ai/thresholds")
        data = response.json()

        assert len(data["description"]) > 0
        assert "kills" in data["description"].lower() or "24h" in data["description"]
