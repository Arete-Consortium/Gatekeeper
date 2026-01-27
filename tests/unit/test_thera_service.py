"""Unit tests for Thera wormhole connection service."""

import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.app.models.thera import TheraConnection
from backend.app.services.thera import (
    CACHE_TTL_SECONDS,
    EVE_SCOUT_URL,
    clear_thera_cache,
    fetch_thera_connections,
    get_active_thera,
    get_thera_cache_age,
    get_thera_last_error,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear Thera cache before and after each test."""
    clear_thera_cache()
    yield
    clear_thera_cache()


def _make_connection(**overrides) -> dict:
    """Build a raw EVE-Scout connection dict."""
    base = {
        "id": 1,
        "in_system_id": 30000142,
        "in_system_name": "Jita",
        "out_system_id": 30002187,
        "out_system_name": "Amarr",
        "wh_type": "Q003",
        "max_ship_size": "battleship",
        "remaining_hours": 10.0,
        "expires_at": "2026-01-28T00:00:00",
        "completed": False,
    }
    base.update(overrides)
    return base


class TestFetchTheraConnections:
    """Tests for fetch_thera_connections()."""

    @patch("backend.app.services.thera.httpx.get")
    def test_fetches_from_api(self, mock_get):
        """Should call EVE-Scout API and return parsed connections."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [_make_connection()]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_thera_connections()

        mock_get.assert_called_once_with(EVE_SCOUT_URL, timeout=10.0)
        assert len(result) == 1
        assert isinstance(result[0], TheraConnection)
        assert result[0].in_system_name == "Jita"

    @patch("backend.app.services.thera.httpx.get")
    def test_returns_multiple_connections(self, mock_get):
        """Should parse all connections from response."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            _make_connection(id=1, in_system_name="Jita"),
            _make_connection(id=2, in_system_name="Amarr"),
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_thera_connections()
        assert len(result) == 2

    @patch("backend.app.services.thera.httpx.get")
    def test_caches_results(self, mock_get):
        """Should return cached results within TTL."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [_make_connection()]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        fetch_thera_connections()
        fetch_thera_connections()

        assert mock_get.call_count == 1

    @patch("backend.app.services.thera.httpx.get")
    def test_cache_expires(self, mock_get):
        """Should refetch after TTL expires."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [_make_connection()]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        fetch_thera_connections()

        # Simulate cache expiry
        from backend.app.services.thera import _cache
        _cache["timestamp"] = time.time() - CACHE_TTL_SECONDS - 1

        fetch_thera_connections()
        assert mock_get.call_count == 2

    @patch("backend.app.services.thera.httpx.get")
    def test_handles_timeout(self, mock_get):
        """Should return empty list on timeout with no cache."""
        mock_get.side_effect = httpx.TimeoutException("timeout")

        result = fetch_thera_connections()
        assert result == []

    @patch("backend.app.services.thera.httpx.get")
    def test_handles_http_error(self, mock_get):
        """Should return empty list on HTTP error with no cache."""
        mock_get.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )

        result = fetch_thera_connections()
        assert result == []

    @patch("backend.app.services.thera.httpx.get")
    def test_returns_stale_cache_on_error(self, mock_get):
        """Should return stale cache when API fails."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [_make_connection()]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        # Populate cache
        fetch_thera_connections()

        # Expire cache
        from backend.app.services.thera import _cache
        _cache["timestamp"] = time.time() - CACHE_TTL_SECONDS - 1

        # API fails
        mock_get.side_effect = httpx.TimeoutException("timeout")
        result = fetch_thera_connections()

        assert len(result) == 1
        assert result[0].in_system_name == "Jita"

    @patch("backend.app.services.thera.httpx.get")
    def test_stores_last_error(self, mock_get):
        """Should store error message on failure."""
        mock_get.side_effect = httpx.TimeoutException("connection timed out")

        fetch_thera_connections()
        assert get_thera_last_error() is not None
        assert "timed out" in get_thera_last_error()

    @patch("backend.app.services.thera.httpx.get")
    def test_clears_error_on_success(self, mock_get):
        """Should clear last error on successful fetch."""
        # First call fails
        mock_get.side_effect = httpx.TimeoutException("timeout")
        fetch_thera_connections()
        assert get_thera_last_error() is not None

        clear_thera_cache()

        # Second call succeeds
        mock_resp = MagicMock()
        mock_resp.json.return_value = [_make_connection()]
        mock_resp.raise_for_status = MagicMock()
        mock_get.side_effect = None
        mock_get.return_value = mock_resp

        fetch_thera_connections()
        assert get_thera_last_error() is None

    @patch("backend.app.services.thera.httpx.get")
    def test_handles_malformed_json(self, mock_get):
        """Should handle invalid JSON gracefully."""
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("bad json")
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_thera_connections()
        assert result == []


class TestGetActiveThera:
    """Tests for get_active_thera()."""

    @patch("backend.app.services.thera.fetch_thera_connections")
    def test_filters_completed(self, mock_fetch):
        """Should exclude completed connections."""
        mock_fetch.return_value = [
            TheraConnection(**_make_connection(completed=True)),
            TheraConnection(**_make_connection(id=2, completed=False)),
        ]

        result = get_active_thera()
        assert len(result) == 1
        assert result[0].id == 2

    @patch("backend.app.services.thera.fetch_thera_connections")
    def test_filters_expired(self, mock_fetch):
        """Should exclude connections with remaining_hours <= 0."""
        mock_fetch.return_value = [
            TheraConnection(**_make_connection(remaining_hours=0.0)),
            TheraConnection(**_make_connection(id=2, remaining_hours=5.0)),
        ]

        result = get_active_thera()
        assert len(result) == 1
        assert result[0].id == 2

    @patch("backend.app.services.thera.fetch_thera_connections")
    def test_filters_unknown_in_system(self, mock_fetch):
        """Should exclude connections where in_system is not in universe."""
        mock_fetch.return_value = [
            TheraConnection(**_make_connection(in_system_name="FakeSystem999")),
        ]

        result = get_active_thera()
        assert len(result) == 0

    @patch("backend.app.services.thera.fetch_thera_connections")
    def test_filters_unknown_out_system(self, mock_fetch):
        """Should exclude connections where out_system is not in universe."""
        mock_fetch.return_value = [
            TheraConnection(**_make_connection(out_system_name="FakeSystem999")),
        ]

        result = get_active_thera()
        assert len(result) == 0

    @patch("backend.app.services.thera.fetch_thera_connections")
    def test_returns_valid_connections(self, mock_fetch):
        """Should return connections where both systems exist."""
        mock_fetch.return_value = [
            TheraConnection(**_make_connection()),
        ]

        result = get_active_thera()
        assert len(result) == 1

    @patch("backend.app.services.thera.fetch_thera_connections")
    def test_empty_input(self, mock_fetch):
        """Should handle empty connection list."""
        mock_fetch.return_value = []

        result = get_active_thera()
        assert result == []

    @patch("backend.app.services.thera.fetch_thera_connections")
    def test_filters_negative_remaining_hours(self, mock_fetch):
        """Should exclude connections with negative remaining hours."""
        mock_fetch.return_value = [
            TheraConnection(**_make_connection(remaining_hours=-1.0)),
        ]

        result = get_active_thera()
        assert len(result) == 0


class TestCacheHelpers:
    """Tests for cache inspection functions."""

    def test_cache_age_none_before_fetch(self):
        """Should return None if never fetched."""
        assert get_thera_cache_age() is None

    @patch("backend.app.services.thera.httpx.get")
    def test_cache_age_after_fetch(self, mock_get):
        """Should return age in seconds after fetch."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [_make_connection()]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        fetch_thera_connections()
        age = get_thera_cache_age()
        assert age is not None
        assert age < 2.0  # Should be nearly instant

    def test_last_error_none_initially(self):
        """Should return None if no errors occurred."""
        assert get_thera_last_error() is None

    def test_clear_cache_resets_all(self):
        """Should reset all cache state."""
        from backend.app.services.thera import _cache
        _cache["timestamp"] = 999.0
        _cache["last_error"] = "some error"

        clear_thera_cache()

        assert get_thera_cache_age() is None
        assert get_thera_last_error() is None


class TestTheraConnectionModel:
    """Tests for TheraConnection Pydantic model."""

    def test_parses_valid_data(self):
        """Should parse a valid connection dict."""
        conn = TheraConnection(**_make_connection())
        assert conn.id == 1
        assert conn.in_system_name == "Jita"
        assert conn.out_system_name == "Amarr"
        assert conn.completed is False

    def test_defaults(self):
        """Should use defaults for optional fields."""
        conn = TheraConnection(
            id=1,
            in_system_id=100,
            in_system_name="Jita",
            out_system_id=200,
            out_system_name="Amarr",
        )
        assert conn.wh_type == ""
        assert conn.max_ship_size == ""
        assert conn.remaining_hours == 0.0
        assert conn.completed is False
        assert conn.expires_at is None
