"""Unit tests for appraisal service — parse_items, resolve_names, get_jita_prices, appraise."""

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.app.models.appraisal import AppraisalResponse
from backend.app.services.appraisal import (
    BATCH_SIZE,
    PRICE_CACHE_TTL,
    appraise,
    get_jita_prices,
    parse_items,
    resolve_names,
)


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear module-level caches before each test."""
    import backend.app.services.appraisal as mod

    mod._name_cache.clear()
    mod._price_cache.clear()
    mod._price_cache_time.clear()
    yield
    mod._name_cache.clear()
    mod._price_cache.clear()
    mod._price_cache_time.clear()


# ---------------------------------------------------------------------------
# parse_items
# ---------------------------------------------------------------------------


class TestParseItems:
    """Tests for parse_items() text parsing."""

    def test_tab_separated(self):
        """Tab-separated format: name<TAB>quantity."""
        result = parse_items("Tritanium\t1000")
        assert result == [("Tritanium", 1000)]

    def test_tab_separated_with_commas(self):
        """Tab-separated with comma-formatted quantity."""
        result = parse_items("Tritanium\t1,000")
        assert result == [("Tritanium", 1000)]

    def test_tab_separated_extra_fields(self):
        """Tab-separated with extra columns ignored."""
        result = parse_items("Tritanium\t500\tsome extra")
        assert result == [("Tritanium", 500)]

    def test_tab_separated_invalid_qty_defaults_to_1(self):
        """Tab-separated with non-numeric qty defaults to 1."""
        result = parse_items("Tritanium\tabc")
        assert result == [("Tritanium", 1)]

    def test_quantity_prefix(self):
        """Quantity prefix format: 1000 Tritanium."""
        result = parse_items("1000 Tritanium")
        assert result == [("Tritanium", 1000)]

    def test_quantity_prefix_with_commas(self):
        """Quantity prefix with comma-formatted quantity."""
        result = parse_items("1,000 Tritanium")
        assert result == [("Tritanium", 1000)]

    def test_quantity_suffix(self):
        """Quantity suffix format: Tritanium 1000."""
        result = parse_items("Tritanium 1000")
        assert result == [("Tritanium", 1000)]

    def test_multiplier_x(self):
        """Multiplier format: Tritanium x1000."""
        result = parse_items("Tritanium x1000")
        assert result == [("Tritanium", 1000)]

    def test_multiplier_x_space(self):
        """Multiplier format with space: Tritanium x 1000."""
        result = parse_items("Tritanium x 1000")
        assert result == [("Tritanium", 1000)]

    def test_name_only_defaults_qty_1(self):
        """Name-only line defaults to quantity 1."""
        result = parse_items("Tritanium")
        assert result == [("Tritanium", 1)]

    def test_skip_empty_lines(self):
        """Empty lines are skipped."""
        result = parse_items("\n\n  \nTritanium\n\n")
        assert result == [("Tritanium", 1)]

    def test_skip_fitting_headers(self):
        """Lines starting with [ are skipped (fitting headers)."""
        result = parse_items("[Raven, Travel Fit]\nTritanium\t100")
        assert result == [("Tritanium", 100)]

    def test_multiple_items(self):
        """Multiple items parsed correctly."""
        text = "Tritanium\t1000\nPyerite\t500\nMexallon\t200"
        result = parse_items(text)
        assert len(result) == 3
        assert result[0] == ("Tritanium", 1000)
        assert result[1] == ("Pyerite", 500)
        assert result[2] == ("Mexallon", 200)

    def test_empty_input(self):
        """Empty string returns empty list."""
        assert parse_items("") == []

    def test_only_whitespace(self):
        """Whitespace-only input returns empty list."""
        assert parse_items("   \n  \n  ") == []

    def test_only_fitting_header(self):
        """Only fitting header returns empty list."""
        assert parse_items("[Raven, Travel Fit]") == []

    def test_multi_word_item_name(self):
        """Multi-word item names are handled."""
        result = parse_items("Large Shield Extender II\t5")
        assert result == [("Large Shield Extender II", 5)]

    def test_multi_word_name_only(self):
        """Multi-word item name with no quantity."""
        result = parse_items("Large Shield Extender II")
        assert result == [("Large Shield Extender II", 1)]


# ---------------------------------------------------------------------------
# resolve_names
# ---------------------------------------------------------------------------


class TestResolveNames:
    """Tests for resolve_names() ESI lookup."""

    @pytest.mark.asyncio
    async def test_resolve_single_name(self):
        """Resolves a single item name via ESI."""
        esi_response = {
            "inventory_types": [{"id": 34, "name": "Tritanium"}]
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            client.post.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await resolve_names(["Tritanium"])

        assert result == {"Tritanium": 34}

    @pytest.mark.asyncio
    async def test_resolve_uses_cache(self):
        """Cached names skip ESI call."""
        import backend.app.services.appraisal as mod

        mod._name_cache["tritanium"] = 34

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            result = await resolve_names(["Tritanium"])
            mock_cls.assert_not_called()

        assert result == {"Tritanium": 34}

    @pytest.mark.asyncio
    async def test_resolve_esi_error_returns_partial(self):
        """ESI error returns only cached results."""
        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.post.side_effect = httpx.HTTPError("ESI down")
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await resolve_names(["Tritanium"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_resolve_empty_list(self):
        """Empty name list returns empty dict without ESI call."""
        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            result = await resolve_names([])
            mock_cls.assert_not_called()

        assert result == {}

    @pytest.mark.asyncio
    async def test_resolve_unrecognized_name(self):
        """Names not found in ESI response are excluded."""
        esi_response = {"inventory_types": []}

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            client.post.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await resolve_names(["NotARealItem"])

        assert result == {}

    @pytest.mark.asyncio
    async def test_resolve_case_insensitive(self):
        """Name resolution is case-insensitive."""
        esi_response = {
            "inventory_types": [{"id": 34, "name": "Tritanium"}]
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            client.post.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await resolve_names(["tritanium"])

        assert result == {"tritanium": 34}


# ---------------------------------------------------------------------------
# get_jita_prices
# ---------------------------------------------------------------------------


class TestGetJitaPrices:
    """Tests for get_jita_prices() Fuzzwork lookup."""

    @pytest.mark.asyncio
    async def test_fetch_single_price(self):
        """Fetches price for a single type ID."""
        fuzz_response = {
            "34": {
                "buy": {"max": 5.5},
                "sell": {"min": 6.0},
            }
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            resp = httpx.Response(
                200,
                json=fuzz_response,
                request=httpx.Request("GET", "https://market.fuzzwork.co.uk/aggregates/"),
            )
            client.get.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await get_jita_prices([34])

        assert result[34] == (5.5, 6.0)

    @pytest.mark.asyncio
    async def test_price_cache_hit(self):
        """Cached prices skip Fuzzwork call."""
        import backend.app.services.appraisal as mod

        mod._price_cache[34] = (5.5, 6.0)
        mod._price_cache_time[34] = time.time()

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            result = await get_jita_prices([34])
            mock_cls.assert_not_called()

        assert result[34] == (5.5, 6.0)

    @pytest.mark.asyncio
    async def test_price_cache_expired(self):
        """Expired cache entries trigger a fresh fetch."""
        import backend.app.services.appraisal as mod

        mod._price_cache[34] = (5.5, 6.0)
        mod._price_cache_time[34] = time.time() - PRICE_CACHE_TTL - 10

        fuzz_response = {
            "34": {
                "buy": {"max": 5.8},
                "sell": {"min": 6.2},
            }
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            resp = httpx.Response(
                200,
                json=fuzz_response,
                request=httpx.Request("GET", "https://market.fuzzwork.co.uk/aggregates/"),
            )
            client.get.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await get_jita_prices([34])

        assert result[34] == (5.8, 6.2)

    @pytest.mark.asyncio
    async def test_empty_type_ids(self):
        """Empty type ID list returns empty dict."""
        result = await get_jita_prices([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_fuzzwork_error_skips_batch(self):
        """Fuzzwork HTTP error skips the batch gracefully."""
        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.side_effect = httpx.HTTPError("Fuzzwork down")
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await get_jita_prices([34, 35])

        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_type_id_in_response(self):
        """Type IDs not in Fuzzwork response are excluded."""
        fuzz_response = {
            "34": {
                "buy": {"max": 5.5},
                "sell": {"min": 6.0},
            }
            # 35 is missing
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            resp = httpx.Response(
                200,
                json=fuzz_response,
                request=httpx.Request("GET", "https://market.fuzzwork.co.uk/aggregates/"),
            )
            client.get.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await get_jita_prices([34, 35])

        assert 34 in result
        assert 35 not in result


# ---------------------------------------------------------------------------
# appraise (integration of parse + resolve + price)
# ---------------------------------------------------------------------------


class TestAppraise:
    """Tests for the top-level appraise() function."""

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_response(self):
        """Empty text returns empty AppraisalResponse."""
        result = await appraise("")
        assert result == AppraisalResponse()
        assert result.item_count == 0

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_empty(self):
        """Whitespace-only text returns empty response."""
        result = await appraise("   \n  \n  ")
        assert result == AppraisalResponse()

    @pytest.mark.asyncio
    async def test_full_appraisal_flow(self):
        """Full flow: parse -> resolve -> price -> response."""
        esi_response = {
            "inventory_types": [{"id": 34, "name": "Tritanium"}]
        }
        fuzz_response = {
            "34": {
                "buy": {"max": 5.0},
                "sell": {"min": 6.0},
            }
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()

            # First call = ESI resolve, second call = Fuzzwork prices
            esi_resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            fuzz_resp = httpx.Response(
                200,
                json=fuzz_response,
                request=httpx.Request("GET", "https://market.fuzzwork.co.uk/aggregates/"),
            )
            client.post.return_value = esi_resp
            client.get.return_value = fuzz_resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await appraise("Tritanium\t100")

        assert result.item_count == 1
        assert result.items[0].name == "Tritanium"
        assert result.items[0].quantity == 100
        assert result.items[0].buy_price == 5.0
        assert result.items[0].sell_price == 6.0
        assert result.items[0].buy_total == 500.0
        assert result.items[0].sell_total == 600.0
        assert result.total_buy == 500.0
        assert result.total_sell == 600.0

    @pytest.mark.asyncio
    async def test_unknown_items_tracked(self):
        """Unresolvable items appear in unknown_items."""
        esi_response = {"inventory_types": []}

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            client.post.return_value = resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await appraise("FakeItem\t10")

        assert "FakeItem" in result.unknown_items
        assert result.item_count == 0

    @pytest.mark.asyncio
    async def test_duplicate_items_aggregated(self):
        """Duplicate item names have quantities summed."""
        esi_response = {
            "inventory_types": [{"id": 34, "name": "Tritanium"}]
        }
        fuzz_response = {
            "34": {
                "buy": {"max": 5.0},
                "sell": {"min": 6.0},
            }
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            esi_resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            fuzz_resp = httpx.Response(
                200,
                json=fuzz_response,
                request=httpx.Request("GET", "https://market.fuzzwork.co.uk/aggregates/"),
            )
            client.post.return_value = esi_resp
            client.get.return_value = fuzz_resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await appraise("Tritanium\t100\nTritanium\t200")

        assert result.item_count == 1
        assert result.items[0].quantity == 300

    @pytest.mark.asyncio
    async def test_items_sorted_by_sell_total_descending(self):
        """Items are sorted by sell_total descending."""
        esi_response = {
            "inventory_types": [
                {"id": 34, "name": "Tritanium"},
                {"id": 35, "name": "Pyerite"},
            ]
        }
        fuzz_response = {
            "34": {"buy": {"max": 1.0}, "sell": {"min": 2.0}},
            "35": {"buy": {"max": 10.0}, "sell": {"min": 20.0}},
        }

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            esi_resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            fuzz_resp = httpx.Response(
                200,
                json=fuzz_response,
                request=httpx.Request("GET", "https://market.fuzzwork.co.uk/aggregates/"),
            )
            client.post.return_value = esi_resp
            client.get.return_value = fuzz_resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await appraise("Tritanium\t100\nPyerite\t100")

        # Pyerite (sell_total=2000) should be first
        assert result.items[0].name == "Pyerite"
        assert result.items[1].name == "Tritanium"

    @pytest.mark.asyncio
    async def test_zero_price_items(self):
        """Items not found in Fuzzwork get zero prices."""
        esi_response = {
            "inventory_types": [{"id": 34, "name": "Tritanium"}]
        }
        fuzz_response = {}  # no price data

        with patch("backend.app.services.appraisal.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            esi_resp = httpx.Response(
                200,
                json=esi_response,
                request=httpx.Request("POST", "https://esi.evetech.net/latest/universe/ids/"),
            )
            fuzz_resp = httpx.Response(
                200,
                json=fuzz_response,
                request=httpx.Request("GET", "https://market.fuzzwork.co.uk/aggregates/"),
            )
            client.post.return_value = esi_resp
            client.get.return_value = fuzz_resp
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            result = await appraise("Tritanium\t10")

        assert result.item_count == 1
        assert result.items[0].buy_price == 0.0
        assert result.items[0].sell_price == 0.0


class TestConstants:
    """Tests for module constants."""

    def test_price_cache_ttl(self):
        """Price cache TTL is 5 minutes."""
        assert PRICE_CACHE_TTL == 300

    def test_batch_size(self):
        """Batch size for Fuzzwork requests is 100."""
        assert BATCH_SIZE == 100
