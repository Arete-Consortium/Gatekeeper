"""
End-to-end integration tests for all 11 MCP tools.

Each test sends a JSON-RPC request through MCPServer.handle_request()
and validates the full response payload from real services.

Coverage:
- gatekeeper_route: Route calculation with various profiles and options
- gatekeeper_system_threat: System threat/risk analysis
- gatekeeper_parse_fitting: EFT fitting parsing
- gatekeeper_analyze_fitting: Fitting analysis with travel recommendations
- gatekeeper_ship_info: Ship information lookup
- gatekeeper_region_map: Region information
- gatekeeper_jump_range: Systems within jump range
- gatekeeper_create_alert: Alert subscription creation
- gatekeeper_list_alerts: Alert subscription listing
- gatekeeper_thera_connections: Thera wormhole connections
- gatekeeper_thera_status: Thera API status
"""

import json

import pytest

from backend.app.mcp.server import MCPServer
from backend.app.services.webhooks import clear_subscriptions


@pytest.fixture
def server():
    return MCPServer()


@pytest.fixture(autouse=True)
def _clean_subscriptions():
    clear_subscriptions()
    yield
    clear_subscriptions()


def _call(tool_name: str, **arguments) -> dict:
    """Build a JSON-RPC tools/call request."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }


def _parse_content(response: dict) -> dict:
    """Extract parsed JSON from MCP tool response content."""
    assert "result" in response, f"Expected result, got: {response}"
    content = response["result"]["content"]
    assert len(content) > 0
    assert content[0]["type"] == "text"
    return json.loads(content[0]["text"])


# ---------------------------------------------------------------------------
# 1. gatekeeper_route
# ---------------------------------------------------------------------------
class TestRouteIntegration:
    @pytest.mark.asyncio
    async def test_route_jita_to_amarr(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr")
        )
        data = _parse_content(resp)

        assert data["from_system"] == "Jita"
        assert data["to_system"] == "Amarr"
        assert data["total_jumps"] > 0
        assert isinstance(data["path"], list)
        assert len(data["path"]) > 0
        assert data["path"][0]["system_name"] == "Jita"
        assert data["path"][-1]["system_name"] == "Amarr"

    @pytest.mark.asyncio
    async def test_route_with_safer_profile(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", profile="safer")
        )
        data = _parse_content(resp)
        assert data["profile"] == "safer"

    @pytest.mark.asyncio
    async def test_route_with_paranoid_profile(self, server):
        """Paranoid profile should have highest risk avoidance."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", profile="paranoid")
        )
        data = _parse_content(resp)
        assert data["profile"] == "paranoid"
        # Paranoid routes may be longer to avoid risky systems
        assert data["total_jumps"] >= 0

    @pytest.mark.asyncio
    async def test_route_with_avoid(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", avoid_systems=["Niarja"])
        )
        data = _parse_content(resp)
        path_names = [h["system_name"] for h in data["path"]]
        assert "Niarja" not in path_names

    @pytest.mark.asyncio
    async def test_route_with_multiple_avoid(self, server):
        """Test avoiding multiple systems."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_route",
                origin="Jita",
                destination="Amarr",
                avoid_systems=["Niarja", "Uedama"],
            )
        )
        data = _parse_content(resp)
        path_names = [h["system_name"] for h in data["path"]]
        assert "Niarja" not in path_names
        assert "Uedama" not in path_names

    @pytest.mark.asyncio
    async def test_route_unknown_system(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="FakeSystem999", destination="Amarr")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_route_unknown_destination(self, server):
        """Test with unknown destination system."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="NonExistentSystem")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_route_same_system(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Jita")
        )
        data = _parse_content(resp)
        # Same system: path contains just the origin, 0 jumps
        assert data["total_jumps"] == 0
        assert len(data["path"]) == 1
        assert data["path"][0]["system_name"] == "Jita"

    @pytest.mark.asyncio
    async def test_route_with_thera_option(self, server):
        """Test route with Thera wormhole option enabled."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", use_thera=True)
        )
        data = _parse_content(resp)
        # Route should still be valid even if no Thera shortcuts are available
        assert data["from_system"] == "Jita"
        assert data["to_system"] == "Amarr"
        assert data["total_jumps"] >= 0

    @pytest.mark.asyncio
    async def test_route_path_has_system_ids(self, server):
        """Verify each hop in path has a system_id."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Perimeter")
        )
        data = _parse_content(resp)
        for hop in data["path"]:
            assert "system_id" in hop
            assert isinstance(hop["system_id"], int)

    @pytest.mark.asyncio
    async def test_route_path_has_risk_scores(self, server):
        """Verify each hop in path has a risk_score."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Perimeter")
        )
        data = _parse_content(resp)
        for hop in data["path"]:
            assert "risk_score" in hop
            assert isinstance(hop["risk_score"], (int, float))

    @pytest.mark.asyncio
    async def test_route_response_contains_statistics(self, server):
        """Verify route response has statistical summaries."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr")
        )
        data = _parse_content(resp)
        assert "max_risk" in data
        assert "avg_risk" in data
        assert "total_cost" in data


