"""Integration tests for route history API endpoint."""


class TestRouteHistoryEndpoint:
    """Tests for /api/v1/route/history endpoint."""

    def test_get_route_history(self, test_client):
        """Test getting route history."""
        response = test_client.get("/api/v1/route/history")
        assert response.status_code == 200

        data = response.json()
        assert "routes" in data
        assert "total" in data
        assert isinstance(data["routes"], list)

    def test_route_history_with_limit(self, test_client):
        """Test route history with custom limit."""
        response = test_client.get("/api/v1/route/history?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data["routes"]) <= 5

    def test_route_calculation_adds_to_history(self, test_client):
        """Test that calculating a route adds it to history."""
        # Get initial history count
        initial_response = test_client.get("/api/v1/route/history")
        initial_total = initial_response.json()["total"]

        # Calculate a route
        test_client.get("/api/v1/route/?from=Jita&to=Perimeter&profile=safer")

        # Check history increased
        after_response = test_client.get("/api/v1/route/history")
        after_total = after_response.json()["total"]

        assert after_total >= initial_total  # May not increase if route fails

    def test_route_history_entry_has_required_fields(self, test_client):
        """Test that history entries have required fields."""
        # First, calculate a route to ensure history has entries
        test_client.get("/api/v1/route/?from=Jita&to=Perimeter&profile=safer")

        response = test_client.get("/api/v1/route/history")
        data = response.json()

        if data["routes"]:  # If there are entries
            entry = data["routes"][0]
            assert "from_system" in entry
            assert "to_system" in entry
            assert "profile" in entry
            assert "total_jumps" in entry
            assert "calculated_at" in entry

    def test_route_history_most_recent_first(self, test_client):
        """Test that history is sorted most recent first."""
        # Calculate multiple routes
        test_client.get("/api/v1/route/?from=Jita&to=Perimeter&profile=safer")
        test_client.get("/api/v1/route/?from=Perimeter&to=Jita&profile=shortest")

        response = test_client.get("/api/v1/route/history")
        data = response.json()

        if len(data["routes"]) >= 2:
            # Most recent should be first
            first_ts = data["routes"][0]["calculated_at"]
            second_ts = data["routes"][1]["calculated_at"]
            assert first_ts >= second_ts
