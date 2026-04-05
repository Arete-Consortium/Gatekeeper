"""Tests for market arbitrage API endpoints and service logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.api.v1.arbitrage import arbitrage_compare, popular_items
from backend.app.models.arbitrage import (
    ArbitrageCompareResponse,
    ArbitrageOpportunity,
    HubPriceData,
    PopularItem,
    PopularItemsResponse,
)
from backend.app.services.arbitrage import (
    CACHE_TTL,
    POPULAR_ITEMS,
    TRADE_HUBS,
    _compare_cache,
    _fetch_hub_orders,
    _name_cache,
    _resolve_type_name,
    compare_hubs,
    get_popular_items,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear module-level caches before and after each test."""
    _compare_cache.clear()
    # Preserve the default name cache entries, only remove extras
    known_ids = {item.type_id for item in POPULAR_ITEMS}
    extras = [k for k in _name_cache if k not in known_ids]
    for k in extras:
        del _name_cache[k]
    yield
    _compare_cache.clear()
    extras = [k for k in _name_cache if k not in known_ids]
    for k in extras:
        del _name_cache[k]


# =============================================================================
# Model Tests
# =============================================================================


class TestArbitrageModels:
    """Tests for arbitrage Pydantic models."""

    def test_hub_price_data_defaults(self):
        data = HubPriceData(system_id=30000142, system_name="Jita", region_id=10000002)
        assert data.best_buy == 0.0
        assert data.best_sell == 0.0
        assert data.spread == 0.0
        assert data.buy_volume == 0
        assert data.sell_volume == 0

    def test_hub_price_data_with_values(self):
        data = HubPriceData(
            system_id=30000142,
            system_name="Jita",
            region_id=10000002,
            best_buy=100.0,
            best_sell=110.0,
            spread=9.09,
            buy_volume=5000,
            sell_volume=3000,
        )
        assert data.best_buy == 100.0
        assert data.sell_volume == 3000

    def test_arbitrage_opportunity(self):
        opp = ArbitrageOpportunity(
            buy_hub="Jita",
            buy_hub_id=30000142,
            buy_price=100.0,
            sell_hub="Amarr",
            sell_hub_id=30002187,
            sell_price=115.0,
            profit_per_unit=15.0,
            margin_pct=15.0,
        )
        assert opp.profit_per_unit == 15.0
        assert opp.margin_pct == 15.0

    def test_arbitrage_compare_response_defaults(self):
        resp = ArbitrageCompareResponse(type_id=34)
        assert resp.type_name == ""
        assert resp.hubs == []
        assert resp.opportunities == []

    def test_popular_item(self):
        item = PopularItem(type_id=34, name="Tritanium", category="Minerals")
        assert item.type_id == 34
        assert item.category == "Minerals"

    def test_popular_items_response(self):
        resp = PopularItemsResponse(
            items=[PopularItem(type_id=34, name="Tritanium", category="Minerals")],
            count=1,
        )
        assert resp.count == 1
        assert len(resp.items) == 1


# =============================================================================
# Name Resolution
# =============================================================================


class TestNameResolution:
    """Tests for type name resolution via ESI."""

    @pytest.mark.asyncio
    async def test_resolve_cached_name(self):
        """Popular item names are resolved from cache without ESI call."""
        name = await _resolve_type_name(34)  # Tritanium
        assert name == "Tritanium"

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage.httpx.AsyncClient")
    async def test_resolve_unknown_name_from_esi(self, mock_client_cls):
        """Unknown type IDs are resolved via ESI POST."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = [{"name": "Exotic Dancers"}]

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        name = await _resolve_type_name(99999)
        assert name == "Exotic Dancers"
        # Should be cached now
        assert _name_cache[99999] == "Exotic Dancers"

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage.httpx.AsyncClient")
    async def test_resolve_name_esi_failure(self, mock_client_cls):
        """ESI failure returns fallback name."""
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("ESI down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        name = await _resolve_type_name(88888)
        assert name == "Type 88888"

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage.httpx.AsyncClient")
    async def test_resolve_name_empty_response(self, mock_client_cls):
        """Empty ESI response returns fallback name."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = []

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        name = await _resolve_type_name(77777)
        assert name == "Type 77777"


# =============================================================================
# Fetch Hub Orders
# =============================================================================