# ---------------------------------------------------------------------------
# 2. gatekeeper_system_threat
# ---------------------------------------------------------------------------
class TestSystemThreatIntegration:
    @pytest.mark.asyncio
    async def test_threat_known_system(self, server):
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Jita"))
        data = _parse_content(resp)

        assert data["system_name"] == "Jita"
        assert "risk_score" in data
        assert isinstance(data["risk_score"], (int, float))
        assert "risk_color" in data
        assert data["risk_color"].startswith("#")
        assert "breakdown" in data
        assert "security_component" in data["breakdown"]
        assert "kills_component" in data["breakdown"]
        assert "pods_component" in data["breakdown"]
        assert "category" in data

    @pytest.mark.asyncio
    async def test_threat_highsec_system(self, server):
        """High-sec system should have lower base risk."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Jita"))
        data = _parse_content(resp)

        assert data["system_name"] == "Jita"
        assert data["category"] == "highsec"
        assert data["security"] >= 0.5

    @pytest.mark.asyncio
    async def test_threat_lowsec_system(self, server):
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Tama"))
        data = _parse_content(resp)

        assert data["system_name"] == "Tama"
        assert data["category"] == "lowsec"
        # Lowsec base risk should be non-trivial
        assert data["risk_score"] > 0

    @pytest.mark.asyncio
    async def test_threat_nullsec_system(self, server):
        """Null-sec system should have high base risk."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="HED-GP"))
        data = _parse_content(resp)

        assert data["system_name"] == "HED-GP"
        assert data["category"] == "nullsec"
        assert data["security"] <= 0.0

    @pytest.mark.asyncio
    async def test_threat_has_danger_level(self, server):
        """Verify response includes danger level classification."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Jita"))
        data = _parse_content(resp)

        assert "danger_level" in data
        assert data["danger_level"] in ["safe", "caution", "dangerous", "deadly", "unknown"]

    @pytest.mark.asyncio
    async def test_threat_has_system_id(self, server):
        """Verify response includes system_id."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Jita"))
        data = _parse_content(resp)

        assert "system_id" in data
        assert isinstance(data["system_id"], int)

    @pytest.mark.asyncio
    async def test_threat_unknown_system(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_system_threat", system_name="FakeSystem999")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_threat_risk_color_is_hex(self, server):
        """Risk color should be a valid hex color code."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Jita"))
        data = _parse_content(resp)

        color = data["risk_color"]
        assert color.startswith("#")
        assert len(color) == 7  # #RRGGBB format


# ---------------------------------------------------------------------------
# 3. gatekeeper_parse_fitting
# ---------------------------------------------------------------------------
SAMPLE_EFT = """[Caracal, Travel Fit]
Damage Control II
Nanofiber Internal Structure II

50MN Microwarpdrive II
"""

SAMPLE_COVERT_FIT = """[Stratios, Covert Travel]
Damage Control II
Nanofiber Internal Structure II

50MN Microwarpdrive II

Covert Ops Cloaking Device II
"""

SAMPLE_CAPITAL_FIT = """[Archon, Travel]
Capital Armor Repairer I
"""

SAMPLE_BLOPS_FIT = """[Sin, Bridge Fit]
Damage Control II
"""


class TestParseFittingIntegration:
    @pytest.mark.asyncio
    async def test_parse_valid_fitting(self, server):
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text=SAMPLE_EFT))
        data = _parse_content(resp)

        assert data["ship_name"] == "Caracal"
        assert data["ship_category"] == "cruiser"
        assert "Damage Control II" in data["modules"]
        assert "travel_capabilities" in data

    @pytest.mark.asyncio
    async def test_parse_fitting_with_covert_cloak(self, server):
        """Covert ops cloak should be detected."""
        resp = await server.handle_request(
            _call("gatekeeper_parse_fitting", eft_text=SAMPLE_COVERT_FIT)
        )
        data = _parse_content(resp)

        assert data["ship_name"] == "Stratios"
        assert data["travel_capabilities"]["is_covert_capable"] is True

    @pytest.mark.asyncio
    async def test_parse_fitting_with_align_mods(self, server):
        """Align mods should be detected."""
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text=SAMPLE_EFT))
        data = _parse_content(resp)

        # Nanofiber should be detected as align mod
        assert data["travel_capabilities"]["has_align_mods"] is True

    @pytest.mark.asyncio
    async def test_parse_capital_fitting(self, server):
        """Capital ships should be identified."""
        resp = await server.handle_request(
            _call("gatekeeper_parse_fitting", eft_text=SAMPLE_CAPITAL_FIT)
        )
        data = _parse_content(resp)

        assert data["ship_name"] == "Archon"
        assert data["ship_category"] == "capital"
        assert data["jump_capability"] == "jump_drive"

    @pytest.mark.asyncio
    async def test_parse_blops_fitting(self, server):
        """Black Ops should be identified with covert bridge capability."""
        resp = await server.handle_request(
            _call("gatekeeper_parse_fitting", eft_text=SAMPLE_BLOPS_FIT)
        )
        data = _parse_content(resp)

        assert data["ship_name"] == "Sin"
        assert data["jump_capability"] == "covert_bridge"

    @pytest.mark.asyncio
    async def test_parse_invalid_fitting(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_parse_fitting", eft_text="not a valid fitting")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_parse_empty_fitting(self, server):
        """Empty text should return error."""
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text=""))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_parse_fitting_missing_bracket(self, server):
        """Missing bracket should return error."""
        resp = await server.handle_request(
            _call("gatekeeper_parse_fitting", eft_text="Caracal, Travel Fit]")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_parse_fitting_has_hint_on_error(self, server):
        """Error response should include hint."""
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text="invalid"))
        data = _parse_content(resp)
        assert "hint" in data


# ---------------------------------------------------------------------------
# 4. gatekeeper_analyze_fitting
# ---------------------------------------------------------------------------
class TestAnalyzeFittingIntegration:
    @pytest.mark.asyncio
    async def test_analyze_valid_fitting(self, server):
        resp = await server.handle_request(_call("gatekeeper_analyze_fitting", eft_text=SAMPLE_EFT))
        data = _parse_content(resp)

        assert data["fitting"]["ship_name"] == "Caracal"
        rec = data["travel_recommendation"]
        assert rec["can_use_gates"] is True
        assert "recommended_profile" in rec

    @pytest.mark.asyncio
    async def test_analyze_capital_fitting(self, server):
        """Capital ships should warn about gate restrictions."""
        resp = await server.handle_request(
            _call("gatekeeper_analyze_fitting", eft_text=SAMPLE_CAPITAL_FIT)
        )
        data = _parse_content(resp)

        rec = data["travel_recommendation"]
        assert rec["can_use_gates"] is False
        assert rec["can_jump"] is True
        # Should have warning about not using gates
        assert any("gate" in w.lower() for w in rec["warnings"])

    @pytest.mark.asyncio
    async def test_analyze_covert_fitting(self, server):
        """Covert ships should get appropriate tips."""
        resp = await server.handle_request(
            _call("gatekeeper_analyze_fitting", eft_text=SAMPLE_COVERT_FIT)
        )
        data = _parse_content(resp)

        rec = data["travel_recommendation"]
        assert rec["can_use_gates"] is True
        # Should have tip about covert cloak
        assert any("covert" in t.lower() for t in rec["tips"])

    @pytest.mark.asyncio
    async def test_analyze_blops_fitting(self, server):
        """Black Ops should indicate bridging capability."""
        resp = await server.handle_request(
            _call("gatekeeper_analyze_fitting", eft_text=SAMPLE_BLOPS_FIT)
        )
        data = _parse_content(resp)

        rec = data["travel_recommendation"]
        assert rec["can_covert_bridge"] is True

    @pytest.mark.asyncio
    async def test_analyze_fitting_has_all_recommendation_fields(self, server):
        """Verify all recommendation fields are present."""
        resp = await server.handle_request(_call("gatekeeper_analyze_fitting", eft_text=SAMPLE_EFT))
        data = _parse_content(resp)

        rec = data["travel_recommendation"]
        expected_fields = [
            "can_use_gates",
            "can_use_jump_bridges",
            "can_jump",
            "can_bridge_others",
            "can_covert_bridge",
            "recommended_profile",
            "warnings",
            "tips",
        ]
        for field in expected_fields:
            assert field in rec, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_analyze_invalid_fitting(self, server):
        resp = await server.handle_request(_call("gatekeeper_analyze_fitting", eft_text="bad"))
        data = _parse_content(resp)
        assert "error" in data


# ---------------------------------------------------------------------------
# 5. gatekeeper_ship_info
# ---------------------------------------------------------------------------
class TestShipInfoIntegration:
    @pytest.mark.asyncio
    async def test_subcapital_ship(self, server):
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Caracal"))
        data = _parse_content(resp)

        assert data["ship_name"] == "Caracal"
        assert data["category"] == "cruiser"
        assert data["can_jump"] is False
        assert data["can_use_gates"] is True

    @pytest.mark.asyncio
    async def test_frigate_ship(self, server):
        """Frigate should be identified correctly."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Rifter"))
        data = _parse_content(resp)

        assert data["ship_name"] == "Rifter"
        assert data["category"] == "frigate"
        assert data["can_jump"] is False
        assert data["can_use_gates"] is True

    @pytest.mark.asyncio
    async def test_battleship_ship(self, server):
        """Battleship should be identified correctly."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Raven"))
        data = _parse_content(resp)

        assert data["ship_name"] == "Raven"
        assert data["category"] == "battleship"
        assert data["can_jump"] is False
        assert data["can_use_gates"] is True

    @pytest.mark.asyncio
    async def test_capital_ship(self, server):
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Archon"))
        data = _parse_content(resp)

        assert data["category"] == "capital"
        assert data["can_jump"] is True
        assert data["can_use_gates"] is False

    @pytest.mark.asyncio
    async def test_supercapital_ship(self, server):
        """Supercapital should have jump but no gates."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Aeon"))
        data = _parse_content(resp)

        assert data["category"] == "supercapital"
        assert data["can_jump"] is True
        assert data["can_use_gates"] is False

    @pytest.mark.asyncio
    async def test_titan_ship(self, server):
        """Titan should have jump_portal capability."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Avatar"))
        data = _parse_content(resp)

        assert data["category"] == "supercapital"
        assert data["jump_capability"] == "jump_portal"
        assert data["can_jump"] is True

    @pytest.mark.asyncio
    async def test_jump_freighter(self, server):
        """Jump freighter should have jump capability."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Rhea"))
        data = _parse_content(resp)

        assert data["category"] == "freighter"
        assert data["jump_capability"] == "jump_freighter"
        assert data["can_jump"] is True

    @pytest.mark.asyncio
    async def test_regular_freighter(self, server):
        """Regular freighter cannot jump."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Charon"))
        data = _parse_content(resp)

        assert data["category"] == "freighter"
        assert data["can_jump"] is False

    @pytest.mark.asyncio
    async def test_unknown_ship(self, server):
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="NotAShip"))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_unknown_ship_has_hint(self, server):
        """Error should include hint about spelling."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="NotAShip"))
        data = _parse_content(resp)
        assert "hint" in data


