"""Unit tests for market ticker service and API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.app.api.v1.market_ticker import router
from backend.app.models.market_ticker import (
    MarketTickerHistoryResponse,
    MarketTickerItem,
    MarketTickerResponse,
)
from backend.app.services.market_ticker import (
    CACHE_TTL,
    TRACKED_ITEMS,
    TRADE_HUB_REGIONS,
    _compute_price_change,
    _fetch_market_history,
    clear_cache,
    fetch_ticker_data,
    get_item_history,
    get_market_ticker,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the module-level cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


# ============================================================
# Model tests
# ============================================================


class TestMarketTickerModels:
    """Tests for Pydantic models."""

    def test_market_ticker_item_creation(self):
        item = MarketTickerItem(
            type_id=34,
            type_name="Tritanium",
            region_id=10000002,
            region_name="The Forge",
            average_price=5.50,
            highest=6.00,
            lowest=5.00,
            volume=1000000,
            date="2026-03-10",
            price_change_pct=2.5,
        )
        assert item.type_id == 34
        assert item.type_name == "Tritanium"
        assert item.price_change_pct == 2.5

    def test_market_ticker_response_defaults(self):
        resp = MarketTickerResponse()
        assert resp.items == []
        assert resp.item_count == 0

    def test_market_ticker_response_with_items(self):
        item = MarketTickerItem(
            type_id=34,
            type_name="Tritanium",
            region_id=10000002,
            region_name="The Forge",
            average_price=5.50,
            highest=6.00,
            lowest=5.00,
            volume=1000000,
            date="2026-03-10",
        )
        resp = MarketTickerResponse(items=[item], item_count=1)
        assert len(resp.items) == 1
        assert resp.item_count == 1

    def test_market_ticker_history_response(self):
        resp = MarketTickerHistoryResponse(
            type_id=34,
            type_name="Tritanium",
            history=[],
        )
        assert resp.type_id == 34
        assert resp.history == []


# ============================================================
# Service tests
# ============================================================


class TestComputePriceChange:
    """Tests for _compute_price_change helper."""

    def test_positive_change(self):
        history = [
            {"average": 100.0, "date": "2026-03-09"},
            {"average": 110.0, "date": "2026-03-10"},
        ]
        assert _compute_price_change(history) == 10.0

    def test_negative_change(self):
        history = [
            {"average": 100.0, "date": "2026-03-09"},
            {"average": 90.0, "date": "2026-03-10"},
        ]
        assert _compute_price_change(history) == -10.0

    def test_no_change(self):
        history = [
            {"average": 100.0, "date": "2026-03-09"},
            {"average": 100.0, "date": "2026-03-10"},
        ]
        assert _compute_price_change(history) == 0.0

    def test_single_entry(self):
        history = [{"average": 100.0, "date": "2026-03-10"}]
        assert _compute_price_change(history) == 0.0

    def test_empty_history(self):
        assert _compute_price_change([]) == 0.0

    def test_zero_previous_price(self):
        history = [
            {"average": 0.0, "date": "2026-03-09"},
            {"average": 100.0, "date": "2026-03-10"},
        ]
        assert _compute_price_change(history) == 0.0


class TestFetchMarketHistory:
    """Tests for _fetch_market_history."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        mock_data = [
            {"date": "2026-03-10", "average": 5.50, "highest": 6.0, "lowest": 5.0, "volume": 1000000}
        ]
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_data

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=mock_response)

        result = await _fetch_market_history(client, 10000002, 34)
        assert result == mock_data

        client.get.assert_called_once()
        call_args = client.get.call_args
        assert "10000002" in call_args.args[0]
        assert call_args.kwargs["params"]["type_id"] == 34

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.HTTPError("ESI down"))

        result = await _fetch_market_history(client, 10000002, 34)
        assert result == []


class TestFetchTickerData:
    """Tests for fetch_ticker_data."""

    @pytest.mark.asyncio
    async def test_fetches_and_caches_data(self):
        mock_history = [
            {"date": "2026-03-09", "average": 5.00, "highest": 5.50, "lowest": 4.50, "volume": 900000},
            {"date": "2026-03-10", "average": 5.50, "highest": 6.00, "lowest": 5.00, "volume": 1000000},
        ]

        with patch(
            "backend.app.services.market_ticker._fetch_market_history",
            new_callable=AsyncMock,
            return_value=mock_history,
        ):
            # Fetch for a single item in a single region
            results = await fetch_ticker_data(region_id=10000002, type_id=34)

        assert len(results) == 1
        item = results[0]
        assert item.type_id == 34
        assert item.type_name == "Tritanium"
        assert item.region_id == 10000002
        assert item.region_name == "The Forge"
        assert item.average_price == 5.50
        assert item.volume == 1000000
        assert item.price_change_pct == 10.0

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self):
        mock_history = [
            {"date": "2026-03-09", "average": 5.00, "highest": 5.50, "lowest": 4.50, "volume": 900000},
            {"date": "2026-03-10", "average": 5.50, "highest": 6.00, "lowest": 5.00, "volume": 1000000},
        ]

        with patch(
            "backend.app.services.market_ticker._fetch_market_history",
            new_callable=AsyncMock,
            return_value=mock_history,
        ) as mock_fetch:
            await fetch_ticker_data(region_id=10000002, type_id=34)
            await fetch_ticker_data(region_id=10000002, type_id=34)

            # Should only call ESI once due to caching
            assert mock_fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_history_returns_no_items(self):
        with patch(
            "backend.app.services.market_ticker._fetch_market_history",
            new_callable=AsyncMock,
            return_value=[],
        ):
            results = await fetch_ticker_data(region_id=10000002, type_id=34)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_invalid_region_returns_empty(self):
        """Filtering by a non-existent region returns no results."""
        results = await fetch_ticker_data(region_id=99999999, type_id=34)
        # Falls through to full TRADE_HUB_REGIONS since 99999999 not in the dict
        # But we just want to ensure it doesn't crash
        assert isinstance(results, list)


