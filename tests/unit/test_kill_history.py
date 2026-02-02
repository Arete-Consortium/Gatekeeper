"""Tests for the kill history service."""

from datetime import UTC, datetime, timedelta

import pytest


class TestKillHistory:
    """Tests for KillHistory class."""

    @pytest.fixture
    def history(self):
        """Create a fresh KillHistory instance for testing."""
        from backend.app.services.kill_history import KillHistory

        return KillHistory(max_age_hours=24, max_entries=100)

    @pytest.fixture
    def sample_kill(self):
        """Create a sample kill data dict."""
        return {
            "kill_id": 12345,
            "solar_system_id": 30000142,  # Jita
            "solar_system_name": "Jita",
            "region_id": 10000002,  # The Forge
            "kill_time": datetime.now(UTC).isoformat(),
            "ship_type_id": 587,  # Rifter
            "is_pod": False,
            "total_value": 10000000,  # 10M ISK
            "received_at": datetime.now(UTC).isoformat(),
        }

    def test_add_kill(self, history, sample_kill):
        """Test adding a kill to history."""
        assert history.count == 0

        result = history.add_kill(sample_kill)

        assert result is True
        assert history.count == 1

    def test_add_duplicate_kill(self, history, sample_kill):
        """Test that duplicate kills are rejected."""
        history.add_kill(sample_kill)

        result = history.add_kill(sample_kill)

        assert result is False
        assert history.count == 1

    def test_add_kill_without_id(self, history):
        """Test that kills without kill_id are rejected."""
        bad_kill = {"solar_system_id": 30000142}

        result = history.add_kill(bad_kill)

        assert result is False
        assert history.count == 0

    def test_max_entries_limit(self):
        """Test that max_entries limit is enforced."""
        from backend.app.services.kill_history import KillHistory

        history = KillHistory(max_age_hours=24, max_entries=5)

        # Add 10 kills
        for i in range(10):
            history.add_kill({"kill_id": i, "solar_system_id": 30000142})

        # Should only have 5
        assert history.count == 5

        # Oldest kills should be evicted (0-4), newest should remain (5-9)
        kills = history.get_recent()
        kill_ids = [k["kill_id"] for k in kills]
        assert 0 not in kill_ids
        assert 9 in kill_ids

    def test_get_recent(self, history):
        """Test getting recent kills."""
        for i in range(5):
            history.add_kill(
                {
                    "kill_id": i,
                    "solar_system_id": 30000142,
                    "received_at": datetime.now(UTC).isoformat(),
                }
            )

        kills = history.get_recent(limit=3)

        assert len(kills) == 3
        # Should be newest first
        assert kills[0]["kill_id"] == 4
        assert kills[2]["kill_id"] == 2

    def test_get_recent_with_system_filter(self, history):
        """Test filtering by system ID."""
        # Add kills from different systems
        history.add_kill({"kill_id": 1, "solar_system_id": 30000142})  # Jita
        history.add_kill({"kill_id": 2, "solar_system_id": 30002187})  # Amarr
        history.add_kill({"kill_id": 3, "solar_system_id": 30000142})  # Jita

        jita_kills = history.get_recent(system_id=30000142)

        assert len(jita_kills) == 2
        assert all(k["solar_system_id"] == 30000142 for k in jita_kills)

    def test_get_recent_with_region_filter(self, history):
        """Test filtering by region ID."""
        history.add_kill({"kill_id": 1, "solar_system_id": 30000142, "region_id": 10000002})
        history.add_kill({"kill_id": 2, "solar_system_id": 30002187, "region_id": 10000043})
        history.add_kill({"kill_id": 3, "solar_system_id": 30000144, "region_id": 10000002})

        forge_kills = history.get_recent(region_id=10000002)

        assert len(forge_kills) == 2
        assert all(k["region_id"] == 10000002 for k in forge_kills)

    def test_get_recent_with_value_filter(self, history):
        """Test filtering by minimum value."""
        history.add_kill({"kill_id": 1, "solar_system_id": 30000142, "total_value": 1000000})
        history.add_kill({"kill_id": 2, "solar_system_id": 30000142, "total_value": 100000000})
        history.add_kill({"kill_id": 3, "solar_system_id": 30000142, "total_value": 5000000})

        expensive_kills = history.get_recent(min_value=10000000)

        assert len(expensive_kills) == 1
        assert expensive_kills[0]["kill_id"] == 2

    def test_get_system_kills(self, history):
        """Test getting kills for a specific system."""
        history.add_kill({"kill_id": 1, "solar_system_id": 30000142})
        history.add_kill({"kill_id": 2, "solar_system_id": 30002187})

        kills = history.get_system_kills(30000142)

        assert len(kills) == 1
        assert kills[0]["kill_id"] == 1

    def test_get_region_kills(self, history):
        """Test getting kills for a specific region."""
        history.add_kill({"kill_id": 1, "solar_system_id": 30000142, "region_id": 10000002})
        history.add_kill({"kill_id": 2, "solar_system_id": 30002187, "region_id": 10000043})

        kills = history.get_region_kills(10000002)

        assert len(kills) == 1
        assert kills[0]["kill_id"] == 1

    def test_cleanup_expired(self, history):
        """Test cleanup of expired kills."""
        # Add an old kill
        old_time = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
        history.add_kill({"kill_id": 1, "solar_system_id": 30000142, "received_at": old_time})

        # Add a recent kill
        recent_time = datetime.now(UTC).isoformat()
        history.add_kill({"kill_id": 2, "solar_system_id": 30000142, "received_at": recent_time})

        assert history.count == 2

        removed = history.cleanup_expired()

        assert removed == 1
        assert history.count == 1
        # Recent kill should remain
        kills = history.get_recent()
        assert kills[0]["kill_id"] == 2

    def test_clear(self, history):
        """Test clearing all kills."""
        for i in range(5):
            history.add_kill({"kill_id": i, "solar_system_id": 30000142})

        assert history.count == 5

        cleared = history.clear()

        assert cleared == 5
        assert history.count == 0

    def test_get_stats(self, history, sample_kill):
        """Test getting statistics."""
        history.add_kill(sample_kill)

        stats = history.get_stats()

        assert stats["total_stored"] == 1
        assert stats["max_entries"] == 100
        assert stats["max_age_hours"] == 24
        assert stats["systems_tracked"] == 1
        assert stats["regions_tracked"] == 1
        assert stats["total_received"] == 1
        assert stats["total_expired"] == 0
        assert stats["total_evicted"] == 0

    def test_eviction_stats(self):
        """Test that eviction stats are tracked."""
        from backend.app.services.kill_history import KillHistory

        history = KillHistory(max_age_hours=24, max_entries=3)

        for i in range(5):
            history.add_kill({"kill_id": i, "solar_system_id": 30000142})

        stats = history.get_stats()

        assert stats["total_received"] == 5
        assert stats["total_evicted"] == 2  # 5 - 3 = 2 evicted

    def test_auto_adds_received_at(self, history):
        """Test that received_at is added if missing."""
        kill = {"kill_id": 1, "solar_system_id": 30000142}

        history.add_kill(kill)

        stored = history.get_recent()[0]
        assert "received_at" in stored


class TestKillHistoryGlobal:
    """Tests for global kill history instance."""

    def test_get_kill_history_singleton(self):
        """Test that get_kill_history returns same instance."""
        from backend.app.services import kill_history

        # Reset global
        kill_history._kill_history = None

        h1 = kill_history.get_kill_history()
        h2 = kill_history.get_kill_history()

        assert h1 is h2

        # Clean up
        kill_history._kill_history = None