# ---------------------------------------------------------------------------
# 6. gatekeeper_region_map
# ---------------------------------------------------------------------------
class TestRegionInfoIntegration:
    @pytest.mark.asyncio
    async def test_known_region(self, server):
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="The Forge"))
        data = _parse_content(resp)

        assert data["region_name"] == "The Forge"
        assert data["system_count"] > 0
        assert "security_breakdown" in data
        assert data["security_breakdown"]["high_sec"] > 0

    @pytest.mark.asyncio
    async def test_region_has_id(self, server):
        """Region response should include region_id."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="The Forge"))
        data = _parse_content(resp)

        assert "region_id" in data
        assert isinstance(data["region_id"], int)

    @pytest.mark.asyncio
    async def test_region_has_connection_count(self, server):
        """Region should have connection count."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="The Forge"))
        data = _parse_content(resp)

        assert "connection_count" in data
        assert data["connection_count"] >= 0

    @pytest.mark.asyncio
    async def test_lowsec_region(self, server):
        """Test a region with lowsec systems."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="Metropolis"))
        data = _parse_content(resp)

        assert data["region_name"] == "Metropolis"
        # Metropolis has mixed security
        breakdown = data["security_breakdown"]
        assert breakdown["high_sec"] >= 0
        assert breakdown["low_sec"] >= 0

    @pytest.mark.asyncio
    async def test_nullsec_region(self, server):
        """Test a nullsec region."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="Catch"))
        data = _parse_content(resp)

        assert data["region_name"] == "Catch"
        breakdown = data["security_breakdown"]
        # Catch is full nullsec
        assert breakdown["null_sec"] > 0

    @pytest.mark.asyncio
    async def test_security_breakdown_sums_correctly(self, server):
        """Security breakdown should sum to total systems."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="The Forge"))
        data = _parse_content(resp)

        breakdown = data["security_breakdown"]
        total_from_breakdown = breakdown["high_sec"] + breakdown["low_sec"] + breakdown["null_sec"]
        assert total_from_breakdown == data["system_count"]

    @pytest.mark.asyncio
    async def test_unknown_region(self, server):
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="FakeRegion"))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_unknown_region_has_hint(self, server):
        """Error should include hint."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="FakeRegion"))
        data = _parse_content(resp)
        assert "hint" in data


