"""Unit tests for FW cache service."""

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.app.services.fw_cache import (
    FW_CACHE_TTL,
    PIRATE_FACTION_IDS,
    FWCacheEntry,
    _cache,
    _is_stale,
    ensure_fw_cache,
    get_pirate_occupied_systems,
    is_pirate_occupied_sync,
    refresh_fw_cache,
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the module-level cache before each test."""
    _cache.occupier_by_system = {}
    _cache.pirate_occupied = set()
    _cache.last_fetched = 0.0
    yield
    _cache.occupier_by_system = {}
    _cache.pirate_occupied = set()
    _cache.last_fetched = 0.0


def _fw_entry(system_id: int, occupier_faction_id: int) -> dict:
    return {"solar_system_id": system_id, "occupier_faction_id": occupier_faction_id}


def _mock_esi_response(payload, status_code=200):
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("GET", "https://esi.evetech.net/latest/fw/systems/"),
    )


class TestFWCacheEntry:
    """Tests for FWCacheEntry dataclass."""

    def test_default_empty(self):
        """New cache entry is empty."""
        entry = FWCacheEntry()
        assert entry.occupier_by_system == {}
        assert entry.pirate_occupied == set()
        assert entry.last_fetched == 0.0

    def test_custom_values(self):
        """Can create cache entry with custom values."""
        entry = FWCacheEntry(
            occupier_by_system={30001: 500010},
            pirate_occupied={30001},
            last_fetched=100.0,
        )
        assert entry.occupier_by_system == {30001: 500010}
        assert entry.pirate_occupied == {30001}
        assert entry.last_fetched == 100.0


class TestIsStale:
    """Tests for _is_stale() function."""

    def test_stale_when_never_fetched(self):
        """Cache is stale when never fetched (last_fetched=0)."""
        assert _is_stale() is True

    def test_not_stale_when_recently_fetched(self):
        """Cache is not stale when recently fetched."""
        _cache.last_fetched = time.monotonic()
        assert _is_stale() is False

    def test_stale_after_ttl_expires(self):
        """Cache is stale after TTL expires."""
        _cache.last_fetched = time.monotonic() - FW_CACHE_TTL - 1
        assert _is_stale() is True

    def test_not_stale_just_before_ttl(self):
        """Cache is not stale just before TTL expires."""
        _cache.last_fetched = time.monotonic() - FW_CACHE_TTL + 10
        assert _is_stale() is False


class TestIsPirateOccupiedSync:
    """Tests for is_pirate_occupied_sync()."""

    def test_returns_false_empty_cache(self):
        """Returns False when cache is empty."""
        assert is_pirate_occupied_sync(30001) is False

    def test_returns_true_for_pirate_system(self):
        """Returns True for a pirate-occupied system."""
        _cache.pirate_occupied = {30001, 30002}
        assert is_pirate_occupied_sync(30001) is True

    def test_returns_false_for_non_pirate_system(self):
        """Returns False for a system not pirate-occupied."""
        _cache.pirate_occupied = {30001}
        assert is_pirate_occupied_sync(30002) is False

    def test_returns_false_for_fw_system_non_pirate(self):
        """Returns False for FW system occupied by non-pirate faction."""
        _cache.occupier_by_system = {30001: 500001}  # Caldari State, not pirate
        _cache.pirate_occupied = set()
        assert is_pirate_occupied_sync(30001) is False


class TestGetPirateOccupiedSystems:
    """Tests for get_pirate_occupied_systems()."""

    def test_returns_empty_set_when_empty(self):
        """Returns empty set when no pirate-occupied systems."""
        result = get_pirate_occupied_systems()
        assert result == set()

    def test_returns_copy_of_pirate_set(self):
        """Returns a copy, not the original set."""
        _cache.pirate_occupied = {30001, 30002}
        result = get_pirate_occupied_systems()
        assert result == {30001, 30002}
        # Verify it's a copy
        result.add(99999)
        assert 99999 not in _cache.pirate_occupied

    def test_returns_all_pirate_systems(self):
        """Returns all pirate-occupied systems."""
        _cache.pirate_occupied = {30001, 30002, 30003}
        result = get_pirate_occupied_systems()
        assert len(result) == 3


class TestRefreshFwCache:
    """Tests for refresh_fw_cache()."""

    @pytest.mark.asyncio
    async def test_successful_refresh(self):
        """Successful ESI fetch populates cache."""
        payload = [
            _fw_entry(30001, 500010),  # Guristas (pirate)
            _fw_entry(30002, 500001),  # Caldari (not pirate)
            _fw_entry(30003, 500011),  # Angel Cartel (pirate)
        ]

        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = _mock_esi_response(payload)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        assert _cache.occupier_by_system[30001] == 500010
        assert _cache.occupier_by_system[30002] == 500001
        assert _cache.occupier_by_system[30003] == 500011
        assert _cache.pirate_occupied == {30001, 30003}
        assert _cache.last_fetched > 0

    @pytest.mark.asyncio
    async def test_refresh_with_no_pirates(self):
        """Refresh with no pirate factions results in empty pirate set."""
        payload = [
            _fw_entry(30001, 500001),  # Caldari
            _fw_entry(30002, 500002),  # Minmatar
        ]

        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = _mock_esi_response(payload)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        assert _cache.pirate_occupied == set()
        assert len(_cache.occupier_by_system) == 2

    @pytest.mark.asyncio
    async def test_refresh_with_empty_response(self):
        """Empty ESI response clears cache data."""
        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = _mock_esi_response([])
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        assert _cache.occupier_by_system == {}
        assert _cache.pirate_occupied == set()
        assert _cache.last_fetched > 0

    @pytest.mark.asyncio
    async def test_refresh_http_error_preserves_cache(self):
        """HTTP error during refresh preserves existing cache data."""
        _cache.pirate_occupied = {30001}
        _cache.occupier_by_system = {30001: 500010}
        _cache.last_fetched = 100.0

        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.side_effect = httpx.HTTPError("ESI down")
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        # Cache should be unchanged
        assert _cache.pirate_occupied == {30001}
        assert _cache.last_fetched == 100.0

    @pytest.mark.asyncio
    async def test_refresh_timeout_preserves_cache(self):
        """Timeout during refresh preserves existing cache data."""
        _cache.pirate_occupied = {30002}
        _cache.last_fetched = 50.0

        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.side_effect = httpx.TimeoutException("timeout")
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        assert _cache.pirate_occupied == {30002}
        assert _cache.last_fetched == 50.0

    @pytest.mark.asyncio
    async def test_refresh_skips_entries_without_system_id(self):
        """Entries without solar_system_id are skipped."""
        payload = [
            {"occupier_faction_id": 500010},  # missing solar_system_id
            _fw_entry(30002, 500011),
        ]

        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = _mock_esi_response(payload)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        assert len(_cache.occupier_by_system) == 1
        assert 30002 in _cache.occupier_by_system

    @pytest.mark.asyncio
    async def test_refresh_skips_entries_without_occupier(self):
        """Entries without occupier_faction_id are skipped."""
        payload = [
            {"solar_system_id": 30001},  # missing occupier_faction_id
            _fw_entry(30002, 500010),
        ]

        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = _mock_esi_response(payload)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        assert len(_cache.occupier_by_system) == 1
        assert 30002 in _cache.occupier_by_system

    @pytest.mark.asyncio
    async def test_refresh_updates_last_fetched_timestamp(self):
        """Successful refresh updates the last_fetched timestamp."""
        before = time.monotonic()

        with patch("backend.app.services.fw_cache.httpx.AsyncClient") as mock_cls:
            client = AsyncMock()
            client.get.return_value = _mock_esi_response([])
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = client

            await refresh_fw_cache()

        assert _cache.last_fetched >= before


class TestEnsureFwCache:
    """Tests for ensure_fw_cache()."""

    @pytest.mark.asyncio
    async def test_refreshes_when_stale(self):
        """Calls refresh when cache is stale."""
        with patch(
            "backend.app.services.fw_cache.refresh_fw_cache", new_callable=AsyncMock
        ) as mock_refresh:
            await ensure_fw_cache()
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_refresh_when_fresh(self):
        """Does not refresh when cache is fresh."""
        _cache.last_fetched = time.monotonic()

        with patch(
            "backend.app.services.fw_cache.refresh_fw_cache", new_callable=AsyncMock
        ) as mock_refresh:
            await ensure_fw_cache()
            mock_refresh.assert_not_called()


class TestPirateFactionIds:
    """Tests for PIRATE_FACTION_IDS constant."""

    def test_contains_guristas(self):
        """500010 (Guristas Pirates) is in pirate faction IDs."""
        assert 500010 in PIRATE_FACTION_IDS

    def test_contains_angel_cartel(self):
        """500011 (Angel Cartel) is in pirate faction IDs."""
        assert 500011 in PIRATE_FACTION_IDS

    def test_count(self):
        """Exactly two pirate factions defined."""
        assert len(PIRATE_FACTION_IDS) == 2

    def test_regular_factions_excluded(self):
        """Regular empire factions are not in pirate set."""
        assert 500001 not in PIRATE_FACTION_IDS  # Caldari State
        assert 500002 not in PIRATE_FACTION_IDS  # Minmatar Republic
        assert 500003 not in PIRATE_FACTION_IDS  # Amarr Empire
        assert 500004 not in PIRATE_FACTION_IDS  # Gallente Federation

    def test_is_frozenset(self):
        """PIRATE_FACTION_IDS is immutable (frozenset)."""
        assert isinstance(PIRATE_FACTION_IDS, frozenset)


class TestFWCacheTTL:
    """Tests for cache TTL constant."""

    def test_ttl_is_300_seconds(self):
        """FW cache TTL is 5 minutes (300 seconds)."""
        assert FW_CACHE_TTL == 300
