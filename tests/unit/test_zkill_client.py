"""Unit tests for zKillboard client stub."""

import pytest

from backend.app.models.risk import ZKillStats
from backend.app.services.zkill_client import fetch_system_stats


class TestZKillClient:
    """Tests for zKillboard client."""

    @pytest.mark.asyncio
    async def test_fetch_system_stats_returns_zkill_stats(self):
        """Test that fetch_system_stats returns a ZKillStats object."""
        result = await fetch_system_stats(30000142)  # Jita
        assert isinstance(result, ZKillStats)

    @pytest.mark.asyncio
    async def test_fetch_system_stats_returns_zero_activity(self):
        """Test that the stub returns zero activity."""
        result = await fetch_system_stats(30000142)
        assert result.recent_kills == 0
        assert result.recent_pods == 0

    @pytest.mark.asyncio
    async def test_fetch_system_stats_works_for_any_system(self):
        """Test that any system ID works (offline mode)."""
        # Test with various system IDs
        for system_id in [30000142, 30002187, 12345, 0]:
            result = await fetch_system_stats(system_id)
            assert isinstance(result, ZKillStats)