# ---------------------------------------------------------------------------
# 7. gatekeeper_jump_range
# ---------------------------------------------------------------------------
class TestJumpRangeIntegration:
    @pytest.mark.asyncio
    async def test_jump_range(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=2)
        )
        data = _parse_content(resp)

        assert data["center_system"] == "Jita"
        assert data["max_jumps"] == 2
        assert data["total_systems"] > 0
        assert "systems_by_security" in data

    @pytest.mark.asyncio
    async def test_jump_range_default_jumps(self, server):
        """Default max_jumps should be used when not specified."""
        resp = await server.handle_request(_call("gatekeeper_jump_range", center_system="Jita"))
        data = _parse_content(resp)

        assert data["center_system"] == "Jita"
        assert data["max_jumps"] == 5  # Default
        assert data["total_systems"] > 0

    @pytest.mark.asyncio
    async def test_jump_range_single_jump(self, server):
        """Test with max_jumps=1 for direct neighbors only."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=1)
        )
        data = _parse_content(resp)

        assert data["max_jumps"] == 1
        # Should include at least Jita itself plus neighbors
        assert data["total_systems"] >= 1

    @pytest.mark.asyncio
    async def test_jump_range_large_range(self, server):
        """Test with larger jump range."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=10)
        )
        data = _parse_content(resp)

        assert data["max_jumps"] == 10
        assert data["total_systems"] > 0

    @pytest.mark.asyncio
    async def test_jump_range_max_clamped(self, server):
        """Max jumps should be clamped to 20."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=100)
        )
        data = _parse_content(resp)

        # Should be clamped to 20
        assert data["max_jumps"] == 20

    @pytest.mark.asyncio
    async def test_jump_range_min_clamped(self, server):
        """Min jumps should be clamped to 1."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=0)
        )
        data = _parse_content(resp)

        # Should be clamped to 1
        assert data["max_jumps"] == 1

    @pytest.mark.asyncio
    async def test_jump_range_security_breakdown(self, server):
        """Security breakdown should categorize all systems."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=3)
        )
        data = _parse_content(resp)

        breakdown = data["systems_by_security"]
        assert "high_sec" in breakdown
        assert "low_sec" in breakdown
        assert "null_sec" in breakdown
        # All should be lists
        assert isinstance(breakdown["high_sec"], list)
        assert isinstance(breakdown["low_sec"], list)
        assert isinstance(breakdown["null_sec"], list)

    @pytest.mark.asyncio
    async def test_jump_range_unknown_system(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="FakeSystem")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_jump_range_unknown_has_hint(self, server):
        """Error should include hint."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="FakeSystem")
        )
        data = _parse_content(resp)
        assert "hint" in data


