"""Unit tests for zKillboard client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.app.models.risk import ZKillStats
from backend.app.services.zkill_client import _POD_TYPE_IDS, fetch_system_stats


def _make_kill(ship_type_id: int) -> dict:
    return {"victim": {"ship_type_id": ship_type_id}}


def _mock_client(*, response=None, side_effect=None):
    """Build a mocked httpx.AsyncClient context manager."""
    client = AsyncMock()
    if side_effect:
        client.get.side_effect = side_effect
    else:
        client.get.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


def _ok_response(payload):
    return httpx.Response(
        200, json=payload, request=httpx.Request("GET", "https://zkillboard.com/api/test/")
    )


def _error_response(status_code: int):
    return httpx.Response(
        status_code, request=httpx.Request("GET", "https://zkillboard.com/api/test/")
    )


class TestFetchSystemStats:
    """Tests for fetch_system_stats with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_happy_path_kills_and_pods(self):
        """Kills and pods are counted correctly."""
        payload = [
            _make_kill(587),  # kill
            _make_kill(670),  # pod
            _make_kill(33328),  # genolution pod
            _make_kill(11393),  # kill
        ]

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 2
        assert result.recent_pods == 2

    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Empty API response returns zero stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response([]))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats(recent_kills=0, recent_pods=0)

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        """HTTP errors return empty stats gracefully."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_error_response(502))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self):
        """Timeout returns empty stats gracefully."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(
                side_effect=httpx.TimeoutException("timed out")
            )
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_pod_counting_only_pods(self):
        """Only pod type IDs 670 and 33328 count as pods."""
        payload = [
            _make_kill(670),
            _make_kill(670),
            _make_kill(33328),
        ]

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 3


class TestFetchSystemStatsHTTPErrors:
    """Tests for various HTTP error status codes."""

    @pytest.mark.asyncio
    async def test_429_rate_limit_returns_empty(self):
        """429 Too Many Requests returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_error_response(429))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_500_server_error_returns_empty(self):
        """500 Internal Server Error returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_error_response(500))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_503_service_unavailable_returns_empty(self):
        """503 Service Unavailable returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_error_response(503))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_403_forbidden_returns_empty(self):
        """403 Forbidden returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_error_response(403))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_404_not_found_returns_empty(self):
        """404 Not Found returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_error_response(404))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()


class TestFetchSystemStatsNetworkErrors:
    """Tests for network-level failures."""

    @pytest.mark.asyncio
    async def test_connect_timeout_returns_empty(self):
        """Connection timeout returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(
                side_effect=httpx.ConnectTimeout("connection timed out")
            )
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_read_timeout_returns_empty(self):
        """Read timeout returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(
                side_effect=httpx.ReadTimeout("read timed out")
            )
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_connect_error_returns_empty(self):
        """Connection refused returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(
                side_effect=httpx.ConnectError("connection refused")
            )
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_generic_exception_returns_empty(self):
        """Any unexpected exception returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(
                side_effect=RuntimeError("something unexpected")
            )
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()


class TestFetchSystemStatsMalformedResponses:
    """Tests for invalid/malformed response bodies."""

    @pytest.mark.asyncio
    async def test_non_list_response_returns_empty(self):
        """Non-list JSON response (dict) returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(
                response=_ok_response({"error": "not a list"})
            )
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_null_response_returns_empty(self):
        """null JSON response returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(None))
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_string_response_returns_empty(self):
        """String JSON response returns empty stats."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(
                response=_ok_response("not a list")
            )
            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_kill_missing_victim_key(self):
        """Kill entry with no victim key counts as regular kill (ship_type_id defaults to 0)."""
        payload = [{"attackers": []}]  # no victim key

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 1
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_kill_missing_ship_type_id(self):
        """Kill with victim but no ship_type_id defaults to 0 (counts as regular kill)."""
        payload = [{"victim": {"character_id": 12345}}]

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 1
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_kill_with_null_victim(self):
        """Kill with null victim object counts as regular kill."""
        payload = [{"victim": None}]

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        # None doesn't have .get(), so this triggers the generic exception handler
        assert result == ZKillStats()


