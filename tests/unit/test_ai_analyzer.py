"""Unit tests for AI analyzer service."""

import pytest

from backend.app.models.ai import RouteAnalysisRequest
from backend.app.models.risk import DangerLevel, ZKillStats
from backend.app.services.ai_analyzer import (
    classify_danger,
    generate_assessment,
    generate_system_warning,
    get_danger_thresholds,
)


class TestClassifyDanger:
    """Tests for classify_danger function."""

    @pytest.fixture
    def default_thresholds(self) -> dict[str, int]:
        """Default danger thresholds."""
        return {"medium": 5, "high": 10, "extreme": 20}

    def test_low_danger_zero_kills(self, default_thresholds):
        """Test low danger with zero kills."""
        stats = ZKillStats(recent_kills=0, recent_pods=0)
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.low

    def test_low_danger_below_medium_threshold(self, default_thresholds):
        """Test low danger below medium threshold."""
        stats = ZKillStats(recent_kills=2, recent_pods=2)  # 4 total
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.low

    def test_medium_danger_at_threshold(self, default_thresholds):
        """Test medium danger at exact threshold."""
        stats = ZKillStats(recent_kills=3, recent_pods=2)  # 5 total
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.medium

    def test_medium_danger_between_thresholds(self, default_thresholds):
        """Test medium danger between medium and high thresholds."""
        stats = ZKillStats(recent_kills=5, recent_pods=2)  # 7 total
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.medium

    def test_high_danger_at_threshold(self, default_thresholds):
        """Test high danger at exact threshold."""
        stats = ZKillStats(recent_kills=8, recent_pods=2)  # 10 total
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.high

    def test_high_danger_between_thresholds(self, default_thresholds):
        """Test high danger between high and extreme thresholds."""
        stats = ZKillStats(recent_kills=10, recent_pods=5)  # 15 total
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.high

    def test_extreme_danger_at_threshold(self, default_thresholds):
        """Test extreme danger at exact threshold."""
        stats = ZKillStats(recent_kills=15, recent_pods=5)  # 20 total
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.extreme

    def test_extreme_danger_above_threshold(self, default_thresholds):
        """Test extreme danger well above threshold."""
        stats = ZKillStats(recent_kills=100, recent_pods=50)  # 150 total
        level = classify_danger(stats, default_thresholds)
        assert level == DangerLevel.extreme

    def test_custom_thresholds(self):
        """Test with custom thresholds."""
        custom = {"medium": 10, "high": 50, "extreme": 100}
        stats = ZKillStats(recent_kills=30, recent_pods=10)  # 40 total
        level = classify_danger(stats, custom)
        assert level == DangerLevel.medium

    def test_missing_threshold_uses_default(self):
        """Test that missing threshold keys use defaults."""
        incomplete = {"medium": 5}  # Missing high and extreme
        stats = ZKillStats(recent_kills=15, recent_pods=10)  # 25 total
        level = classify_danger(stats, incomplete)
        assert level == DangerLevel.extreme  # Uses default 20


class TestGenerateSystemWarning:
    """Tests for generate_system_warning function."""

    def test_extreme_danger_warning(self):
        """Test warning text for extreme danger."""
        stats = ZKillStats(recent_kills=50, recent_pods=10)
        warning = generate_system_warning("Amamake", 30002537, DangerLevel.extreme, stats)

        assert warning.system_name == "Amamake"
        assert warning.system_id == 30002537
        assert warning.danger_level == DangerLevel.extreme
        assert warning.recent_kills == 50
        assert warning.recent_pods == 10
        assert "EXTREME DANGER" in warning.warning_text
        assert "warzone" in warning.warning_text
        assert "60" in warning.warning_text  # 50 + 10

    def test_high_danger_warning(self):
        """Test warning text for high danger."""
        stats = ZKillStats(recent_kills=12, recent_pods=3)
        warning = generate_system_warning("Rancer", 30003068, DangerLevel.high, stats)

        assert warning.danger_level == DangerLevel.high
        assert "HIGH DANGER" in warning.warning_text
        assert "caution" in warning.warning_text.lower()

    def test_medium_danger_warning(self):
        """Test warning text for medium danger."""
        stats = ZKillStats(recent_kills=5, recent_pods=2)
        warning = generate_system_warning("Tama", 30002813, DangerLevel.medium, stats)

        assert warning.danger_level == DangerLevel.medium
        assert "CAUTION" in warning.warning_text
        assert "moderate" in warning.warning_text.lower()

    def test_low_danger_warning(self):
        """Test warning text for low danger."""
        stats = ZKillStats(recent_kills=1, recent_pods=0)
        warning = generate_system_warning("Jita", 30000142, DangerLevel.low, stats)

        assert warning.danger_level == DangerLevel.low
        assert "quiet" in warning.warning_text.lower()