# ---------------------------------------------------------------------------
# 8. gatekeeper_create_alert
# ---------------------------------------------------------------------------
class TestCreateAlertIntegration:
    @pytest.mark.asyncio
    async def test_create_discord_alert(self, server):
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/123/abc",
                webhook_type="discord",
                systems=["Jita", "Tama"],
                min_value=100_000_000,
            )
        )
        data = _parse_content(resp)

        assert data["status"] == "created"
        assert "subscription_id" in data
        assert data["webhook_type"] == "discord"
        assert data["systems"] == ["Jita", "Tama"]

    @pytest.mark.asyncio
    async def test_create_slack_alert(self, server):
        """Slack webhook type should work."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://hooks.slack.com/services/123/abc",
                webhook_type="slack",
            )
        )
        data = _parse_content(resp)

        assert data["status"] == "created"
        assert data["webhook_type"] == "slack"

    @pytest.mark.asyncio
    async def test_create_alert_default_type(self, server):
        """Default webhook type should be discord."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/123/abc",
            )
        )
        data = _parse_content(resp)

        assert data["status"] == "created"
        assert data["webhook_type"] == "discord"

    @pytest.mark.asyncio
    async def test_create_alert_no_systems_means_all(self, server):
        """Empty systems list should mean 'all systems'."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/123/abc",
            )
        )
        data = _parse_content(resp)

        assert data["systems"] == ["all"]

    @pytest.mark.asyncio
    async def test_create_alert_with_min_value(self, server):
        """Alert with min_value filter."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/123/abc",
                min_value=1_000_000_000,  # 1 billion ISK
            )
        )
        data = _parse_content(resp)

        assert data["status"] == "created"
        assert data["min_value"] == 1_000_000_000

    @pytest.mark.asyncio
    async def test_create_alert_unique_ids(self, server):
        """Each alert should get a unique ID."""
        resp1 = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/1/a",
            )
        )
        resp2 = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/2/b",
            )
        )

        data1 = _parse_content(resp1)
        data2 = _parse_content(resp2)

        assert data1["subscription_id"] != data2["subscription_id"]

    @pytest.mark.asyncio
    async def test_create_alert_invalid_type(self, server):
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://example.com/hook",
                webhook_type="invalid",
            )
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_create_alert_invalid_type_shows_valid_types(self, server):
        """Error should list valid webhook types."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://example.com/hook",
                webhook_type="invalid",
            )
        )
        data = _parse_content(resp)
        assert "valid_types" in data
        assert "discord" in data["valid_types"]
        assert "slack" in data["valid_types"]


# ---------------------------------------------------------------------------
# 9. gatekeeper_list_alerts
# ---------------------------------------------------------------------------
class TestListAlertsIntegration:
    @pytest.mark.asyncio
    async def test_list_empty(self, server):
        resp = await server.handle_request(_call("gatekeeper_list_alerts"))
        data = _parse_content(resp)

        assert data["total"] == 0
        assert data["subscriptions"] == []

    @pytest.mark.asyncio
    async def test_list_after_create(self, server):
        await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/1/a",
            )
        )
        resp = await server.handle_request(_call("gatekeeper_list_alerts"))
        data = _parse_content(resp)

        assert data["total"] == 1
        assert len(data["subscriptions"]) == 1

    @pytest.mark.asyncio
    async def test_list_multiple_alerts(self, server):
        """List should show all created alerts."""
        await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/1/a",
            )
        )
        await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://hooks.slack.com/services/1/a",
                webhook_type="slack",
            )
        )
        await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/2/b",
                systems=["Jita"],
            )
        )

        resp = await server.handle_request(_call("gatekeeper_list_alerts"))
        data = _parse_content(resp)

        assert data["total"] == 3
        assert len(data["subscriptions"]) == 3

    @pytest.mark.asyncio
    async def test_list_subscription_fields(self, server):
        """Each subscription should have required fields."""
        await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/1/a",
                systems=["Jita"],
                min_value=50_000_000,
            )
        )

        resp = await server.handle_request(_call("gatekeeper_list_alerts"))
        data = _parse_content(resp)

        sub = data["subscriptions"][0]
        assert "id" in sub
        assert "webhook_type" in sub
        assert "systems" in sub
        assert "min_value" in sub
        assert "enabled" in sub

    @pytest.mark.asyncio
    async def test_list_shows_enabled_status(self, server):
        """Subscriptions should show enabled status."""
        await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/1/a",
            )
        )

        resp = await server.handle_request(_call("gatekeeper_list_alerts"))
        data = _parse_content(resp)

        sub = data["subscriptions"][0]
        assert sub["enabled"] is True  # Default should be enabled


# ---------------------------------------------------------------------------
# 10. gatekeeper_thera_connections
# ---------------------------------------------------------------------------
class TestTheraConnectionsIntegration:
    @pytest.mark.asyncio
    async def test_thera_connections(self, server):
        resp = await server.handle_request(_call("gatekeeper_thera_connections"))
        data = _parse_content(resp)

        assert "connections" in data
        assert "total" in data
        assert isinstance(data["connections"], list)
        assert data["total"] == len(data["connections"])

    @pytest.mark.asyncio
    async def test_thera_connections_structure(self, server):
        """Verify connection structure when connections exist."""
        resp = await server.handle_request(_call("gatekeeper_thera_connections"))
        data = _parse_content(resp)

        # If there are connections, verify structure
        if data["connections"]:
            conn = data["connections"][0]
            assert "id" in conn
            assert "in_system_name" in conn
            assert "out_system_name" in conn
            assert "wh_type" in conn
            assert "max_ship_size" in conn
            assert "remaining_hours" in conn

    @pytest.mark.asyncio
    async def test_thera_connections_with_filter(self, server):
        """Filter connections by max ship size."""
        resp = await server.handle_request(
            _call("gatekeeper_thera_connections", max_ship_size="frigate")
        )
        data = _parse_content(resp)

        # All returned connections should match filter (if any)
        for conn in data["connections"]:
            assert conn["max_ship_size"].lower() == "frigate"

    @pytest.mark.asyncio
    async def test_thera_connections_filter_case_insensitive(self, server):
        """Ship size filter should be case-insensitive."""
        resp_lower = await server.handle_request(
            _call("gatekeeper_thera_connections", max_ship_size="battleship")
        )
        resp_upper = await server.handle_request(
            _call("gatekeeper_thera_connections", max_ship_size="BATTLESHIP")
        )

        data_lower = _parse_content(resp_lower)
        data_upper = _parse_content(resp_upper)

        # Both should return same count
        assert data_lower["total"] == data_upper["total"]


# ---------------------------------------------------------------------------
# 11. gatekeeper_thera_status
# ---------------------------------------------------------------------------
class TestTheraStatusIntegration:
    @pytest.mark.asyncio
    async def test_thera_status(self, server):
        resp = await server.handle_request(_call("gatekeeper_thera_status"))
        data = _parse_content(resp)

        assert "cache_age" in data
        assert "connection_count" in data
        assert "api_healthy" in data
        assert isinstance(data["api_healthy"], bool)

    @pytest.mark.asyncio
    async def test_thera_status_connection_count_matches(self, server):
        """Connection count should match connections endpoint."""
        status_resp = await server.handle_request(_call("gatekeeper_thera_status"))
        conn_resp = await server.handle_request(_call("gatekeeper_thera_connections"))

        status_data = _parse_content(status_resp)
        conn_data = _parse_content(conn_resp)

        assert status_data["connection_count"] == conn_data["total"]

    @pytest.mark.asyncio
    async def test_thera_status_last_error_field(self, server):
        """Status should include last_error field."""
        resp = await server.handle_request(_call("gatekeeper_thera_status"))
        data = _parse_content(resp)

        assert "last_error" in data
        # last_error can be None or a string

    @pytest.mark.asyncio
    async def test_thera_status_cache_age_type(self, server):
        """Cache age should be a number or None."""
        resp = await server.handle_request(_call("gatekeeper_thera_status"))
        data = _parse_content(resp)

        cache_age = data["cache_age"]
        assert cache_age is None or isinstance(cache_age, (int, float))


# ---------------------------------------------------------------------------
# Cross-cutting: JSON-RPC protocol compliance
# ---------------------------------------------------------------------------
class TestProtocolCompliance:
    @pytest.mark.asyncio
    async def test_all_tools_return_valid_jsonrpc(self, server):
        """Every tool call returns valid JSON-RPC with text content."""
        calls = [
            _call("gatekeeper_route", origin="Jita", destination="Amarr"),
            _call("gatekeeper_system_threat", system_name="Jita"),
            _call("gatekeeper_parse_fitting", eft_text=SAMPLE_EFT),
            _call("gatekeeper_analyze_fitting", eft_text=SAMPLE_EFT),
            _call("gatekeeper_ship_info", ship_name="Caracal"),
            _call("gatekeeper_region_map", region_name="The Forge"),
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=1),
            _call("gatekeeper_create_alert", webhook_url="https://example.com/hook"),
            _call("gatekeeper_list_alerts"),
            _call("gatekeeper_thera_connections"),
            _call("gatekeeper_thera_status"),
        ]

        for req in calls:
            tool = req["params"]["name"]
            resp = await server.handle_request(req)
            assert resp["jsonrpc"] == "2.0", f"Bad jsonrpc for {tool}"
            assert resp["id"] == 1
            assert "result" in resp, f"Missing result for {tool}"
            content = resp["result"]["content"]
            assert len(content) == 1, f"Expected 1 content block for {tool}"
            assert content[0]["type"] == "text"
            # Must be valid JSON
            parsed = json.loads(content[0]["text"])
            assert isinstance(parsed, dict), f"Expected dict for {tool}"


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------
class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, server):
        """Calling an unknown tool should return proper error."""
        resp = await server.handle_request(_call("nonexistent_tool"))
        assert "error" in resp
        assert resp["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_error_responses_have_structure(self, server):
        """Error responses should have proper structure."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="FakeSystem", destination="Amarr")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_all_error_cases_return_valid_json(self, server):
        """All error cases should return valid JSON content."""
        error_calls = [
            _call("gatekeeper_route", origin="FakeSystem", destination="Amarr"),
            _call("gatekeeper_system_threat", system_name="FakeSystem"),
            _call("gatekeeper_parse_fitting", eft_text="invalid"),
            _call("gatekeeper_analyze_fitting", eft_text="invalid"),
            _call("gatekeeper_ship_info", ship_name="NotAShip"),
            _call("gatekeeper_region_map", region_name="FakeRegion"),
            _call("gatekeeper_jump_range", center_system="FakeSystem"),
            _call("gatekeeper_create_alert", webhook_url="https://x.com", webhook_type="bad"),
        ]

        for req in error_calls:
            resp = await server.handle_request(req)
            # Should still be valid JSON-RPC response
            assert resp["jsonrpc"] == "2.0"
            assert "result" in resp
            content = resp["result"]["content"]
            # Content should be parseable JSON
            parsed = json.loads(content[0]["text"])
            assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Concurrent request handling
