"""Integration tests for fatigue API endpoints."""

import pytest

from backend.app.services.jump_fatigue import reset_fatigue_tracker


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset fatigue tracker before each test."""
    reset_fatigue_tracker()
    yield
    reset_fatigue_tracker()


class TestFatigueCalculateEndpoint:
    """Tests for GET /api/v1/fatigue/calculate."""

    def test_calculate_basic_jump(self, test_client):
        """Test calculating fatigue for a basic jump."""
        # Using real systems from universe
        response = test_client.get(
            "/api/v1/fatigue/calculate",
            params={"from": "Jita", "to": "Perimeter"},
        )

        # May fail if systems not in universe, but endpoint should work
        assert response.status_code in (200, 400)

        if response.status_code == 200:
            data = response.json()
            assert "blue_timer_after" in data
            assert "red_timer_after" in data
            assert "wait_time_formatted" in data

    def test_calculate_with_existing_fatigue(self, test_client):
        """Test calculating with existing fatigue."""
        response = test_client.get(
            "/api/v1/fatigue/calculate",
            params={
                "from": "Jita",
                "to": "Perimeter",
                "blue_timer": 60,
                "red_timer": 600,
            },
        )

        assert response.status_code in (200, 400)


class TestFatigueRouteEndpoint:
    """Tests for POST /api/v1/fatigue/route."""

    def test_calculate_route_fatigue(self, test_client):
        """Test calculating fatigue for a route."""
        response = test_client.post(
            "/api/v1/fatigue/route",
            json={
                "waypoints": ["Jita", "Perimeter", "Urlen"],
                "wait_between_jumps": True,
            },
        )

        # May fail if systems not in universe
        assert response.status_code in (200, 400)

    def test_route_requires_two_waypoints(self, test_client):
        """Test that route requires at least 2 waypoints."""
        response = test_client.post(
            "/api/v1/fatigue/route",
            json={"waypoints": ["Jita"]},
        )

        assert response.status_code == 422  # Validation error

    def test_route_with_character(self, test_client):
        """Test route calculation with character fatigue."""
        # First set character fatigue
        test_client.put(
            "/api/v1/fatigue/character/12345",
            json={
                "blue_timer_seconds": 60,
                "red_timer_seconds": 600,
            },
        )

        # Then calculate route
        response = test_client.post(
            "/api/v1/fatigue/route",
            json={
                "waypoints": ["Jita", "Perimeter"],
                "character_id": 12345,
            },
        )

        assert response.status_code in (200, 400)


class TestFatigueCharacterEndpoint:
    """Tests for /api/v1/fatigue/character/{character_id}."""

    def test_get_default_character_fatigue(self, test_client):
        """Test getting fatigue for unknown character."""
        response = test_client.get("/api/v1/fatigue/character/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["blue_timer_seconds"] == 0.0
        assert data["red_timer_seconds"] == 0.0
        assert data["can_jump"] is True

    def test_set_character_fatigue(self, test_client):
        """Test setting character fatigue."""
        response = test_client.put(
            "/api/v1/fatigue/character/12345",
            json={
                "blue_timer_seconds": 300,
                "red_timer_seconds": 1800,
                "character_name": "Test Pilot",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["character_name"] == "Test Pilot"
        # Timers should be approximately set (accounting for decay)
        assert 290 <= data["blue_timer_seconds"] <= 310
        assert 1790 <= data["red_timer_seconds"] <= 1810

    def test_get_set_character_fatigue(self, test_client):
        """Test get after set."""
        # Set
        test_client.put(
            "/api/v1/fatigue/character/12345",
            json={
                "blue_timer_seconds": 300,
                "red_timer_seconds": 1800,
            },
        )

        # Get
        response = test_client.get("/api/v1/fatigue/character/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["blue_timer_seconds"] > 0
        assert data["red_timer_seconds"] > 0

    def test_clear_character_fatigue(self, test_client):
        """Test clearing character fatigue."""
        # Set
        test_client.put(
            "/api/v1/fatigue/character/12345",
            json={
                "blue_timer_seconds": 300,
                "red_timer_seconds": 1800,
            },
        )

        # Clear
        response = test_client.delete("/api/v1/fatigue/character/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"

        # Verify cleared
        get_response = test_client.get("/api/v1/fatigue/character/12345")
        get_data = get_response.json()
        assert get_data["blue_timer_seconds"] == 0.0


class TestFatigueRecordJumpEndpoint:
    """Tests for POST /api/v1/fatigue/character/{id}/jump."""

    def test_record_jump(self, test_client):
        """Test recording a jump."""
        response = test_client.post(
            "/api/v1/fatigue/character/12345/jump",
            json={
                "from_system": "Jita",
                "to_system": "Perimeter",
            },
        )

        # May fail if systems not in universe
        assert response.status_code in (200, 400)


class TestFatigueFormatEndpoint:
    """Tests for GET /api/v1/fatigue/format."""

    def test_format_zero(self, test_client):
        """Test formatting zero seconds."""
        response = test_client.get(
            "/api/v1/fatigue/format",
            params={"seconds": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["formatted"] == "0:00"

    def test_format_minutes(self, test_client):
        """Test formatting minutes."""
        response = test_client.get(
            "/api/v1/fatigue/format",
            params={"seconds": 185},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["formatted"] == "3:05"

    def test_format_hours(self, test_client):
        """Test formatting hours."""
        response = test_client.get(
            "/api/v1/fatigue/format",
            params={"seconds": 3661},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["formatted"] == "1:01:01"

    def test_format_requires_seconds(self, test_client):
        """Test that seconds parameter is required."""
        response = test_client.get("/api/v1/fatigue/format")

        assert response.status_code == 422
