"""Unit tests for hotzone detection service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.hotzone import (
    HotzoneSystem,
    _count_kills_in_window,
    _sec_category,
)


class TestSecCategory:
    """Tests for security category classification."""

    def test_highsec(self):
        assert _sec_category(0.5) == "high_sec"
        assert _sec_category(1.0) == "high_sec"
        assert _sec_category(0.95) == "high_sec"

    def test_lowsec(self):
        assert _sec_category(0.4) == "low_sec"
        assert _sec_category(0.1) == "low_sec"

    def test_nullsec(self):
        assert _sec_category(0.0) == "null_sec"
        assert _sec_category(-0.5) == "null_sec"
        assert _sec_category(-1.0) == "null_sec"


class TestCountKillsInWindow:
    """Tests for kill counting within time windows."""

    def test_empty_kills(self):
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        assert _count_kills_in_window([], start, now) == (0, 0)

    def test_counts_ship_kills(self):
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        kills = [
            {"received_at": (now - timedelta(minutes=30)).isoformat(), "is_pod": False},
            {"received_at": (now - timedelta(minutes=15)).isoformat(), "is_pod": False},
        ]
        ship, pod = _count_kills_in_window(kills, start, now)
        assert ship == 2
        assert pod == 0

    def test_counts_pod_kills(self):
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        kills = [
            {"received_at": (now - timedelta(minutes=30)).isoformat(), "is_pod": True},
        ]
        ship, pod = _count_kills_in_window(kills, start, now)
        assert ship == 0
        assert pod == 1

    def test_excludes_kills_outside_window(self):
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        kills = [
            {"received_at": (now - timedelta(hours=2)).isoformat(), "is_pod": False},  # Before window
            {"received_at": (now - timedelta(minutes=30)).isoformat(), "is_pod": False},  # In window
        ]
        ship, pod = _count_kills_in_window(kills, start, now)
        assert ship == 1
        assert pod == 0

    def test_handles_invalid_timestamps(self):
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        kills = [
            {"received_at": "not-a-date", "is_pod": False},
            {"received_at": None, "is_pod": False},
            {"is_pod": False},  # No timestamp
        ]
        ship, pod = _count_kills_in_window(kills, start, now)
        assert ship == 0
        assert pod == 0

    def test_mixed_kills_and_pods(self):
        now = datetime.now(UTC)
        start = now - timedelta(hours=1)
        kills = [
            {"received_at": (now - timedelta(minutes=30)).isoformat(), "is_pod": False},
            {"received_at": (now - timedelta(minutes=20)).isoformat(), "is_pod": True},
            {"received_at": (now - timedelta(minutes=10)).isoformat(), "is_pod": False},
            {"received_at": (now - timedelta(minutes=5)).isoformat(), "is_pod": True},
        ]
        ship, pod = _count_kills_in_window(kills, start, now)
        assert ship == 2
        assert pod == 2


class TestHotzoneSystemModel:
    """Tests for HotzoneSystem pydantic model."""

    def test_default_values(self):
        hz = HotzoneSystem(system_id=1, system_name="Test", security=0.5, category="high_sec")
        assert hz.kills_current == 0
        assert hz.pods_current == 0
        assert hz.trend == 0.0
        assert hz.predicted_1hr == 0
        assert hz.predicted_2hr == 0
        assert hz.gate_camp_likely is False

    def test_full_values(self):
        hz = HotzoneSystem(
            system_id=30000142,
            system_name="Jita",
            security=0.95,
            category="high_sec",
            region_name="The Forge",
            kills_current=15,
            pods_current=8,
            kills_previous=5,
            trend=3.0,
            predicted_1hr=10,
            predicted_2hr=7,
            gate_camp_likely=True,
        )
        assert hz.system_name == "Jita"
        assert hz.gate_camp_likely is True
        assert hz.trend == 3.0