class TestGenerateAssessment:
    """Tests for generate_assessment function."""

    def test_low_risk_assessment(self):
        """Test assessment for route with no dangerous systems."""
        dangerous_systems: list[tuple[str, DangerLevel]] = []
        overall, text = generate_assessment("Jita", "Amarr", 15, dangerous_systems)

        assert overall == DangerLevel.low
        assert "LOW RISK" in text
        assert "15 jumps" in text

    def test_medium_risk_assessment(self):
        """Test assessment for route with medium-danger systems only."""
        dangerous_systems = [("Tama", DangerLevel.medium)]
        overall, text = generate_assessment("Jita", "Nennamaila", 8, dangerous_systems)

        assert overall == DangerLevel.medium
        assert "MODERATE RISK" in text
        assert "1 system" in text

    def test_high_risk_assessment(self):
        """Test assessment for route with high-danger systems."""
        dangerous_systems = [
            ("Rancer", DangerLevel.high),
            ("Tama", DangerLevel.medium),
        ]
        overall, text = generate_assessment("Jita", "Amamake", 20, dangerous_systems)

        assert overall == DangerLevel.high
        assert "HIGH RISK" in text
        assert "2 dangerous" in text
        assert "safer" in text.lower() or "paranoid" in text.lower()

    def test_extreme_risk_assessment(self):
        """Test assessment for route with extreme-danger systems."""
        dangerous_systems = [
            ("Amamake", DangerLevel.extreme),
            ("Rancer", DangerLevel.high),
        ]
        overall, text = generate_assessment("Jita", "Amamake", 25, dangerous_systems)

        assert overall == DangerLevel.extreme
        assert "CRITICAL" in text
        assert "Amamake" in text
        assert "fleet" in text.lower() or "alternative" in text.lower()

    def test_extreme_with_multiple_systems_truncates(self):
        """Test that many extreme systems are truncated in text."""
        dangerous_systems = [
            ("System1", DangerLevel.extreme),
            ("System2", DangerLevel.extreme),
            ("System3", DangerLevel.extreme),
            ("System4", DangerLevel.extreme),
            ("System5", DangerLevel.extreme),
        ]
        overall, text = generate_assessment("Origin", "Dest", 30, dangerous_systems)

        assert overall == DangerLevel.extreme
        assert "+2 more" in text  # 5 - 3 shown = 2 more


class TestGetDangerThresholds:
    """Tests for get_danger_thresholds function."""

    def test_returns_thresholds(self):
        """Test that thresholds are returned correctly."""
        response = get_danger_thresholds()

        assert response.medium >= 1
        assert response.high > response.medium
        assert response.extreme > response.high
        assert response.description  # Has description text

    def test_default_thresholds_values(self):
        """Test default threshold values from config."""
        response = get_danger_thresholds()

        # These should match risk_config.json defaults
        assert response.medium == 5
        assert response.high == 10
        assert response.extreme == 20


class TestAnalyzeRouteIntegration:
    """Integration tests for analyze_route function using real data."""

    def test_analyze_highsec_route(self):
        """Test analyzing a highsec route."""
        from backend.app.services.ai_analyzer import analyze_route

        request = RouteAnalysisRequest(
            from_system="Jita",
            to_system="Perimeter",
            profile="shortest",
        )
        response = analyze_route(request)

        assert response.from_system == "Jita"
        assert response.to_system == "Perimeter"
        assert response.total_jumps == 1
        # Danger level depends on cached zkill stats, just verify it's valid
        assert response.overall_danger in DangerLevel
        assert response.assessment  # Has assessment text
        assert len(response.path_danger) == 2  # Jita and Perimeter

    def test_analyze_route_validates_systems(self):
        """Test that invalid systems raise ValueError."""
        from backend.app.services.ai_analyzer import analyze_route

        request = RouteAnalysisRequest(
            from_system="NonExistent",
            to_system="Jita",
        )
        with pytest.raises(ValueError, match="Unknown system"):
            analyze_route(request)

    def test_analyze_route_validates_profile(self):
        """Test that invalid profile raises ValueError."""
        from backend.app.services.ai_analyzer import analyze_route

        request = RouteAnalysisRequest(
            from_system="Jita",
            to_system="Perimeter",
            profile="invalid_profile",
        )
        with pytest.raises(ValueError, match="Unknown profile"):
            analyze_route(request)

    def test_analyze_route_path_danger_populated(self):
        """Test that path_danger contains all systems."""
        from backend.app.services.ai_analyzer import analyze_route

        request = RouteAnalysisRequest(
            from_system="Jita",
            to_system="Urlen",  # 2 jumps
            profile="shortest",
        )
        response = analyze_route(request)

        assert len(response.path_danger) == 3  # Jita, Perimeter, Urlen
        for pd in response.path_danger:
            assert pd.system_name
            assert pd.danger_level in DangerLevel
            assert pd.recent_kills >= 0

    def test_analyze_route_alternatives_only_for_dangerous_routes(self):
        """Test that alternatives are only suggested for dangerous routes."""
        from backend.app.services.ai_analyzer import analyze_route

        request = RouteAnalysisRequest(
            from_system="Jita",
            to_system="Perimeter",
            include_alternatives=True,
        )
        response = analyze_route(request)

        # Alternatives only suggested for high/extreme danger
        if response.overall_danger in (DangerLevel.low, DangerLevel.medium):
            assert len(response.alternatives) == 0
        # If danger is high/extreme, alternatives may or may not exist depending on routes

    def test_analyze_route_respects_include_alternatives_flag(self):
        """Test that include_alternatives=False skips alternative search."""
        from backend.app.services.ai_analyzer import analyze_route

        request = RouteAnalysisRequest(
            from_system="Jita",
            to_system="Perimeter",
            include_alternatives=False,
        )
        response = analyze_route(request)

        assert len(response.alternatives) == 0
