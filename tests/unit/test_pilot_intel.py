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


class TestInferActiveTimezone:
    """Tests for timezone inference."""

    def test_returns_none_for_empty_activity(self):
        assert _infer_active_timezone({}) is None
        assert _infer_active_timezone(None) is None

    def test_ustz_afternoon(self):
        # Peak at UTC 18-23 → USTZ
        activity = {str(h): 100 if 18 <= h <= 23 else 1 for h in range(24)}
        assert _infer_active_timezone(activity) == "USTZ"

    def test_eutz_morning(self):
        # Peak at UTC 6-11 → EUTZ (center ~9 → EUTZ maps to 0-5 center or wraps)
        activity = {str(h): 100 if 0 <= h <= 5 else 1 for h in range(24)}
        assert _infer_active_timezone(activity) == "EUTZ"

    def test_autz_midday(self):
        # Peak at UTC 6-11 → center ~9 → AUTZ
        activity = {str(h): 100 if 6 <= h <= 11 else 1 for h in range(24)}
        assert _infer_active_timezone(activity) == "AUTZ"

    def test_handles_non_numeric_keys(self):
        activity = {"abc": 100, "def": 200}
        assert _infer_active_timezone(activity) is None


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
