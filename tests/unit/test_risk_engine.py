"""Unit tests for risk engine."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.models.risk import ZKillStats
from backend.app.services.risk_engine import (
    compute_risk,
    compute_risk_async,
    compute_route_risks_async,
    risk_to_color,
)


class TestComputeRisk:
    """Tests for compute_risk function."""

    def test_compute_risk_highsec_system(self):
        """Test risk calculation for a high-sec system."""
        report = compute_risk("Jita")

        assert report.system_name == "Jita"
        assert report.system_id == 30000142
        assert report.category == "highsec"
        assert report.security == 0.95  # Real Jita security
        # High-sec with no kills should have low risk
        assert 0 <= report.score <= 100

    def test_compute_risk_lowsec_system(self):
        """Test risk calculation for a low-sec system."""
        report = compute_risk("Tama")  # Use Tama instead of Niarja (real lowsec)

        assert report.system_name == "Tama"
        assert report.category == "lowsec"
        assert 0.0 < report.security < 0.5  # Lowsec range
        # Low-sec should have higher base risk than high-sec
        assert report.score > 0

    def test_compute_risk_with_kill_stats(self):
        """Test risk calculation with kill statistics."""
        stats_high = ZKillStats(recent_kills=500, recent_pods=100)
        stats_low = ZKillStats(recent_kills=0, recent_pods=0)
        report_with_kills = compute_risk("Jita", stats=stats_high)
        report_no_kills = compute_risk("Jita", stats=stats_low)

        # Risk should be higher with kills
        assert report_with_kills.score > report_no_kills.score

    def test_compute_risk_unknown_system(self):
        """Test risk calculation for unknown system raises error."""
        with pytest.raises(ValueError, match="Unknown system"):
            compute_risk("NonExistentSystem")

    def test_compute_risk_breakdown(self):
        """Test that risk breakdown is properly populated."""
        stats = ZKillStats(recent_kills=10, recent_pods=5)
        report = compute_risk("Jita", stats=stats)

        assert report.breakdown.security_component >= 0
        assert report.breakdown.kills_component >= 0
        assert report.breakdown.pods_component >= 0

    def test_compute_risk_clamped(self):
        """Test that risk score is clamped between 0 and 100."""
        # Even with extreme kill stats, should not exceed 100
        extreme_stats = ZKillStats(recent_kills=10000, recent_pods=5000)
        report = compute_risk("Tama", stats=extreme_stats)

        assert 0 <= report.score <= 100


class TestRiskToColor:
    """Tests for risk_to_color function."""

    def test_low_risk_color(self):
        """Test color for low risk score."""
        color = risk_to_color(5)
        assert color == "#3AF57A"  # Green

    def test_medium_risk_color(self):
        """Test color for medium risk score."""
        color = risk_to_color(30)
        assert color == "#F5D33A"  # Yellow

    def test_high_risk_color(self):
        """Test color for high risk score."""
        color = risk_to_color(80)
        assert color == "#F53A3A"  # Red

    def test_boundary_risk_color(self):
        """Test color at exact boundary."""
        color = risk_to_color(10)
        assert color == "#3AF57A"  # Should be in 0-10 band

    def test_out_of_range_color(self):
        """Test color for out-of-range score returns default."""
        color = risk_to_color(150)
        assert color == "#FFFFFF"  # Default white


class TestComputeRiskAsync:
    """Tests for async risk computation."""

    @pytest.mark.asyncio
    async def test_compute_risk_async_no_fetch(self):
        """Test async risk computation without fetching live data."""
        report = await compute_risk_async("Jita", fetch_live=False)

        assert report.system_name == "Jita"
        assert report.category == "highsec"
        assert 0 <= report.score <= 100

    @pytest.mark.asyncio
    async def test_compute_risk_async_unknown_system(self):
        """Test async risk computation for unknown system."""
        with pytest.raises(ValueError, match="Unknown system"):
            await compute_risk_async("FakeSystem", fetch_live=False)

    @pytest.mark.asyncio
    async def test_compute_risk_async_with_mock_fetch(self):
        """Test async risk computation with mocked live data."""
        mock_stats = ZKillStats(recent_kills=100, recent_pods=50)

        with patch(
            "backend.app.services.zkill_stats.fetch_system_kills",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            report = await compute_risk_async("Jita", fetch_live=True)

            assert report.system_name == "Jita"
            # With kills, zkill_stats should be populated
            assert report.zkill_stats is not None
            assert report.zkill_stats.recent_kills == 100


class TestComputeRouteRisksAsync:
    """Tests for bulk route risk computation."""

    @pytest.mark.asyncio
    async def test_compute_route_risks_no_fetch(self):
        """Test bulk risk computation without fetching live data."""
        systems = ["Jita", "Perimeter", "Urlen"]

        results = await compute_route_risks_async(systems, fetch_live=False)

        assert len(results) == 3
        assert "Jita" in results
        assert "Perimeter" in results
        assert "Urlen" in results
        assert all(0 <= r.score <= 100 for r in results.values())

    @pytest.mark.asyncio
    async def test_compute_route_risks_with_unknown_system(self):
        """Test bulk computation ignores unknown systems."""
        systems = ["Jita", "FakeSystem", "Perimeter"]

        results = await compute_route_risks_async(systems, fetch_live=False)

        # Only known systems should be in results
        assert "Jita" in results
        assert "Perimeter" in results
        assert "FakeSystem" not in results

    @pytest.mark.asyncio
    async def test_compute_route_risks_empty_list(self):
        """Test bulk computation with empty list."""
        results = await compute_route_risks_async([], fetch_live=False)

        assert results == {}

    @pytest.mark.asyncio
    async def test_compute_route_risks_with_mock_fetch(self):
        """Test bulk computation with mocked live data."""
        mock_stats = {
            30000142: ZKillStats(recent_kills=100, recent_pods=10),  # Jita
            30000144: ZKillStats(recent_kills=5, recent_pods=1),  # Perimeter
        }

        with patch(
            "backend.app.services.zkill_stats.fetch_bulk_system_stats",
            new_callable=AsyncMock,
            return_value=mock_stats,
        ):
            results = await compute_route_risks_async(
                ["Jita", "Perimeter"], fetch_live=True
            )

            assert results["Jita"].zkill_stats is not None
            assert results["Jita"].zkill_stats.recent_kills == 100
