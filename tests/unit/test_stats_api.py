"""Unit tests for stats API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.api.v1.stats import (
    get_bulk_stats,
    get_hot_systems,
    get_system_stats,
)
from backend.app.models.risk import ZKillStats


@pytest.fixture
def mock_universe():
    """Create a mock universe with test systems."""
    mock = MagicMock()
    mock.systems = {
        "Jita": MagicMock(id=30000142),
        "Amarr": MagicMock(id=30002187),
        "Tama": MagicMock(id=30002813),
        "Rancer": MagicMock(id=30002718),
    }
    return mock


@pytest.fixture
def mock_preloader():
    """Create a mock preloader with priority systems."""
    mock = MagicMock()
    mock._priority_systems = [30000142, 30002187, 30002813]
    return mock


class TestGetSystemStats:
    """Tests for get_system_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_system_stats_success(self, mock_universe):
        """Test getting stats for a valid system."""
        stats = ZKillStats(recent_kills=10, recent_pods=2)

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch(
                "backend.app.api.v1.stats.fetch_system_kills",
                new_callable=AsyncMock,
                return_value=stats,
            ),
        ):
            response = await get_system_stats("Jita", hours=24)

        assert response.system_id == 30000142
        assert response.system_name == "Jita"
        assert response.hours == 24
        assert response.stats.recent_kills == 10
        assert response.stats.recent_pods == 2

    @pytest.mark.asyncio
    async def test_get_system_stats_custom_hours(self, mock_universe):
        """Test getting stats with custom hours."""
        stats = ZKillStats(recent_kills=50, recent_pods=10)

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch(
                "backend.app.api.v1.stats.fetch_system_kills",
                new_callable=AsyncMock,
                return_value=stats,
            ) as mock_fetch,
        ):
            response = await get_system_stats("Tama", hours=48)

        mock_fetch.assert_called_once_with(30002813, 48)
        assert response.hours == 48
        assert response.stats.recent_kills == 50

    @pytest.mark.asyncio
    async def test_get_system_stats_unknown_system(self, mock_universe):
        """Test getting stats for unknown system."""
        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            pytest.raises(Exception) as exc_info,
        ):
            await get_system_stats("FakeSystem")

        assert "Unknown system: FakeSystem" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_system_stats_no_activity(self, mock_universe):
        """Test getting stats for system with no activity."""
        stats = ZKillStats(recent_kills=0, recent_pods=0)

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch(
                "backend.app.api.v1.stats.fetch_system_kills",
                new_callable=AsyncMock,
                return_value=stats,
            ),
        ):
            response = await get_system_stats("Amarr", hours=24)

        assert response.stats.recent_kills == 0
        assert response.stats.recent_pods == 0


