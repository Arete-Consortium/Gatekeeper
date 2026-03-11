"""Unit tests for market hub ESI service."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.services.market_hubs import (
    CACHE_TTL,
    HUB_DEFINITIONS,
    ORDERS_PER_PAGE,
    MarketHubData,
    _fetch_region_order_pages,
    clear_cache,
    fetch_market_hub_data,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the module-level cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


class TestFetchRegionOrderPages:
    """Tests for _fetch_region_order_pages."""

    @pytest.mark.asyncio
    async def test_returns_page_count_from_header(self):
        """Should parse X-Pages header into integer."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"x-pages": "347"}

        client = AsyncMock(spec=httpx.AsyncClient)
        client.head = AsyncMock(return_value=mock_response)

        result = await _fetch_region_order_pages(client, 10000002)
        assert result == 347

        # Verify correct URL and params
        client.head.assert_called_once()
        call_args = client.head.call_args
        assert "10000002" in call_args.args[0]
        assert call_args.kwargs["params"] == {"order_type": "all", "page": 1}

    @pytest.mark.asyncio
    async def test_defaults_to_1_page_when_header_missing(self):
        """Should default to 1 page when X-Pages header is absent."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}

        client = AsyncMock(spec=httpx.AsyncClient)
        client.head = AsyncMock(return_value=mock_response)

        result = await _fetch_region_order_pages(client, 10000002)
        assert result == 1

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        """Should return None when ESI returns an error."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.head = AsyncMock(
            side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=MagicMock())
        )

        result = await _fetch_region_order_pages(client, 10000002)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self):
        """Should return None on connection timeout."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.head = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))

        result = await _fetch_region_order_pages(client, 10000002)
        assert result is None


class TestFetchMarketHubData:
    """Tests for fetch_market_hub_data."""

    @pytest.mark.asyncio
    async def test_returns_all_five_hubs(self):
        """Should return data for all 5 trade hubs."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"x-pages": "100"}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_market_hub_data()

        assert len(result) == 5
        assert all(isinstance(h, MarketHubData) for h in result)

        # Verify hub names
        names = {h.system_name for h in result}
        assert names == {"Jita", "Amarr", "Dodixie", "Rens", "Hek"}

    @pytest.mark.asyncio
    async def test_calculates_active_orders_from_pages(self):
        """Should multiply pages by ORDERS_PER_PAGE."""
        pages_by_region = {
            10000002: 350,  # The Forge (Jita)
            10000043: 120,  # Domain (Amarr)
            10000032: 40,  # Sinq Laison (Dodixie)
            10000030: 30,  # Heimatar (Rens)
            10000042: 20,  # Metropolis (Hek)
        }

        async def mock_head(url, **kwargs):
            for region_id, pages in pages_by_region.items():
                if str(region_id) in url:
                    resp = MagicMock()
                    resp.raise_for_status = MagicMock()
                    resp.headers = {"x-pages": str(pages)}
                    return resp
            raise httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_market_hub_data()

        jita = next(h for h in result if h.system_name == "Jita")
        assert jita.active_orders == 350 * ORDERS_PER_PAGE
        assert jita.is_primary is True

        amarr = next(h for h in result if h.system_name == "Amarr")
        assert amarr.active_orders == 120 * ORDERS_PER_PAGE

    @pytest.mark.asyncio
    async def test_jita_is_primary(self):
        """Jita should be marked as primary hub."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"x-pages": "10"}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_market_hub_data()

        primary_hubs = [h for h in result if h.is_primary]
        assert len(primary_hubs) == 1
        assert primary_hubs[0].system_name == "Jita"

    @pytest.mark.asyncio
    async def test_fallback_on_total_esi_failure(self):
        """Should return static fallback when ESI is completely down."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("ESI down"))
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_market_hub_data()

        assert len(result) == 5
        # All should have 0 active orders (static fallback)
        assert all(h.active_orders == 0 for h in result)
        # But should still have static volume estimates
        jita = next(h for h in result if h.system_name == "Jita")
        assert jita.daily_volume_estimate == 50_000_000_000_000

    @pytest.mark.asyncio
    async def test_partial_esi_failure(self):
        """Should handle partial ESI failures gracefully."""
        call_count = 0

        async def mock_head(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "10000002" in url:  # Jita succeeds
                resp = MagicMock()
                resp.raise_for_status = MagicMock()
                resp.headers = {"x-pages": "300"}
                return resp
            # All others fail
            raise httpx.HTTPStatusError("503", request=MagicMock(), response=MagicMock())

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(side_effect=mock_head)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_market_hub_data()

        jita = next(h for h in result if h.system_name == "Jita")
        assert jita.active_orders == 300 * ORDERS_PER_PAGE

        # Others should have 0 orders (individual fetch failed)
        amarr = next(h for h in result if h.system_name == "Amarr")
        assert amarr.active_orders == 0

    @pytest.mark.asyncio
    async def test_cache_returns_same_data(self):
        """Should return cached data on second call."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"x-pages": "50"}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result1 = await fetch_market_hub_data()
            result2 = await fetch_market_hub_data()

        # Should be the exact same list object (cached)
        assert result1 is result2
        # httpx client should only have been created once
        assert mock_client.__aenter__.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self):
        """Should refetch after cache TTL expires."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"x-pages": "50"}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result1 = await fetch_market_hub_data()

            # Expire cache by manipulating timestamp
            import backend.app.services.market_hubs as mh_module

            mh_module._cache.timestamp = time.monotonic() - CACHE_TTL - 1

            result2 = await fetch_market_hub_data()

        # Should have fetched twice
        assert mock_client.__aenter__.call_count == 2
        assert result1 is not result2

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """clear_cache should force a refetch on next call."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"x-pages": "25"}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            await fetch_market_hub_data()
            clear_cache()
            await fetch_market_hub_data()

        assert mock_client.__aenter__.call_count == 2

    @pytest.mark.asyncio
    async def test_hub_definitions_match_expected_systems(self):
        """Verify hub definitions contain the correct system IDs."""
        expected_ids = {30000142, 30002187, 30002659, 30002510, 30002053}
        actual_ids = {sid for sid, _, _, _, _, _ in HUB_DEFINITIONS}
        assert actual_ids == expected_ids

    @pytest.mark.asyncio
    async def test_hub_definitions_match_expected_regions(self):
        """Verify hub definitions contain the correct region IDs."""
        expected_regions = {10000002, 10000043, 10000032, 10000030, 10000042}
        actual_regions = {rid for _, _, rid, _, _, _ in HUB_DEFINITIONS}
        assert actual_regions == expected_regions


class TestMarketHubDataModel:
    """Tests for MarketHubData output structure (endpoint contract)."""

    def test_hub_data_has_all_required_fields(self):
        """MarketHubData should carry all fields the endpoint needs."""
        hub = MarketHubData(
            system_id=30000142,
            system_name="Jita",
            region_id=10000002,
            region_name="The Forge",
            is_primary=True,
            daily_volume_estimate=50_000_000_000_000,
            active_orders=350000,
        )
        assert hub.system_id == 30000142
        assert hub.system_name == "Jita"
        assert hub.region_name == "The Forge"
        assert hub.is_primary is True
        assert hub.daily_volume_estimate == 50_000_000_000_000
        assert hub.active_orders == 350000

    def test_hub_data_active_orders_zero_default(self):
        """active_orders=0 is the fallback when ESI is unavailable."""
        hub = MarketHubData(
            system_id=30002053,
            system_name="Hek",
            region_id=10000042,
            region_name="Metropolis",
            is_primary=False,
            daily_volume_estimate=1_000_000_000_000,
            active_orders=0,
        )
        assert hub.active_orders == 0
        assert hub.daily_volume_estimate == 1_000_000_000_000

    @pytest.mark.asyncio
    async def test_fetch_returns_data_matching_endpoint_contract(self):
        """fetch_market_hub_data output should map cleanly to response model fields."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"x-pages": "200"}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.services.market_hubs.httpx.AsyncClient", return_value=mock_client):
            result = await fetch_market_hub_data()

        # Verify each hub has the fields the endpoint model expects
        for hub in result:
            assert isinstance(hub.system_id, int)
            assert isinstance(hub.system_name, str)
            assert isinstance(hub.region_name, str)
            assert isinstance(hub.is_primary, bool)
            assert isinstance(hub.daily_volume_estimate, (int, float))
            assert isinstance(hub.active_orders, int)
            assert hub.active_orders >= 0