class TestFetchHubOrders:
    """Tests for ESI market order fetching."""

    @pytest.mark.asyncio
    async def test_fetch_orders_basic(self):
        """Fetches and filters orders to hub system."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"x-pages": "1"}
        mock_resp.json.return_value = [
            {"system_id": 30000142, "is_buy_order": True, "price": 100.0, "volume_remain": 500},
            {"system_id": 30000142, "is_buy_order": False, "price": 110.0, "volume_remain": 300},
            {"system_id": 99999999, "is_buy_order": False, "price": 90.0, "volume_remain": 200},
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        best_buy, best_sell, buy_vol, sell_vol = await _fetch_hub_orders(
            mock_client, 10000002, 34, 30000142
        )

        assert best_buy == 100.0
        assert best_sell == 110.0
        assert buy_vol == 500
        assert sell_vol == 300

    @pytest.mark.asyncio
    async def test_fetch_orders_no_orders(self):
        """Empty order response returns zeros."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"x-pages": "1"}
        mock_resp.json.return_value = []

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        best_buy, best_sell, buy_vol, sell_vol = await _fetch_hub_orders(
            mock_client, 10000002, 34, 30000142
        )

        assert best_buy == 0.0
        assert best_sell == 0.0
        assert buy_vol == 0
        assert sell_vol == 0

    @pytest.mark.asyncio
    async def test_fetch_orders_multipage(self):
        """Multi-page responses are combined."""
        page1_resp = MagicMock()
        page1_resp.status_code = 200
        page1_resp.raise_for_status = MagicMock()
        page1_resp.headers = {"x-pages": "2"}
        page1_resp.json.return_value = [
            {"system_id": 30000142, "is_buy_order": True, "price": 100.0, "volume_remain": 500},
        ]

        page2_resp = MagicMock()
        page2_resp.status_code = 200
        page2_resp.raise_for_status = MagicMock()
        page2_resp.headers = {"x-pages": "2"}
        page2_resp.json.return_value = [
            {"system_id": 30000142, "is_buy_order": True, "price": 105.0, "volume_remain": 300},
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[page1_resp, page2_resp])

        best_buy, best_sell, buy_vol, sell_vol = await _fetch_hub_orders(
            mock_client, 10000002, 34, 30000142
        )

        assert best_buy == 105.0  # max of 100 and 105
        assert buy_vol == 800  # 500 + 300

    @pytest.mark.asyncio
    async def test_fetch_orders_esi_error(self):
        """ESI error returns zeros (graceful degradation)."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("ESI 500"))

        best_buy, best_sell, buy_vol, sell_vol = await _fetch_hub_orders(
            mock_client, 10000002, 34, 30000142
        )

        assert best_buy == 0.0
        assert best_sell == 0.0

    @pytest.mark.asyncio
    async def test_fetch_orders_only_buy(self):
        """Hub with only buy orders returns zero sell."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_resp.headers = {"x-pages": "1"}
        mock_resp.json.return_value = [
            {"system_id": 30000142, "is_buy_order": True, "price": 95.0, "volume_remain": 1000},
        ]

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        best_buy, best_sell, buy_vol, sell_vol = await _fetch_hub_orders(
            mock_client, 10000002, 34, 30000142
        )

        assert best_buy == 95.0
        assert best_sell == 0.0
        assert sell_vol == 0


# =============================================================================
# Compare Hubs (Service)
# =============================================================================


