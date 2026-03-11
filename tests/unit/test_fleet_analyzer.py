"""Unit tests for fleet composition analyzer."""

import pytest

from backend.app.services.fleet_analyzer import (
    ShipRole,
    analyze_fleet,
    classify_ship,
    parse_fleet_text,
)


class TestParseFleetText:
    """Tests for fleet text parsing."""

    def test_multiplied_format(self):
        """Parse '2x Loki' style format."""
        text = "2x Loki\n3x Muninn\n1x Sabre"
        result = parse_fleet_text(text)
        assert result == {"Loki": 2, "Muninn": 3, "Sabre": 1}

    def test_multiplied_format_no_x(self):
        """Parse '2 Loki' style without x."""
        text = "2 Loki\n3 Muninn"
        result = parse_fleet_text(text)
        assert result == {"Loki": 2, "Muninn": 3}

    def test_tab_separated_format(self):
        """Parse EVE fleet window tab-separated copy."""
        text = (
            "PilotA\tLoki\tJita\tFleet Commander\n"
            "PilotB\tMuninn\tJita\tWing Commander\n"
            "PilotC\tMuninn\tJita\tSquad Member\n"
        )
        result = parse_fleet_text(text)
        assert result == {"Loki": 1, "Muninn": 2}

    def test_tab_separated_skips_header(self):
        """Header row with 'Ship Type' is skipped."""
        text = "Name\tShip Type\tSystem\tPosition\nPilotA\tLoki\tJita\tFC\n"
        result = parse_fleet_text(text)
        assert result == {"Loki": 1}

    def test_simple_ship_names(self):
        """Parse one ship name per line."""
        text = "Loki\nMuninn\nLoki"
        result = parse_fleet_text(text)
        assert result == {"Loki": 2, "Muninn": 1}

    def test_empty_input(self):
        """Empty string returns empty dict."""
        assert parse_fleet_text("") == {}
        assert parse_fleet_text("   ") == {}
        assert parse_fleet_text("\n\n") == {}

    def test_blank_lines_ignored(self):
        """Blank lines between entries are skipped."""
        text = "2x Loki\n\n3x Muninn\n\n"
        result = parse_fleet_text(text)
        assert result == {"Loki": 2, "Muninn": 3}

    def test_comment_lines_ignored(self):
        """Lines starting with # are skipped."""
        text = "# Fleet comp\n2x Loki\n# End"
        result = parse_fleet_text(text)
        assert result == {"Loki": 2}

    def test_mixed_formats(self):
        """Mixed multiplied and simple formats."""
        text = "3x Muninn\nLoki\nLoki"
        result = parse_fleet_text(text)
        assert result == {"Muninn": 3, "Loki": 2}


class TestClassifyShip:
    """Tests for ship classification."""

    def test_known_dps_ship(self):
        assert classify_ship("Muninn") == ShipRole.DPS

    def test_known_logistics_ship(self):
        assert classify_ship("Guardian") == ShipRole.LOGISTICS

    def test_known_tackle_ship(self):
        assert classify_ship("Sabre") == ShipRole.TACKLE

    def test_known_ewar_ship(self):
        assert classify_ship("Falcon") == ShipRole.EWAR

    def test_known_capital_ship(self):
        assert classify_ship("Revelation") == ShipRole.CAPITAL

    def test_known_scout_ship(self):
        assert classify_ship("Buzzard") == ShipRole.SCOUT

    def test_known_support_ship(self):
        assert classify_ship("Pontifex") == ShipRole.SUPPORT

    def test_case_insensitive(self):
        assert classify_ship("muninn") == ShipRole.DPS
        assert classify_ship("GUARDIAN") == ShipRole.LOGISTICS

    def test_unknown_ship(self):
        assert classify_ship("SpaceBoat9000") == ShipRole.UNKNOWN