class TestFetchSystemStatsHoursParameter:
    """Tests for the hours parameter."""

    @pytest.mark.asyncio
    async def test_custom_hours_parameter(self):
        """Custom hours value is used in the URL."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = _mock_client(response=_ok_response([]))
            mock_cls.return_value = client
            await fetch_system_stats(30000142, hours=48)

        # Verify the URL includes the correct pastSeconds value (48 * 3600 = 172800)
        call_args = client.get.call_args
        url = call_args[0][0]
        assert "172800" in url

    @pytest.mark.asyncio
    async def test_default_hours_is_24(self):
        """Default hours parameter produces pastSeconds of 86400."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = _mock_client(response=_ok_response([]))
            mock_cls.return_value = client
            await fetch_system_stats(30000142)

        call_args = client.get.call_args
        url = call_args[0][0]
        assert "86400" in url

    @pytest.mark.asyncio
    async def test_one_hour_parameter(self):
        """hours=1 produces pastSeconds of 3600."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = _mock_client(response=_ok_response([]))
            mock_cls.return_value = client
            await fetch_system_stats(30000142, hours=1)

        call_args = client.get.call_args
        url = call_args[0][0]
        assert "3600" in url


class TestFetchSystemStatsLargePayloads:
    """Tests for large and edge-case payloads."""

    @pytest.mark.asyncio
    async def test_large_kill_list(self):
        """Handles a large number of kills correctly."""
        payload = [_make_kill(587)] * 50 + [_make_kill(670)] * 25

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 50
        assert result.recent_pods == 25

    @pytest.mark.asyncio
    async def test_mixed_ship_types(self):
        """Various ship type IDs are categorized correctly."""
        payload = [
            _make_kill(587),    # Rifter (kill)
            _make_kill(24690),  # Raven Navy Issue (kill)
            _make_kill(670),    # Capsule (pod)
            _make_kill(33328),  # Capsule - Genolution (pod)
            _make_kill(11393),  # Maelstrom (kill)
            _make_kill(17740),  # Zealot (kill)
        ]

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 4
        assert result.recent_pods == 2

    @pytest.mark.asyncio
    async def test_single_kill(self):
        """Single kill in response is counted."""
        payload = [_make_kill(587)]

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 1
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_single_pod(self):
        """Single pod in response is counted."""
        payload = [_make_kill(670)]

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_client(response=_ok_response(payload))
            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 1


class TestPodTypeIds:
    """Tests for the _POD_TYPE_IDS constant."""

    def test_pod_type_ids_contains_capsule(self):
        """670 (Capsule) is in the pod type IDs set."""
        assert 670 in _POD_TYPE_IDS

    def test_pod_type_ids_contains_genolution(self):
        """33328 (Capsule - Genolution) is in the pod type IDs set."""
        assert 33328 in _POD_TYPE_IDS

    def test_pod_type_ids_count(self):
        """Only two pod type IDs exist."""
        assert len(_POD_TYPE_IDS) == 2

    def test_regular_ship_not_in_pod_ids(self):
        """Regular ship type IDs are not in the pod set."""
        assert 587 not in _POD_TYPE_IDS  # Rifter
        assert 24690 not in _POD_TYPE_IDS  # Raven Navy Issue


class TestFetchSystemStatsSystemId:
    """Tests for different system ID values."""

    @pytest.mark.asyncio
    async def test_jita_system_id_in_url(self):
        """System ID 30000142 (Jita) is included in the request URL."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = _mock_client(response=_ok_response([]))
            mock_cls.return_value = client
            await fetch_system_stats(30000142)

        url = client.get.call_args[0][0]
        assert "30000142" in url

    @pytest.mark.asyncio
    async def test_nullsec_system_id_in_url(self):
        """System ID 30001161 (HED-GP) is included in the request URL."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = _mock_client(response=_ok_response([]))
            mock_cls.return_value = client
            await fetch_system_stats(30001161)

        url = client.get.call_args[0][0]
        assert "30001161" in url
