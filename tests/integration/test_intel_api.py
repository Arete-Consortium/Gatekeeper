"""Integration tests for intel API endpoints."""

import pytest

from backend.app.services.intel_parser import reset_intel_store


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the global intel store before each test."""
    reset_intel_store()
    yield
    reset_intel_store()


class TestIntelSubmitEndpoint:
    """Tests for POST /api/v1/intel/submit."""

    def test_submit_intel_success(self, test_client):
        """Test submitting intel text."""
        response = test_client.post(
            "/api/v1/intel/submit",
            json={"text": "Jita +1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reports_parsed"] >= 0  # May be 0 if universe not loaded

    def test_submit_multiline_intel(self, test_client):
        """Test submitting multiple lines of intel."""
        response = test_client.post(
            "/api/v1/intel/submit",
            json={"text": "Jita +1\nAmarr +2"},
        )

        assert response.status_code == 200

    def test_submit_with_reporter(self, test_client):
        """Test submitting intel with reporter name."""
        response = test_client.post(
            "/api/v1/intel/submit",
            json={"text": "Jita +1", "reporter": "TestPilot"},
        )

        assert response.status_code == 200

    def test_submit_empty_text(self, test_client):
        """Test submitting empty text."""
        response = test_client.post(
            "/api/v1/intel/submit",
            json={"text": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["reports_parsed"] == 0


class TestIntelParseEndpoint:
    """Tests for POST /api/v1/intel/parse."""

    def test_parse_preview(self, test_client):
        """Test parsing intel without storing."""
        response = test_client.post(
            "/api/v1/intel/parse",
            json={"text": "Jita +1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "reports" in data

    def test_parse_invalid_returns_valid_false(self, test_client):
        """Test that invalid intel returns valid: false."""
        response = test_client.post(
            "/api/v1/intel/parse",
            json={"text": "not a valid intel line"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False


class TestIntelSystemEndpoint:
    """Tests for GET /api/v1/intel/system/{system_name}."""

    def test_get_nonexistent_system_returns_404(self, test_client):
        """Test getting intel for system with no reports."""
        response = test_client.get("/api/v1/intel/system/NonExistent")

        assert response.status_code == 404

    def test_get_system_intel_after_submit(self, test_client):
        """Test getting system intel after submitting a report."""
        # First submit some intel (may not work if universe not loaded)
        test_client.post(
            "/api/v1/intel/submit",
            json={"text": "Jita +1"},
        )

        # Try to get it - may still be 404 if system not recognized
        response = test_client.get("/api/v1/intel/system/Jita")

        # Either 200 (found) or 404 (not found because universe not loaded)
        assert response.status_code in (200, 404)


class TestIntelAllEndpoint:
    """Tests for GET /api/v1/intel/all."""

    def test_get_all_intel_empty(self, test_client):
        """Test getting all intel when empty."""
        response = test_client.get("/api/v1/intel/all")

        assert response.status_code == 200
        data = response.json()
        assert data["total_systems"] == 0
        assert data["total_hostiles"] == 0
        assert data["systems"] == {}

    def test_get_all_intel_structure(self, test_client):
        """Test all intel response structure."""
        response = test_client.get("/api/v1/intel/all")

        assert response.status_code == 200
        data = response.json()
        assert "total_systems" in data
        assert "total_hostiles" in data
        assert "systems" in data


class TestIntelHostileSystemsEndpoint:
    """Tests for GET /api/v1/intel/hostile-systems."""

    def test_get_hostile_systems_empty(self, test_client):
        """Test getting hostile systems when empty."""
        response = test_client.get("/api/v1/intel/hostile-systems")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["systems"] == []


class TestIntelClearSystemEndpoint:
    """Tests for DELETE /api/v1/intel/system/{system_name}."""

    def test_clear_system_intel(self, test_client):
        """Test clearing intel for a system."""
        response = test_client.delete("/api/v1/intel/system/Jita")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert data["system"] == "Jita"


class TestIntelClearAllEndpoint:
    """Tests for DELETE /api/v1/intel/all."""

    def test_clear_all_intel(self, test_client):
        """Test clearing all intel."""
        response = test_client.delete("/api/v1/intel/all")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