class TestGetBulkStats:
    """Tests for get_bulk_stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_bulk_stats_success(self, mock_universe):
        """Test getting stats for multiple systems."""
        from backend.app.api.v1.stats import BulkStatsRequest

        stats_by_id = {
            30000142: ZKillStats(recent_kills=10, recent_pods=2),
            30002187: ZKillStats(recent_kills=5, recent_pods=1),
        }

        request = BulkStatsRequest(systems=["Jita", "Amarr"], hours=24)

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch(
                "backend.app.api.v1.stats.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value=stats_by_id,
            ),
        ):
            response = await get_bulk_stats(request)

        assert response.total_systems == 2
        assert response.hours == 24
        assert "Jita" in response.stats
        assert "Amarr" in response.stats
        assert response.stats["Jita"].recent_kills == 10

    @pytest.mark.asyncio
    async def test_get_bulk_stats_unknown_system(self, mock_universe):
        """Test bulk stats with unknown system."""
        from backend.app.api.v1.stats import BulkStatsRequest

        request = BulkStatsRequest(systems=["Jita", "FakeSystem"], hours=24)

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            pytest.raises(Exception) as exc_info,
        ):
            await get_bulk_stats(request)

        assert "Unknown system: FakeSystem" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_bulk_stats_single_system(self, mock_universe):
        """Test bulk stats with single system."""
        from backend.app.api.v1.stats import BulkStatsRequest

        stats_by_id = {30002813: ZKillStats(recent_kills=100, recent_pods=50)}

        request = BulkStatsRequest(systems=["Tama"], hours=12)

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch(
                "backend.app.api.v1.stats.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value=stats_by_id,
            ),
        ):
            response = await get_bulk_stats(request)

        assert response.total_systems == 1
        assert response.stats["Tama"].recent_kills == 100


class TestGetHotSystems:
    """Tests for get_hot_systems endpoint."""

    @pytest.mark.asyncio
    async def test_get_hot_systems_success(self, mock_universe, mock_preloader):
        """Test getting hot systems."""
        stats_by_id = {
            30000142: ZKillStats(recent_kills=10, recent_pods=2),
            30002187: ZKillStats(recent_kills=5, recent_pods=1),
            30002813: ZKillStats(recent_kills=100, recent_pods=50),
        }

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.stats.get_zkill_preloader", return_value=mock_preloader),
            patch(
                "backend.app.api.v1.stats.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value=stats_by_id,
            ),
        ):
            response = await get_hot_systems(hours=24)

        assert response.hours == 24
        assert len(response.systems) == 3
        # Should be sorted by total activity (descending)
        assert response.systems[0].system_name == "Tama"
        assert response.systems[0].total_activity == 150

    @pytest.mark.asyncio
    async def test_get_hot_systems_custom_hours(self, mock_universe, mock_preloader):
        """Test hot systems with custom hours."""
        stats_by_id = {
            30000142: ZKillStats(recent_kills=5, recent_pods=0),
            30002187: ZKillStats(recent_kills=3, recent_pods=0),
            30002813: ZKillStats(recent_kills=20, recent_pods=5),
        }

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.stats.get_zkill_preloader", return_value=mock_preloader),
            patch(
                "backend.app.api.v1.stats.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value=stats_by_id,
            ) as mock_fetch,
        ):
            response = await get_hot_systems(hours=48)

        mock_fetch.assert_called_once_with([30000142, 30002187, 30002813], 48)
        assert response.hours == 48

    @pytest.mark.asyncio
    async def test_get_hot_systems_empty_stats(self, mock_universe, mock_preloader):
        """Test hot systems when no kills."""
        stats_by_id = {
            30000142: ZKillStats(recent_kills=0, recent_pods=0),
            30002187: ZKillStats(recent_kills=0, recent_pods=0),
            30002813: ZKillStats(recent_kills=0, recent_pods=0),
        }

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.stats.get_zkill_preloader", return_value=mock_preloader),
            patch(
                "backend.app.api.v1.stats.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value=stats_by_id,
            ),
        ):
            response = await get_hot_systems(hours=24)

        assert len(response.systems) == 3
        assert all(s.total_activity == 0 for s in response.systems)

    @pytest.mark.asyncio
    async def test_get_hot_systems_sorted_by_activity(self, mock_universe, mock_preloader):
        """Test that hot systems are sorted by activity."""
        stats_by_id = {
            30000142: ZKillStats(recent_kills=50, recent_pods=10),  # 60 total
            30002187: ZKillStats(recent_kills=100, recent_pods=20),  # 120 total
            30002813: ZKillStats(recent_kills=30, recent_pods=5),  # 35 total
        }

        with (
            patch("backend.app.api.v1.stats.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.stats.get_zkill_preloader", return_value=mock_preloader),
            patch(
                "backend.app.api.v1.stats.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value=stats_by_id,
            ),
        ):
            response = await get_hot_systems(hours=24)

        activities = [s.total_activity for s in response.systems]
        assert activities == sorted(activities, reverse=True)
        assert response.systems[0].total_activity == 120
        assert response.systems[1].total_activity == 60
        assert response.systems[2].total_activity == 35


class TestStatsModels:
    """Tests for stats Pydantic models."""

    def test_bulk_stats_request_validation(self):
        """Test bulk stats request validation."""
        from backend.app.api.v1.stats import BulkStatsRequest

        # Valid request
        request = BulkStatsRequest(systems=["Jita", "Amarr"], hours=24)
        assert len(request.systems) == 2
        assert request.hours == 24

    def test_bulk_stats_request_default_hours(self):
        """Test bulk stats request default hours."""
        from backend.app.api.v1.stats import BulkStatsRequest

        request = BulkStatsRequest(systems=["Jita"])
        assert request.hours == 24

    def test_hot_system_stats_total_activity(self):
        """Test HotSystemStats total_activity calculation."""
        from backend.app.api.v1.stats import HotSystemStats

        stats = HotSystemStats(
            system_id=30000142,
            system_name="Jita",
            recent_kills=10,
            recent_pods=5,
            total_activity=15,
        )
        assert stats.total_activity == stats.recent_kills + stats.recent_pods