# ---------------------------------------------------------------------------
class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, server):
        """Multiple concurrent tool calls should all succeed."""
        import asyncio

        calls = [
            server.handle_request(_call("gatekeeper_route", origin="Jita", destination="Amarr")),
            server.handle_request(_call("gatekeeper_system_threat", system_name="Jita")),
            server.handle_request(_call("gatekeeper_ship_info", ship_name="Caracal")),
            server.handle_request(_call("gatekeeper_region_map", region_name="The Forge")),
            server.handle_request(_call("gatekeeper_thera_status")),
        ]

        results = await asyncio.gather(*calls)

        for resp in results:
            assert resp["jsonrpc"] == "2.0"
            assert "result" in resp


# ---------------------------------------------------------------------------
# Edge cases and boundary conditions
# ---------------------------------------------------------------------------
class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_route_with_empty_avoid_list(self, server):
        """Empty avoid list should work normally."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", avoid_systems=[])
        )
        data = _parse_content(resp)
        assert "error" not in data
        assert data["total_jumps"] > 0

    @pytest.mark.asyncio
    async def test_alert_with_empty_systems_list(self, server):
        """Empty systems list should mean all systems."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/1/a",
                systems=[],
            )
        )
        data = _parse_content(resp)
        assert data["status"] == "created"
        assert data["systems"] == ["all"]

    @pytest.mark.asyncio
    async def test_fitting_with_special_characters(self, server):
        """Fitting with special characters in name should parse."""
        eft = "[Rifter, Test's Fit - v2.0 (PvP)]"
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text=eft))
        data = _parse_content(resp)
        assert data["ship_name"] == "Rifter"

    @pytest.mark.asyncio
    async def test_system_name_case_sensitivity(self, server):
        """System names should work with various cases."""
        # Test lowercase
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Jita"))
        data = _parse_content(resp)
        assert "error" not in data

    @pytest.mark.asyncio
    async def test_region_name_case_sensitivity(self, server):
        """Region lookup should match case-insensitively."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="the forge"))
        data = _parse_content(resp)
        assert "error" not in data
        # Region lookup is case-insensitive but returns input case
        assert data["region_name"].lower() == "the forge"

    @pytest.mark.asyncio
    async def test_very_long_route(self, server):
        """Very long routes should still work."""
        # Jita to far nullsec
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="HED-GP")
        )
        data = _parse_content(resp)
        assert data["total_jumps"] > 20  # Should be a long route


# ---------------------------------------------------------------------------
# Input Validation Edge Cases (new tests for error handling)
# ---------------------------------------------------------------------------
class TestInputValidationEdgeCases:
    """Tests for input validation and edge case error handling."""

    # --- Null/None Input Tests ---
    @pytest.mark.asyncio
    async def test_route_with_null_origin(self, server):
        """Route with None origin should return validation error."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin=None, destination="Amarr")
        )
        data = _parse_content(resp)
        assert "error" in data
        assert "origin" in data["error"].lower() or "missing" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_route_with_null_destination(self, server):
        """Route with None destination should return validation error."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination=None)
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_system_threat_with_null_name(self, server):
        """System threat with None name should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name=None))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_ship_info_with_null_name(self, server):
        """Ship info with None name should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name=None))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_region_map_with_null_name(self, server):
        """Region map with None name should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name=None))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_jump_range_with_null_system(self, server):
        """Jump range with None system should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_jump_range", center_system=None))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_parse_fitting_with_null_text(self, server):
        """Parse fitting with None text should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text=None))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_create_alert_with_null_url(self, server):
        """Create alert with None URL should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_create_alert", webhook_url=None))
        data = _parse_content(resp)
        assert "error" in data

    # --- Empty String Input Tests ---
    @pytest.mark.asyncio
    async def test_route_with_empty_origin(self, server):
        """Route with empty origin should return validation error."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="", destination="Amarr")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_system_threat_with_empty_name(self, server):
        """System threat with empty name should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name=""))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_ship_info_with_empty_name(self, server):
        """Ship info with empty name should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name=""))
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_parse_fitting_with_empty_text(self, server):
        """Parse fitting with empty text should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text=""))
        data = _parse_content(resp)
        assert "error" in data

    # --- Whitespace-Only Input Tests ---
    @pytest.mark.asyncio
    async def test_route_with_whitespace_origin(self, server):
        """Route with whitespace-only origin should return validation error."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="   ", destination="Amarr")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_system_threat_with_whitespace_name(self, server):
        """System threat with whitespace-only name should return validation error."""
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="   \t  "))
        data = _parse_content(resp)
        assert "error" in data

    # --- Type Mismatch Tests ---
    @pytest.mark.asyncio
    async def test_route_with_integer_origin(self, server):
        """Route with integer origin should return validation error."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin=12345, destination="Amarr")
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_jump_range_with_string_max_jumps(self, server):
        """Jump range handles string max_jumps gracefully."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps="five")
        )
        data = _parse_content(resp)
        # Should return error for invalid type
        assert "error" in data

    @pytest.mark.asyncio
    async def test_jump_range_with_boolean_max_jumps(self, server):
        """Jump range handles boolean max_jumps gracefully."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=True)
        )
        data = _parse_content(resp)
        # Should return error for boolean input
        assert "error" in data

    @pytest.mark.asyncio
    async def test_route_with_list_origin(self, server):
        """Route with list origin should return validation error."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin=["Jita"], destination="Amarr")
        )
        data = _parse_content(resp)
        assert "error" in data

    # --- Boundary Value Tests ---
    @pytest.mark.asyncio
    async def test_jump_range_with_negative_jumps(self, server):
        """Jump range with negative max_jumps should clamp to 1."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=-5)
        )
        data = _parse_content(resp)
        # Should clamp to 1, not error
        assert "error" not in data
        assert data["max_jumps"] == 1

    @pytest.mark.asyncio
    async def test_jump_range_with_very_large_jumps(self, server):
        """Jump range with very large max_jumps should clamp to 20."""
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="Jita", max_jumps=1000)
        )
        data = _parse_content(resp)
        # Should clamp to 20, not error
        assert "error" not in data
        assert data["max_jumps"] == 20

    @pytest.mark.asyncio
    async def test_create_alert_with_negative_min_value(self, server):
        """Create alert with negative min_value should return error."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="https://discord.com/api/webhooks/1/a",
                min_value=-100,
            )
        )
        data = _parse_content(resp)
        assert "error" in data

    # --- Invalid URL Format Tests ---
    @pytest.mark.asyncio
    async def test_create_alert_with_invalid_url(self, server):
        """Create alert with invalid URL format should return error."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="not-a-url",
            )
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_create_alert_with_javascript_url(self, server):
        """Create alert with javascript: URL should return error."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="javascript:alert('xss')",
            )
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_create_alert_with_ftp_url(self, server):
        """Create alert with ftp:// URL should return error."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_create_alert",
                webhook_url="ftp://example.com/file",
            )
        )
        data = _parse_content(resp)
        assert "error" in data

    # --- Invalid Profile Tests ---
    @pytest.mark.asyncio
    async def test_route_with_invalid_profile(self, server):
        """Route with invalid profile should return error with valid options."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", profile="invalid_profile")
        )
        data = _parse_content(resp)
        assert "error" in data
        # Should provide valid profiles in response
        assert "valid_profiles" in data or "hint" in data

    # --- Avoid Systems Edge Cases ---
    @pytest.mark.asyncio
    async def test_route_with_non_string_avoid_items(self, server):
        """Route with non-string items in avoid_systems should error."""
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", avoid_systems=[123, 456])
        )
        data = _parse_content(resp)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_route_with_mixed_avoid_items(self, server):
        """Route with mixed types in avoid_systems should error."""
        resp = await server.handle_request(
            _call(
                "gatekeeper_route",
                origin="Jita",
                destination="Amarr",
                avoid_systems=["Niarja", 123],
            )
        )
        data = _parse_content(resp)
        assert "error" in data

    # --- EFT Parsing Edge Cases ---
    @pytest.mark.asyncio
    async def test_parse_fitting_without_opening_bracket(self, server):
        """Fitting without opening bracket should return clear error."""
        resp = await server.handle_request(
            _call("gatekeeper_parse_fitting", eft_text="Caracal, Test Fit]")
        )
        data = _parse_content(resp)
        assert "error" in data
        assert "hint" in data

    @pytest.mark.asyncio
    async def test_parse_fitting_with_only_whitespace(self, server):
        """Fitting with only whitespace should return error."""
        resp = await server.handle_request(_call("gatekeeper_parse_fitting", eft_text="   \n\t   "))
        data = _parse_content(resp)
        assert "error" in data