class TestCompareHubs:
    """Tests for compare_hubs service function."""

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_default_hubs(self, mock_fetch, mock_name):
        """Compare with default hubs uses all 5 major hubs."""
        mock_name.return_value = "Tritanium"
        mock_fetch.return_value = (100.0, 110.0, 5000, 3000)

        result = await compare_hubs(34)

        assert isinstance(result, ArbitrageCompareResponse)
        assert result.type_id == 34
        assert result.type_name == "Tritanium"
        assert len(result.hubs) == 5

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_specific_hubs(self, mock_fetch, mock_name):
        """Compare with specific hub IDs only fetches those hubs."""
        mock_name.return_value = "Tritanium"
        mock_fetch.return_value = (100.0, 110.0, 5000, 3000)

        result = await compare_hubs(34, [30000142, 30002187])  # Jita, Amarr

        assert len(result.hubs) == 2
        hub_names = {h.system_name for h in result.hubs}
        assert hub_names == {"Jita", "Amarr"}

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_invalid_hub_ids_fallback(self, mock_fetch, mock_name):
        """Invalid hub IDs fall back to all 5 major hubs."""
        mock_name.return_value = "Tritanium"
        mock_fetch.return_value = (100.0, 110.0, 5000, 3000)

        result = await compare_hubs(34, [99999])  # Not a real hub

        assert len(result.hubs) == 5  # Falls back to all hubs

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_detects_arbitrage(self, mock_fetch, mock_name):
        """Arbitrage opportunities are detected when price differentials exist."""
        mock_name.return_value = "Tritanium"

        # Jita: sell at 100, buy at 95
        # Amarr: sell at 90, buy at 105
        # Opportunity: buy at Amarr sell (90) -> sell at Amarr buy... no
        # Actually: buy at Amarr (best_sell=90), sell at Jita (best_buy=95) -> profit 5
        call_count = 0

        async def side_effect(client, region_id, type_id, system_id):
            nonlocal call_count
            call_count += 1
            if system_id == 30000142:  # Jita
                return (95.0, 100.0, 5000, 3000)
            elif system_id == 30002187:  # Amarr
                return (105.0, 90.0, 4000, 2000)
            else:
                return (80.0, 110.0, 1000, 500)

        mock_fetch.side_effect = side_effect

        result = await compare_hubs(34, [30000142, 30002187])

        # Amarr sell (90) -> Jita buy (95) = 5 ISK profit
        # Amarr sell (90) -> Amarr buy (105) = 15 ISK profit... wait, same hub excluded
        # Jita sell (100) -> Amarr buy (105) = 5 ISK profit
        assert len(result.opportunities) > 0
        # Check sorted by margin desc
        if len(result.opportunities) > 1:
            assert result.opportunities[0].margin_pct >= result.opportunities[1].margin_pct

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_no_arbitrage(self, mock_fetch, mock_name):
        """No opportunities when prices don't have cross-hub differential."""
        mock_name.return_value = "Tritanium"
        # Same prices everywhere, buy < sell within each hub
        mock_fetch.return_value = (90.0, 100.0, 5000, 3000)

        result = await compare_hubs(34, [30000142, 30002187])

        # buy_hub.best_sell (100) vs sell_hub.best_buy (90) -> profit = -10 -> no opportunity
        assert len(result.opportunities) == 0

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_spread_calculation(self, mock_fetch, mock_name):
        """Spread is calculated correctly."""
        mock_name.return_value = "Tritanium"
        mock_fetch.return_value = (90.0, 100.0, 5000, 3000)

        result = await compare_hubs(34, [30000142])

        # spread = ((100 - 90) / 100) * 100 = 10.0%
        assert result.hubs[0].spread == 10.0

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_caching(self, mock_fetch, mock_name):
        """Second call within TTL returns cached result."""
        mock_name.return_value = "Tritanium"
        mock_fetch.return_value = (100.0, 110.0, 5000, 3000)

        result1 = await compare_hubs(34, [30000142])
        result2 = await compare_hubs(34, [30000142])

        # _fetch_hub_orders should only be called once (cached second time)
        assert mock_fetch.call_count == 1
        assert result1 == result2

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage.time")
    async def test_compare_cache_expiry(self, mock_time, mock_fetch, mock_name):
        """Expired cache entries are re-fetched."""
        mock_name.return_value = "Tritanium"
        mock_fetch.return_value = (100.0, 110.0, 5000, 3000)

        # First call at time 1000
        mock_time.time.return_value = 1000.0
        await compare_hubs(34, [30000142])

        # Second call after TTL expires
        mock_time.time.return_value = 1000.0 + CACHE_TTL + 1
        await compare_hubs(34, [30000142])

        assert mock_fetch.call_count == 2

    @pytest.mark.asyncio
    @patch("backend.app.services.arbitrage._resolve_type_name", new_callable=AsyncMock)
    @patch("backend.app.services.arbitrage._fetch_hub_orders", new_callable=AsyncMock)
    async def test_compare_zero_prices_no_spread(self, mock_fetch, mock_name):
        """Zero prices result in zero spread (no division by zero)."""
        mock_name.return_value = "Unknown"
        mock_fetch.return_value = (0.0, 0.0, 0, 0)

        result = await compare_hubs(99999, [30000142])

        assert result.hubs[0].spread == 0.0
        assert result.hubs[0].best_buy == 0.0
        assert result.hubs[0].best_sell == 0.0


