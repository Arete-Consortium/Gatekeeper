"""Unit tests for pirate insurgency endpoint."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.api.routes_map import PIRATE_FACTIONS, get_pirate_insurgency
from backend.app.services.fw_cache import _cache


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the module-level FW cache before each test."""
    _cache.occupier_by_system = {}
    _cache.pirate_occupied = set()
    _cache.last_fetched = 0.0
    yield
    _cache.occupier_by_system = {}
    _cache.pirate_occupied = set()
    _cache.last_fetched = 0.0


class TestPirateFactions:
    """Tests for the PIRATE_FACTIONS mapping."""

    def test_guristas_present(self):
        """500010 maps to Guristas Pirates."""
        assert PIRATE_FACTIONS[500010] == "Guristas Pirates"

    def test_angel_cartel_present(self):
        """500011 maps to Angel Cartel."""
        assert PIRATE_FACTIONS[500011] == "Angel Cartel"

    def test_exactly_two_factions(self):
        """Only two pirate factions defined."""
        assert len(PIRATE_FACTIONS) == 2


class TestPirateInsurgencyEndpoint:
    """Tests for GET /map/pirate-insurgency."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pirates(self):
        """Returns empty systems list when no pirate occupation."""
        _cache.occupier_by_system = {30001: 500001}  # Caldari, not pirate
        _cache.last_fetched = time.monotonic()

        with patch("backend.app.services.fw_cache.ensure_fw_cache", new_callable=AsyncMock):
            result = await get_pirate_insurgency()

        assert result["systems"] == []

    @pytest.mark.asyncio
    async def test_returns_pirate_occupied_systems(self):
        """Returns systems occupied by pirate factions with names."""
        _cache.occupier_by_system = {
            30002813: 500010,  # Guristas — Akidagi (real system)
            30003456: 500011,  # Angel Cartel
            30001000: 500001,  # Caldari — should be excluded
        }
        _cache.last_fetched = time.monotonic()

        with patch("backend.app.services.fw_cache.ensure_fw_cache", new_callable=AsyncMock):
            result = await get_pirate_insurgency()

        systems = result["systems"]
        assert len(systems) == 2

        faction_ids = {s["occupier_faction_id"] for s in systems}
        assert faction_ids == {500010, 500011}

        for system in systems:
            assert "system_id" in system
            assert "system_name" in system
            assert "occupier_faction_id" in system
            assert "faction_name" in system
            assert system["faction_name"] in ("Guristas Pirates", "Angel Cartel")

    @pytest.mark.asyncio
    async def test_returns_empty_when_cache_empty(self):
        """Returns empty when FW cache has no data."""
        _cache.last_fetched = time.monotonic()

        with patch("backend.app.services.fw_cache.ensure_fw_cache", new_callable=AsyncMock):
            result = await get_pirate_insurgency()

        assert result["systems"] == []

    @pytest.mark.asyncio
    async def test_calls_ensure_fw_cache(self):
        """Endpoint calls ensure_fw_cache to refresh stale data."""
        with patch(
            "backend.app.services.fw_cache.ensure_fw_cache", new_callable=AsyncMock
        ) as mock_ensure:
            await get_pirate_insurgency()
            mock_ensure.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_system_id_gets_fallback_name(self):
        """System IDs not in universe data get a fallback name."""
        _cache.occupier_by_system = {
            99999999: 500010,  # Non-existent system ID
        }
        _cache.last_fetched = time.monotonic()

        with patch("backend.app.services.fw_cache.ensure_fw_cache", new_callable=AsyncMock):
            result = await get_pirate_insurgency()

        systems = result["systems"]
        assert len(systems) == 1
        assert systems[0]["system_name"] == "Unknown-99999999"
        assert systems[0]["faction_name"] == "Guristas Pirates"
