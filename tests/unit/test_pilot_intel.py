"""Unit tests for pilot intel service."""

import pytest

from backend.app.services.pilot_intel import (
    _compute_threat_level,
    _detect_flags,
    _infer_active_timezone,
)


class TestComputeThreatLevel:
    """Tests for threat level computation."""

    def test_minimal_threat_zero_stats(self):
        assert _compute_threat_level({"kills": 0, "danger_ratio": 0, "solo_kills": 0}) == "minimal"

    def test_low_threat(self):
        assert _compute_threat_level({"kills": 200, "danger_ratio": 30, "solo_kills": 10}) == "low"

    def test_moderate_threat(self):
        assert _compute_threat_level({"kills": 1500, "danger_ratio": 65, "solo_kills": 50}) == "moderate"

    def test_high_threat(self):
        assert _compute_threat_level({"kills": 5500, "danger_ratio": 70, "solo_kills": 200}) == "high"

    def test_extreme_threat(self):
        assert _compute_threat_level({"kills": 15000, "danger_ratio": 85, "solo_kills": 600}) == "extreme"

    def test_kills_only_scoring(self):
        # 10001+ kills = 4 points, danger 0 = 0, solo 0 = 0 → score 4 → moderate
        result = _compute_threat_level({"kills": 10001, "danger_ratio": 0, "solo_kills": 0})
        assert result in ("moderate", "high")

    def test_danger_only_scoring(self):
        # kills 0 = 0, danger 85 = 3, solo 0 = 0 → score 3 → moderate
        assert _compute_threat_level({"kills": 0, "danger_ratio": 85, "solo_kills": 0}) == "moderate"


def _make_kills_at_hours(hours: list[int]) -> list[dict]:
    """Create fake killmails with timestamps at the given UTC hours."""
    return [{"timestamp": f"2026-03-10T{h:02d}:00:00Z"} for h in hours]


class TestInferActiveTimezone:
    """Tests for timezone inference."""

    def test_returns_none_for_empty_kills(self):
        assert _infer_active_timezone([]) is None
        assert _infer_active_timezone(None) is None

    def test_ustz_afternoon(self):
        # Peak at UTC 18-23 → USTZ
        kills = _make_kills_at_hours([18, 19, 20, 21, 22, 23] * 10 + list(range(18)))
        assert _infer_active_timezone(kills) == "USTZ"

    def test_eutz_morning(self):
        # Peak at UTC 0-5 → EUTZ
        kills = _make_kills_at_hours([0, 1, 2, 3, 4, 5] * 10 + list(range(6, 24)))
        assert _infer_active_timezone(kills) == "EUTZ"

    def test_autz_midday(self):
        # Peak at UTC 6-11 → center ~9 → AUTZ
        kills = _make_kills_at_hours([6, 7, 8, 9, 10, 11] * 10 + list(range(12, 24)))
        assert _infer_active_timezone(kills) == "AUTZ"

    def test_handles_bad_timestamps(self):
        kills = [{"timestamp": ""}, {"timestamp": "not-a-date"}, {}]
        assert _infer_active_timezone(kills) is None


class TestDetectFlags:
    """Tests for behavior flag detection."""

    def test_no_flags_empty_stats(self):
        flags = _detect_flags({"top_ships": [], "solo_kills": 0, "danger_ratio": 0, "gang_ratio": 0, "active_pvp_kills": 0})
        assert flags == []

    def test_solo_hunter_flag(self):
        flags = _detect_flags({
            "top_ships": [],
            "solo_kills": 200,
            "danger_ratio": 70,
            "gang_ratio": 0,
            "active_pvp_kills": 0,
        })
        assert "solo_hunter" in flags

    def test_gang_focus_flag(self):
        flags = _detect_flags({
            "top_ships": [],
            "solo_kills": 0,
            "danger_ratio": 0,
            "gang_ratio": 90,
            "active_pvp_kills": 0,
        })
        assert "gang_focus" in flags

    def test_recently_active_flag(self):
        flags = _detect_flags({
            "top_ships": [],
            "solo_kills": 0,
            "danger_ratio": 0,
            "gang_ratio": 0,
            "active_pvp_kills": 60,
        })
        assert "recently_active" in flags

    def test_capital_pilot_flag(self):
        flags = _detect_flags({
            "top_ships": [{"name": "Revelation", "kills": 100}],
            "solo_kills": 0,
            "danger_ratio": 0,
            "gang_ratio": 0,
            "active_pvp_kills": 0,
        })
        assert "capital_pilot" in flags

    def test_possible_cyno_flag(self):
        flags = _detect_flags({
            "top_ships": [{"name": "Falcon", "kills": 50}],
            "solo_kills": 0,
            "danger_ratio": 0,
            "gang_ratio": 0,
            "active_pvp_kills": 0,
        })
        assert "possible_cyno" in flags

    def test_multiple_flags(self):
        flags = _detect_flags({
            "top_ships": [{"name": "Revelation", "kills": 100}],
            "solo_kills": 200,
            "danger_ratio": 70,
            "gang_ratio": 0,
            "active_pvp_kills": 60,
        })
        assert "capital_pilot" in flags
        assert "solo_hunter" in flags
        assert "recently_active" in flags