# =============================================================================
# Popular Items (Service)
# =============================================================================


class TestGetPopularItems:
    """Tests for get_popular_items service."""

    @pytest.mark.asyncio
    async def test_returns_all_items(self):
        result = await get_popular_items()
        assert isinstance(result, PopularItemsResponse)
        assert result.count == len(POPULAR_ITEMS)
        assert len(result.items) == result.count

    @pytest.mark.asyncio
    async def test_items_have_categories(self):
        result = await get_popular_items()
        categories = {item.category for item in result.items}
        assert "Minerals" in categories
        assert "Services" in categories
        assert "Fuel" in categories

    @pytest.mark.asyncio
    async def test_tritanium_in_popular(self):
        result = await get_popular_items()
        trit = [i for i in result.items if i.name == "Tritanium"]
        assert len(trit) == 1
        assert trit[0].type_id == 34


# =============================================================================
# API Endpoint Tests
# =============================================================================


class TestArbitrageEndpoints:
    """Tests for arbitrage API endpoints via direct function calls."""

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.arbitrage.compare_hubs", new_callable=AsyncMock)
    async def test_compare_endpoint_success(self, mock_compare):
        """Compare endpoint returns service result."""
        mock_compare.return_value = ArbitrageCompareResponse(
            type_id=34,
            type_name="Tritanium",
            hubs=[],
            opportunities=[],
        )

        result = await arbitrage_compare(type_id=34, hubs=None)

        assert result.type_id == 34
        mock_compare.assert_called_once_with(34, None)

    @pytest.mark.asyncio
    async def test_compare_endpoint_invalid_type_id(self):
        """Negative type_id returns 400."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await arbitrage_compare(type_id=-1, hubs=None)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_compare_endpoint_zero_type_id(self):
        """Zero type_id returns 400."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await arbitrage_compare(type_id=0, hubs=None)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.arbitrage.compare_hubs", new_callable=AsyncMock)
    async def test_compare_endpoint_with_hubs_param(self, mock_compare):
        """Hubs query param is parsed into list of ints."""
        mock_compare.return_value = ArbitrageCompareResponse(type_id=34)

        await arbitrage_compare(type_id=34, hubs="30000142,30002187")

        mock_compare.assert_called_once_with(34, [30000142, 30002187])

    @pytest.mark.asyncio
    async def test_compare_endpoint_invalid_hubs_param(self):
        """Non-integer hubs param returns 400."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await arbitrage_compare(type_id=34, hubs="jita,amarr")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.arbitrage.compare_hubs", new_callable=AsyncMock)
    async def test_compare_endpoint_service_error(self, mock_compare):
        """Service exception returns 500."""
        from fastapi import HTTPException

        mock_compare.side_effect = RuntimeError("ESI down")

        with pytest.raises(HTTPException) as exc:
            await arbitrage_compare(type_id=34, hubs=None)
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.arbitrage.get_popular_items", new_callable=AsyncMock)
    async def test_popular_endpoint_success(self, mock_popular):
        """Popular endpoint returns item list."""
        mock_popular.return_value = PopularItemsResponse(
            items=[PopularItem(type_id=34, name="Tritanium", category="Minerals")],
            count=1,
        )

        result = await popular_items()

        assert result.count == 1

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.arbitrage.get_popular_items", new_callable=AsyncMock)
    async def test_popular_endpoint_service_error(self, mock_popular):
        """Popular endpoint service error returns 500."""
        from fastapi import HTTPException

        mock_popular.side_effect = RuntimeError("broken")

        with pytest.raises(HTTPException) as exc:
            await popular_items()
        assert exc.value.status_code == 500


# =============================================================================
# Trade Hub Constants
# =============================================================================


class TestTradeHubConstants:
    """Tests for trade hub configuration."""

    def test_all_five_hubs_present(self):
        assert len(TRADE_HUBS) == 5

    def test_jita_is_in_the_forge(self):
        system_name, region_id = TRADE_HUBS[30000142]
        assert system_name == "Jita"
        assert region_id == 10000002

    def test_amarr_is_in_domain(self):
        system_name, region_id = TRADE_HUBS[30002187]
        assert system_name == "Amarr"
        assert region_id == 10000043

    def test_popular_items_count(self):
        assert len(POPULAR_ITEMS) >= 20  # Curated list should be substantial