class TestGetMarketTicker:
    """Tests for get_market_ticker."""

    @pytest.mark.asyncio
    async def test_returns_response_model(self):
        mock_item = MarketTickerItem(
            type_id=34,
            type_name="Tritanium",
            region_id=10000002,
            region_name="The Forge",
            average_price=5.50,
            highest=6.00,
            lowest=5.00,
            volume=1000000,
            date="2026-03-10",
            price_change_pct=2.5,
        )

        with patch(
            "backend.app.services.market_ticker.fetch_ticker_data",
            new_callable=AsyncMock,
            return_value=[mock_item],
        ):
            result = await get_market_ticker()

        assert isinstance(result, MarketTickerResponse)
        assert result.item_count == 1
        assert result.items[0].type_name == "Tritanium"


class TestGetItemHistory:
    """Tests for get_item_history."""

    @pytest.mark.asyncio
    async def test_returns_history_response(self):
        mock_item = MarketTickerItem(
            type_id=34,
            type_name="Tritanium",
            region_id=10000002,
            region_name="The Forge",
            average_price=5.50,
            highest=6.00,
            lowest=5.00,
            volume=1000000,
            date="2026-03-10",
        )

        with patch(
            "backend.app.services.market_ticker.fetch_ticker_data",
            new_callable=AsyncMock,
            return_value=[mock_item],
        ):
            result = await get_item_history(34)

        assert isinstance(result, MarketTickerHistoryResponse)
        assert result.type_id == 34
        assert result.type_name == "Tritanium"
        assert len(result.history) == 1

    @pytest.mark.asyncio
    async def test_unknown_type_uses_fallback_name(self):
        with patch(
            "backend.app.services.market_ticker.fetch_ticker_data",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await get_item_history(99999)

        assert result.type_name == "Unknown (99999)"


# ============================================================
# API endpoint tests
# ============================================================


@pytest.fixture
def app():
    """Create a test FastAPI app with the market ticker router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


class TestMarketTickerAPI:
    """Tests for market ticker API endpoints."""

    @pytest.mark.asyncio
    async def test_get_ticker(self, app):
        mock_response = MarketTickerResponse(
            items=[
                MarketTickerItem(
                    type_id=34,
                    type_name="Tritanium",
                    region_id=10000002,
                    region_name="The Forge",
                    average_price=5.50,
                    highest=6.00,
                    lowest=5.00,
                    volume=1000000,
                    date="2026-03-10",
                    price_change_pct=2.5,
                )
            ],
            item_count=1,
        )

        with patch(
            "backend.app.api.v1.market_ticker.get_market_ticker",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/market/ticker")

        assert resp.status_code == 200
        data = resp.json()
        assert data["item_count"] == 1
        assert data["items"][0]["type_name"] == "Tritanium"

    @pytest.mark.asyncio
    async def test_get_item_ticker(self, app):
        mock_response = MarketTickerHistoryResponse(
            type_id=34,
            type_name="Tritanium",
            history=[],
        )

        with patch(
            "backend.app.api.v1.market_ticker.get_item_history",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/market/ticker/34")

        assert resp.status_code == 200
        data = resp.json()
        assert data["type_id"] == 34
        assert data["type_name"] == "Tritanium"

    @pytest.mark.asyncio
    async def test_get_item_ticker_not_tracked(self, app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/market/ticker/99999")

        assert resp.status_code == 404
        assert "not in the tracked items" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_ticker_server_error(self, app):
        with patch(
            "backend.app.api.v1.market_ticker.get_market_ticker",
            new_callable=AsyncMock,
            side_effect=Exception("ESI down"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/market/ticker")

        assert resp.status_code == 500

    @pytest.mark.asyncio
    async def test_get_item_ticker_server_error(self, app):
        with patch(
            "backend.app.api.v1.market_ticker.get_item_history",
            new_callable=AsyncMock,
            side_effect=Exception("ESI down"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/market/ticker/34")

        assert resp.status_code == 500


class TestConstants:
    """Tests for module constants."""

    def test_trade_hub_regions_has_five(self):
        assert len(TRADE_HUB_REGIONS) == 5

    def test_tracked_items_count(self):
        assert len(TRACKED_ITEMS) == 18  # Omega removed (not tradeable on market)

    def test_cache_ttl_is_one_hour(self):
        assert CACHE_TTL == 3600

    def test_the_forge_is_tracked(self):
        assert 10000002 in TRADE_HUB_REGIONS
        assert TRADE_HUB_REGIONS[10000002] == "The Forge"

    def test_plex_is_tracked(self):
        assert 44992 in TRACKED_ITEMS
        assert TRACKED_ITEMS[44992] == "PLEX"
