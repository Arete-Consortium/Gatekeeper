"""Unit tests for zKillboard client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.app.models.risk import ZKillStats
from backend.app.services.zkill_client import fetch_system_stats


def _make_kill(ship_type_id: int) -> dict:
    return {"victim": {"ship_type_id": ship_type_id}}


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
        response = httpx.Response(
            200, json=payload, request=httpx.Request("GET", "https://zkillboard.com/api/test/")
        )

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = response
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 2
        assert result.recent_pods == 2

    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Empty API response returns zero stats."""
        response = httpx.Response(
            200, json=[], request=httpx.Request("GET", "https://zkillboard.com/api/test/")
        )

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = response
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await fetch_system_stats(30000142)

        assert result == ZKillStats(recent_kills=0, recent_pods=0)

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        """HTTP errors return empty stats gracefully."""
        response = httpx.Response(502)

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = response
            # raise_for_status will raise
            response.request = httpx.Request("GET", "https://zkillboard.com/api/test/")
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await fetch_system_stats(30000142)

        assert result == ZKillStats()

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self):
        """Timeout returns empty stats gracefully."""
        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.side_effect = httpx.TimeoutException("timed out")
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

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
        response = httpx.Response(
            200, json=payload, request=httpx.Request("GET", "https://zkillboard.com/api/test/")
        )

        with patch("backend.app.services.zkill_client.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = response
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await fetch_system_stats(30000142)

        assert result.recent_kills == 0
        assert result.recent_pods == 3