class TestAnalyzeFleet:
    """Tests for full fleet analysis."""

    def test_empty_fleet(self):
        """Empty text returns minimal threat."""
        result = analyze_fleet("")
        assert result["total_pilots"] == 0
        assert result["threat_level"] == "minimal"
        assert result["has_logistics"] is False
        assert result["has_capitals"] is False
        assert result["has_tackle"] is False
        assert result["estimated_dps_category"] == "low"

    def test_small_gang(self):
        """Small gang with few ships."""
        text = "2x Loki\n1x Sabre\n1x Scimitar"
        result = analyze_fleet(text)
        assert result["total_pilots"] == 4
        assert result["has_logistics"] is True
        assert result["has_tackle"] is True
        assert result["threat_level"] == "minimal"  # <5 pilots

    def test_moderate_gang(self):
        """5+ pilot gang triggers moderate."""
        text = "3x Muninn\n1x Sabre\n1x Scimitar\n1x Loki"
        result = analyze_fleet(text)
        assert result["total_pilots"] == 6
        assert result["threat_level"] == "moderate"

    def test_significant_fleet(self):
        """15+ pilot fleet is significant."""
        lines = ["1x Muninn"] * 15
        text = "\n".join(lines)
        result = analyze_fleet(text)
        assert result["total_pilots"] == 15
        assert result["threat_level"] == "significant"

    def test_critical_fleet_with_capitals(self):
        """Capitals push to critical."""
        text = "5x Muninn\n2x Scimitar\n1x Revelation"
        result = analyze_fleet(text)
        assert result["has_capitals"] is True
        assert result["threat_level"] == "critical"

    def test_overwhelming_fleet(self):
        """Many capitals = overwhelming."""
        text = "5x Revelation\n10x Muninn\n5x Guardian"
        result = analyze_fleet(text)
        assert result["threat_level"] == "overwhelming"

    def test_composition_breakdown(self):
        """Composition dict has correct role counts."""
        text = "3x Muninn\n2x Guardian\n1x Sabre"
        result = analyze_fleet(text)
        assert result["composition"]["dps"] == 3
        assert result["composition"]["logistics"] == 2
        assert result["composition"]["tackle"] == 1

    def test_ship_list_sorted(self):
        """Ship list is sorted by count descending."""
        text = "1x Sabre\n3x Muninn\n2x Guardian"
        result = analyze_fleet(text)
        names = [s["name"] for s in result["ship_list"]]
        assert names[0] == "Muninn"
        assert names[1] == "Guardian"
        assert names[2] == "Sabre"

    def test_dps_category_extreme(self):
        """30+ DPS ships = extreme."""
        lines = ["1x Muninn"] * 30
        text = "\n".join(lines)
        result = analyze_fleet(text)
        assert result["estimated_dps_category"] == "extreme"

    def test_dps_category_high(self):
        """15-29 DPS ships = high."""
        lines = ["1x Muninn"] * 15
        text = "\n".join(lines)
        result = analyze_fleet(text)
        assert result["estimated_dps_category"] == "high"

    def test_dps_category_medium(self):
        """5-14 DPS ships = medium."""
        lines = ["1x Muninn"] * 5
        text = "\n".join(lines)
        result = analyze_fleet(text)
        assert result["estimated_dps_category"] == "medium"

    def test_advice_no_logistics(self):
        """Fleet without logi gets vulnerability advice."""
        text = "5x Muninn\n1x Sabre"
        result = analyze_fleet(text)
        advice_text = " ".join(result["advice"])
        assert (
            "vulnerable to attrition" in advice_text.lower()
            or "no logistics" in advice_text.lower()
        )

    def test_advice_heavy_tackle(self):
        """Heavy tackle fleet gets appropriate advice."""
        text = "5x Sabre\n3x Broadsword\n2x Muninn"
        result = analyze_fleet(text)
        advice_text = " ".join(result["advice"])
        assert "tackle" in advice_text.lower()

    def test_advice_ewar_present(self):
        """EWAR ships trigger counter-EWAR advice."""
        text = "3x Falcon\n5x Muninn"
        result = analyze_fleet(text)
        advice_text = " ".join(result["advice"])
        assert "ewar" in advice_text.lower()

    def test_unknown_ships_counted(self):
        """Unknown ships are still counted in totals."""
        text = "2x SpaceBoat\n3x Muninn"
        result = analyze_fleet(text)
        assert result["total_pilots"] == 5
        assert result["composition"].get("unknown", 0) == 2
        assert result["composition"].get("dps", 0) == 3

    def test_logi_with_10_pilots_is_significant(self):
        """10 pilots + logistics = significant."""
        text = "8x Muninn\n2x Scimitar"
        result = analyze_fleet(text)
        assert result["total_pilots"] == 10
        assert result["threat_level"] == "significant"

    def test_has_logistics_flag(self):
        """has_logistics is True when logi present."""
        text = "1x Guardian"
        result = analyze_fleet(text)
        assert result["has_logistics"] is True

    def test_has_capitals_flag(self):
        """has_capitals is True when caps present."""
        text = "1x Nyx"
        result = analyze_fleet(text)
        assert result["has_capitals"] is True

    def test_has_tackle_flag(self):
        """has_tackle is True when tackle present."""
        text = "1x Stiletto"
        result = analyze_fleet(text)
        assert result["has_tackle"] is True

    def test_large_logi_wing_advice(self):
        """Strong logi wing (>=20%) triggers alpha advice."""
        text = "6x Muninn\n4x Scimitar"
        result = analyze_fleet(text)
        advice_text = " ".join(result["advice"])
        assert "alpha" in advice_text.lower() or "strong logistics" in advice_text.lower()


class TestFleetAPIEndpoint:
    """Tests for the fleet API endpoint."""

    @pytest.mark.anyio
    async def test_analyze_endpoint_success(self):
        """POST /fleet/analyze returns valid response."""
        from backend.app.api.v1.fleet import analyze_fleet_composition
        from backend.app.models.fleet import FleetAnalyzeRequest

        request = FleetAnalyzeRequest(text="3x Muninn\n2x Scimitar\n1x Sabre")
        result = await analyze_fleet_composition(request)

        assert result.total_pilots == 6
        assert result.threat_level == "moderate"
        assert result.has_logistics is True
        assert result.has_tackle is True

    @pytest.mark.anyio
    async def test_analyze_endpoint_empty_text(self):
        """Empty text still returns a valid minimal response."""
        from backend.app.api.v1.fleet import analyze_fleet_composition
        from backend.app.models.fleet import FleetAnalyzeRequest

        request = FleetAnalyzeRequest(text=" ")
        result = await analyze_fleet_composition(request)
        assert result.total_pilots == 0
        assert result.threat_level == "minimal"