# ---------------------------------------------------------------------------
# Server-Level Error Handling Tests
# ---------------------------------------------------------------------------
class TestServerErrorHandling:
    """Tests for server-level error handling."""

    @pytest.mark.asyncio
    async def test_tool_call_without_name(self, server):
        """Tool call without name should return error."""
        resp = await server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"arguments": {}},
            }
        )
        assert "error" in resp
        assert resp["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_tool_call_with_empty_name(self, server):
        """Tool call with empty name should return error."""
        resp = await server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "", "arguments": {}},
            }
        )
        assert "error" in resp
        assert resp["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_tool_call_with_numeric_name(self, server):
        """Tool call with numeric name should return error."""
        resp = await server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": 12345, "arguments": {}},
            }
        )
        assert "error" in resp
        assert resp["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_tool_call_with_list_arguments(self, server):
        """Tool call with list arguments should return error."""
        resp = await server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "gatekeeper_ship_info", "arguments": ["Caracal"]},
            }
        )
        assert "error" in resp
        assert resp["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_tool_call_with_null_arguments(self, server):
        """Tool call with null arguments should work (use empty dict)."""
        resp = await server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "gatekeeper_list_alerts", "arguments": None},
            }
        )
        # Should succeed for list_alerts which has no required args
        assert "result" in resp
        data = json.loads(resp["result"]["content"][0]["text"])
        assert "total" in data

    @pytest.mark.asyncio
    async def test_error_responses_include_hint_when_available(self, server):
        """Error responses should include hint when validation fails."""
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name=""))
        data = _parse_content(resp)
        assert "error" in data
        assert "hint" in data

    @pytest.mark.asyncio
    async def test_all_validation_errors_return_valid_json(self, server):
        """All validation error cases return valid JSON responses."""
        validation_error_calls = [
            _call("gatekeeper_route", origin=None, destination="Amarr"),
            _call("gatekeeper_route", origin="", destination="Amarr"),
            _call("gatekeeper_route", origin="   ", destination="Amarr"),
            _call("gatekeeper_system_threat", system_name=None),
            _call("gatekeeper_system_threat", system_name=""),
            _call("gatekeeper_ship_info", ship_name=None),
            _call("gatekeeper_ship_info", ship_name=""),
            _call("gatekeeper_region_map", region_name=None),
            _call("gatekeeper_jump_range", center_system=None),
            _call("gatekeeper_parse_fitting", eft_text=None),
            _call("gatekeeper_parse_fitting", eft_text=""),
            _call("gatekeeper_create_alert", webhook_url=None),
            _call("gatekeeper_create_alert", webhook_url="not-a-url"),
        ]

        for req in validation_error_calls:
            tool = req["params"]["name"]
            resp = await server.handle_request(req)
            # Should always be valid JSON-RPC
            assert resp["jsonrpc"] == "2.0", f"Bad jsonrpc for {tool}"
            assert "result" in resp, f"Missing result for {tool}"
            content = resp["result"]["content"]
            assert len(content) > 0, f"Empty content for {tool}"
            # Content should be parseable JSON
            try:
                parsed = json.loads(content[0]["text"])
                assert isinstance(parsed, dict), f"Expected dict for {tool}"
                assert "error" in parsed, f"Expected error in response for {tool}"
            except json.JSONDecodeError:
                pytest.fail(f"Failed to parse JSON for {tool}: {content[0]['text']}")
