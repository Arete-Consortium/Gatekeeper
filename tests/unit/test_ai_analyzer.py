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


class TestFindAlternatives:
    """Tests for _find_alternatives function edge cases."""

    def test_paranoid_profile_no_alternatives(self):
        """Test that paranoid profile has no safer alternatives to suggest."""
        from unittest.mock import MagicMock

        from backend.app.services.ai_analyzer import _find_alternatives

        # Create a mock route
        mock_route = MagicMock()
        mock_route.path = []
        mock_route.total_jumps = 5

        thresholds = {"medium": 5, "high": 10, "extreme": 20}

        alternatives = _find_alternatives(
            "Jita",
            "Amarr",
            "paranoid",  # Already safest profile
            mock_route,
            set(),
            False,
            thresholds,
        )

        # paranoid has no safer profiles
        assert len(alternatives) == 0

    def test_safer_profile_tries_paranoid_only(self):
        """Test that safer profile only tries paranoid."""
        from unittest.mock import MagicMock, patch

        from backend.app.services.ai_analyzer import _find_alternatives

        mock_route = MagicMock()
        mock_route.path = []
        mock_route.total_jumps = 5

        thresholds = {"medium": 5, "high": 10, "extreme": 20}

        # Mock compute_route to raise ValueError (no route found)
        with patch(
            "backend.app.services.ai_analyzer.compute_route",
            side_effect=ValueError("No route"),
        ):
            alternatives = _find_alternatives(
                "Jita",
                "Amarr",
                "safer",
                mock_route,
                set(),
                False,
                thresholds,
            )

        # ValueError means no route found, should return empty
        assert len(alternatives) == 0

    def test_alternative_not_suggested_if_not_better(self):
        """Test alternatives not suggested if same/more dangerous systems."""
        from unittest.mock import MagicMock, patch

        from backend.app.services.ai_analyzer import _find_alternatives

        # Mock current route with 0 dangerous systems
        mock_current_route = MagicMock()
        mock_hop = MagicMock()
        mock_hop.system_name = "Jita"
        mock_current_route.path = [mock_hop]
        mock_current_route.total_jumps = 1

        # Alternative route also has 0 dangerous
        mock_alt_route = MagicMock()
        mock_alt_route.path = [mock_hop, mock_hop]  # Longer but same danger
        mock_alt_route.total_jumps = 2

        thresholds = {"medium": 5, "high": 10, "extreme": 20}

        # Both routes have 0 dangerous systems, alternative is not better
        with (
            patch(
                "backend.app.services.ai_analyzer.compute_route",
                return_value=mock_alt_route,
            ),
            patch(
                "backend.app.services.ai_analyzer._count_dangerous_systems",
                return_value=0,  # Same danger for both
            ),
        ):
            alternatives = _find_alternatives(
                "Jita",
                "Amarr",
                "shortest",
                mock_current_route,
                set(),
                False,
                thresholds,
            )

        # Alternative not better, should not be suggested
        assert len(alternatives) == 0

    def test_alternative_suggested_with_same_or_fewer_jumps(self):
        """Test alternative improvement text when same or fewer jumps."""
        from unittest.mock import MagicMock, patch

        from backend.app.services.ai_analyzer import _find_alternatives

        # Mock current route with 2 dangerous systems
        mock_current_route = MagicMock()
        mock_hop = MagicMock()
        mock_hop.system_name = "Jita"
        mock_current_route.path = [mock_hop]
        mock_current_route.total_jumps = 10

        # Alternative route - same jumps but safer
        mock_alt_route = MagicMock()
        mock_alt_route.path = [mock_hop]
        mock_alt_route.total_jumps = 10  # Same jumps
        mock_alt_route.max_risk = 5.0
        mock_alt_route.avg_risk = 2.0

        thresholds = {"medium": 5, "high": 10, "extreme": 20}

        call_count = [0]

        def mock_count_dangerous(path, thresh):
            call_count[0] += 1
            if call_count[0] == 1:
                return 2  # Current route - 2 dangerous
            return 1  # Alternative - 1 dangerous

        with (
            patch(
                "backend.app.services.ai_analyzer.compute_route",
                return_value=mock_alt_route,
            ),
            patch(
                "backend.app.services.ai_analyzer._count_dangerous_systems",
                side_effect=mock_count_dangerous,
            ),
        ):
            alternatives = _find_alternatives(
                "Jita",
                "Amarr",
                "shortest",
                mock_current_route,
                set(),
                False,
                thresholds,
            )

        assert len(alternatives) >= 1
        assert "Same or fewer jumps" in alternatives[0].improvement

    def test_alternative_with_more_jumps(self):
        """Test alternative improvement text when more jumps."""
        from unittest.mock import MagicMock, patch

        from backend.app.services.ai_analyzer import _find_alternatives

        mock_current_route = MagicMock()
        mock_hop = MagicMock()
        mock_hop.system_name = "Jita"
        mock_current_route.path = [mock_hop]
        mock_current_route.total_jumps = 10

        mock_alt_route = MagicMock()
        mock_alt_route.path = [mock_hop]
        mock_alt_route.total_jumps = 15  # 5 more jumps
        mock_alt_route.max_risk = 5.0
        mock_alt_route.avg_risk = 2.0

        thresholds = {"medium": 5, "high": 10, "extreme": 20}

        call_count = [0]

        def mock_count_dangerous(path, thresh):
            call_count[0] += 1
            if call_count[0] == 1:
                return 3  # Current route - 3 dangerous
            return 1  # Alternative - 1 dangerous

        with (
            patch(
                "backend.app.services.ai_analyzer.compute_route",
                return_value=mock_alt_route,
            ),
            patch(
                "backend.app.services.ai_analyzer._count_dangerous_systems",
                side_effect=mock_count_dangerous,
            ),
        ):
            alternatives = _find_alternatives(
                "Jita",
                "Amarr",
                "shortest",
                mock_current_route,
                set(),
                False,
                thresholds,
            )

        assert len(alternatives) >= 1
        assert "Adds 5 jump(s)" in alternatives[0].improvement
        assert "avoids 2 dangerous" in alternatives[0].improvement

    def test_alternative_compute_route_value_error(self):
        """Test that ValueError from compute_route is handled."""
        from unittest.mock import MagicMock, patch

        from backend.app.services.ai_analyzer import _find_alternatives

        mock_current_route = MagicMock()
        mock_hop = MagicMock()
        mock_hop.system_name = "Jita"
        mock_current_route.path = [mock_hop]
        mock_current_route.total_jumps = 10

        thresholds = {"medium": 5, "high": 10, "extreme": 20}

        # First call to _count_dangerous_systems returns danger count
        # compute_route raises ValueError
        with (
            patch(
                "backend.app.services.ai_analyzer.compute_route",
                side_effect=ValueError("No route found"),
            ),
            patch(
                "backend.app.services.ai_analyzer._count_dangerous_systems",
                return_value=2,
            ),
        ):
            alternatives = _find_alternatives(
                "Jita",
                "Amarr",
                "shortest",
                mock_current_route,
                set(),
                False,
                thresholds,
            )

        # ValueError is caught, should return empty
        assert len(alternatives) == 0

    def test_profile_not_in_routing_profiles(self):
        """Test handling when alternative profile not in routing_profiles."""
        from unittest.mock import MagicMock, patch

        from backend.app.services.ai_analyzer import _find_alternatives

        mock_current_route = MagicMock()
        mock_hop = MagicMock()
        mock_hop.system_name = "Jita"
        mock_current_route.path = [mock_hop]
        mock_current_route.total_jumps = 10

        thresholds = {"medium": 5, "high": 10, "extreme": 20}

        # Mock config with no safer/paranoid profiles
        mock_config = MagicMock()
        mock_config.routing_profiles = {"shortest": {}}  # Only has shortest

        with (
            patch(
                "backend.app.services.ai_analyzer.load_risk_config",
                return_value=mock_config,
            ),
            patch(
                "backend.app.services.ai_analyzer._count_dangerous_systems",
                return_value=2,
            ),
        ):
            alternatives = _find_alternatives(
                "Jita",
                "Amarr",
                "shortest",
                mock_current_route,
                set(),
                False,
                thresholds,
            )

        # safer and paranoid not in config, should skip them
        assert len(alternatives) == 0
