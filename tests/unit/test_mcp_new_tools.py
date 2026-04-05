"""
Tests for new MCP tools: kill_stats, hot_systems, system_neighbors,
external_links, submit_intel, and calculate_fatigue.

Tests both the server integration (tool registration, schemas, routing)
and the tool implementation functions.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.mcp.server import MCPServer
from backend.app.mcp.tools import (
    calculate_fatigue,
    get_external_links,
    get_hot_systems,
    get_kill_stats,
    get_system_neighbors,
    submit_intel,
)


@pytest.fixture
def server():
    """Create a fresh MCP server instance."""
    return MCPServer()


# =============================================================================
# Server Registration Tests
# =============================================================================


class TestNewToolsRegistered:
    """Verify that all 6 new tools are registered in the server."""

    def test_kill_stats_registered(self, server):
        """gatekeeper_kill_stats should be registered."""
        assert "gatekeeper_kill_stats" in server.tools

    def test_hot_systems_registered(self, server):
        """gatekeeper_hot_systems should be registered."""
        assert "gatekeeper_hot_systems" in server.tools

    def test_system_neighbors_registered(self, server):
        """gatekeeper_system_neighbors should be registered."""
        assert "gatekeeper_system_neighbors" in server.tools

    def test_external_links_registered(self, server):
        """gatekeeper_external_links should be registered."""
        assert "gatekeeper_external_links" in server.tools

    def test_submit_intel_registered(self, server):
        """gatekeeper_submit_intel should be registered."""
        assert "gatekeeper_submit_intel" in server.tools

    def test_calculate_fatigue_registered(self, server):
        """gatekeeper_calculate_fatigue should be registered."""
        assert "gatekeeper_calculate_fatigue" in server.tools

    def test_total_tool_count(self, server):
        """Server should now have 17 tools (11 original + 6 new)."""
        assert len(server.tools) == 17

    def test_version_bumped(self, server):
        """Version should be 1.3.0."""
        from backend.app.mcp.server import VERSION

        assert VERSION == "1.3.0"


# =============================================================================
# Tool Schema Tests
# =============================================================================


class TestNewToolSchemas:
    """Verify input schemas are correctly defined for new tools."""

    def test_kill_stats_schema(self, server):
        """Kill stats tool should require system_name and have optional hours."""
        tool = server.tools["gatekeeper_kill_stats"]
        schema = tool["inputSchema"]

        assert schema["type"] == "object"
        assert "system_name" in schema["properties"]
        assert "hours" in schema["properties"]
        assert "system_name" in schema["required"]
        assert schema["properties"]["hours"]["minimum"] == 1
        assert schema["properties"]["hours"]["maximum"] == 168

    def test_hot_systems_schema(self, server):
        """Hot systems tool should have optional hours and limit."""
        tool = server.tools["gatekeeper_hot_systems"]
        schema = tool["inputSchema"]

        assert schema["type"] == "object"
        assert "hours" in schema["properties"]
        assert "limit" in schema["properties"]
        # No required fields
        assert "required" not in schema or len(schema.get("required", [])) == 0

    def test_system_neighbors_schema(self, server):
        """System neighbors tool should require system_name."""
        tool = server.tools["gatekeeper_system_neighbors"]
        schema = tool["inputSchema"]

        assert "system_name" in schema["properties"]
        assert "system_name" in schema["required"]

    def test_external_links_schema(self, server):
        """External links tool should require system_name."""
        tool = server.tools["gatekeeper_external_links"]
        schema = tool["inputSchema"]

        assert "system_name" in schema["properties"]
        assert "system_name" in schema["required"]

    def test_submit_intel_schema(self, server):
        """Submit intel tool should require text."""
        tool = server.tools["gatekeeper_submit_intel"]
        schema = tool["inputSchema"]

        assert "text" in schema["properties"]
        assert "text" in schema["required"]

    def test_calculate_fatigue_schema(self, server):
        """Calculate fatigue tool should require light_years and have optional fatigue."""
        tool = server.tools["gatekeeper_calculate_fatigue"]
        schema = tool["inputSchema"]

        assert "light_years" in schema["properties"]
        assert "current_fatigue_minutes" in schema["properties"]
        assert "light_years" in schema["required"]
        assert schema["properties"]["light_years"]["minimum"] == 0.1
        assert schema["properties"]["light_years"]["maximum"] == 500.0

    def test_all_new_tools_have_required_fields(self, server):
        """All new tools should have name, description, and inputSchema."""
        new_tools = [
            "gatekeeper_kill_stats",
            "gatekeeper_hot_systems",
            "gatekeeper_system_neighbors",
            "gatekeeper_external_links",
            "gatekeeper_submit_intel",
            "gatekeeper_calculate_fatigue",
        ]
        for tool_name in new_tools:
            tool = server.tools[tool_name]
            assert "name" in tool, f"{tool_name} missing 'name'"
            assert "description" in tool, f"{tool_name} missing 'description'"
            assert "inputSchema" in tool, f"{tool_name} missing 'inputSchema'"
            assert tool["name"] == tool_name


# =============================================================================
# get_kill_stats Tests
# =============================================================================


class TestGetKillStats:
    """Tests for the get_kill_stats tool function."""

    @pytest.mark.asyncio
    async def test_missing_system_name(self):
        """Should return validation error when system_name is missing."""
        result = await get_kill_stats(system_name=None)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_empty_system_name(self):
        """Should return validation error for empty system_name."""
        result = await get_kill_stats(system_name="")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_hours_type(self):
        """Should handle invalid hours type gracefully."""
        result = await get_kill_stats(system_name="Jita", hours=True)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_hours_clamped_to_bounds(self):
        """Hours should be clamped to valid range."""
        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_universe.systems = {"Jita": mock_system}

        mock_stats = MagicMock()
        mock_stats.recent_kills = 5
        mock_stats.recent_pods = 2

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_system_kills",
                new_callable=AsyncMock,
                return_value=mock_stats,
            ),
        ):
            result = await get_kill_stats(system_name="Jita", hours=999)
            # Clamped to 168
            assert result["hours"] == 168

    @pytest.mark.asyncio
    async def test_unknown_system(self):
        """Should return error for unknown system name."""
        mock_universe = MagicMock()
        mock_universe.systems = {}

        with patch("backend.app.mcp.tools.load_universe", return_value=mock_universe):
            result = await get_kill_stats(system_name="FakeSystem")
            assert "error" in result
            assert "Unknown system" in result["error"]

    @pytest.mark.asyncio
    async def test_successful_kill_stats(self):
        """Should return kill stats for a valid system."""
        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_universe.systems = {"Jita": mock_system}

        mock_stats = MagicMock()
        mock_stats.recent_kills = 10
        mock_stats.recent_pods = 3

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_system_kills",
                new_callable=AsyncMock,
                return_value=mock_stats,
            ),
        ):
            result = await get_kill_stats(system_name="Jita", hours=24)

            assert result["system_name"] == "Jita"
            assert result["system_id"] == 30000142
            assert result["hours"] == 24
            assert result["kills"] == 10
            assert result["pods"] == 3
            assert result["total"] == 13

    @pytest.mark.asyncio
    async def test_fetch_failure(self):
        """Should return error when zKillboard API fails."""
        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_universe.systems = {"Jita": mock_system}

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_system_kills",
                new_callable=AsyncMock,
                side_effect=Exception("API timeout"),
            ),
        ):
            result = await get_kill_stats(system_name="Jita")
            assert "error" in result
            assert "Failed to fetch kill stats" in result["error"]

    @pytest.mark.asyncio
    async def test_via_server(self, server):
        """Should work through the MCP server tool call interface."""
        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_universe.systems = {"Jita": mock_system}

        mock_stats = MagicMock()
        mock_stats.recent_kills = 5
        mock_stats.recent_pods = 1

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_system_kills",
                new_callable=AsyncMock,
                return_value=mock_stats,
            ),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "gatekeeper_kill_stats",
                    "arguments": {"system_name": "Jita"},
                },
            }
            response = await server.handle_request(request)

            assert response["id"] == 1
            assert "result" in response
            assert "content" in response["result"]
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["system_name"] == "Jita"
            assert content["kills"] == 5


# =============================================================================
# get_hot_systems Tests
# =============================================================================


class TestGetHotSystems:
    """Tests for the get_hot_systems tool function."""

    @pytest.mark.asyncio
    async def test_invalid_hours_type(self):
        """Should return validation error for boolean hours."""
        result = await get_hot_systems(hours=True)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_successful_hot_systems(self):
        """Should return ranked hot systems."""
        mock_universe = MagicMock()
        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.security = 0.9
        mock_tama = MagicMock()
        mock_tama.id = 30002813
        mock_tama.security = 0.3
        mock_universe.systems = {"Jita": mock_jita, "Tama": mock_tama}

        mock_stats_jita = MagicMock()
        mock_stats_jita.recent_kills = 5
        mock_stats_jita.recent_pods = 2
        mock_stats_tama = MagicMock()
        mock_stats_tama.recent_kills = 20
        mock_stats_tama.recent_pods = 10

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value={30000142: mock_stats_jita, 30002813: mock_stats_tama},
            ),
        ):
            result = await get_hot_systems(hours=24, limit=5)

            assert "systems" in result
            assert result["hours"] == 24
            # Tama should be first (more kills)
            assert result["systems"][0]["system_name"] == "Tama"
            assert result["systems"][0]["total"] == 30

    @pytest.mark.asyncio
    async def test_limit_applied(self):
        """Should respect the limit parameter."""
        mock_universe = MagicMock()
        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.security = 0.9
        mock_universe.systems = {"Jita": mock_jita}

        mock_stats = MagicMock()
        mock_stats.recent_kills = 5
        mock_stats.recent_pods = 2

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value={30000142: mock_stats},
            ),
        ):
            result = await get_hot_systems(hours=24, limit=1)
            assert result["total_systems"] <= 1

    @pytest.mark.asyncio
    async def test_default_parameters(self):
        """Should use default hours=24 and limit=10."""
        mock_universe = MagicMock()
        mock_universe.systems = {}

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            result = await get_hot_systems()
            assert result["hours"] == 24

    @pytest.mark.asyncio
    async def test_fetch_failure(self):
        """Should return error when API fails."""
        mock_universe = MagicMock()
        mock_universe.systems = {}

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                side_effect=Exception("API error"),
            ),
        ):
            result = await get_hot_systems()
            assert "error" in result


# =============================================================================
# get_system_neighbors Tests
# =============================================================================


class TestGetSystemNeighbors:
    """Tests for the get_system_neighbors tool function."""

    def test_missing_system_name(self):
        """Should return validation error when system_name is missing."""
        result = get_system_neighbors(system_name=None)
        assert "error" in result

    def test_empty_system_name(self):
        """Should return validation error for empty system_name."""
        result = get_system_neighbors(system_name="  ")
        assert "error" in result

    def test_unknown_system(self):
        """Should return error for unknown system."""
        mock_universe = MagicMock()
        mock_universe.systems = {}

        with patch("backend.app.mcp.tools.load_universe", return_value=mock_universe):
            result = get_system_neighbors(system_name="FakeSystem")
            assert "error" in result
            assert "Unknown system" in result["error"]

    def test_successful_neighbors(self):
        """Should return list of neighboring systems with security info."""
        mock_universe = MagicMock()
        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.security = 0.9
        mock_jita.region_name = "The Forge"

        mock_perimeter = MagicMock()
        mock_perimeter.id = 30000144
        mock_perimeter.security = 0.9
        mock_perimeter.region_name = "The Forge"

        mock_new_caldari = MagicMock()
        mock_new_caldari.id = 30000145
        mock_new_caldari.security = 1.0
        mock_new_caldari.region_name = "The Forge"

        mock_universe.systems = {
            "Jita": mock_jita,
            "Perimeter": mock_perimeter,
            "New Caldari": mock_new_caldari,
        }

        mock_gate1 = MagicMock()
        mock_gate1.from_system = "Jita"
        mock_gate1.to_system = "Perimeter"

        mock_gate2 = MagicMock()
        mock_gate2.from_system = "Jita"
        mock_gate2.to_system = "New Caldari"

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.get_neighbors",
                return_value=[mock_gate1, mock_gate2],
            ),
        ):
            result = get_system_neighbors(system_name="Jita")

            assert result["system_name"] == "Jita"
            assert result["neighbor_count"] == 2
            assert len(result["neighbors"]) == 2

            # Check first neighbor has required fields
            neighbor_names = [n["system_name"] for n in result["neighbors"]]
            assert "Perimeter" in neighbor_names
            assert "New Caldari" in neighbor_names

            for neighbor in result["neighbors"]:
                assert "security" in neighbor
                assert "security_level" in neighbor
                assert "region_name" in neighbor

    def test_via_server(self, server):
        """Should work through the MCP server tool call interface."""
        mock_universe = MagicMock()
        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.security = 0.9
        mock_jita.region_name = "The Forge"
        mock_universe.systems = {"Jita": mock_jita}

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.get_neighbors",
                return_value=[],
            ),
        ):
            import asyncio

            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "gatekeeper_system_neighbors",
                    "arguments": {"system_name": "Jita"},
                },
            }
            response = asyncio.get_event_loop().run_until_complete(server.handle_request(request))

            assert response["id"] == 2
            assert "result" in response
            assert "content" in response["result"]


# =============================================================================
# get_external_links Tests
# =============================================================================


class TestGetExternalLinks:
    """Tests for the get_external_links tool function."""

    def test_missing_system_name(self):
        """Should return validation error when system_name is missing."""
        result = get_external_links(system_name=None)
        assert "error" in result

    def test_empty_system_name(self):
        """Should return validation error for empty system_name."""
        result = get_external_links(system_name="")
        assert "error" in result

    def test_successful_links(self):
        """Should return links dict for a valid system."""
        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_system.region_name = "The Forge"
        mock_system.region_id = 10000002
        mock_universe.systems = {"Jita": mock_system}

        with patch("backend.app.mcp.tools.load_universe", return_value=mock_universe):
            result = get_external_links(system_name="Jita")

            assert result["system_name"] == "Jita"
            assert result["system_id"] == 30000142
            assert "links" in result
            assert "dotlan" in result["links"]
            assert "zkillboard" in result["links"]
            assert "eveeye" in result["links"]

    def test_links_contain_urls(self):
        """Links should contain valid URLs."""
        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_system.region_name = "The Forge"
        mock_system.region_id = 10000002
        mock_universe.systems = {"Jita": mock_system}

        with patch("backend.app.mcp.tools.load_universe", return_value=mock_universe):
            result = get_external_links(system_name="Jita")

            for link_name, url in result["links"].items():
                assert url.startswith("https://"), f"Link {link_name} should start with https://"

    def test_system_not_in_universe(self):
        """Should still generate links even if system is not in universe data."""
        mock_universe = MagicMock()
        mock_universe.systems = MagicMock()
        mock_universe.systems.get.return_value = None
        mock_universe.systems.__contains__ = lambda self, key: False

        with patch("backend.app.mcp.tools.load_universe", return_value=mock_universe):
            result = get_external_links(system_name="UnknownSystem")

            assert result["system_name"] == "UnknownSystem"
            assert "links" in result
            # Dotlan works without system ID
            assert "dotlan" in result["links"]


# =============================================================================
# submit_intel Tests
# =============================================================================


class TestSubmitIntel:
    """Tests for the submit_intel tool function."""

    def test_missing_text(self):
        """Should return validation error when text is missing."""
        result = submit_intel(text=None)
        assert "error" in result

    def test_empty_text(self):
        """Should return validation error for empty text."""
        result = submit_intel(text="")
        assert "error" in result

    def test_whitespace_only_text(self):
        """Should return validation error for whitespace-only text."""
        result = submit_intel(text="   ")
        assert "error" in result

    def test_successful_intel_parse(self):
        """Should parse intel text and return reports."""
        mock_report = MagicMock()
        mock_report.system_name = "Tama"
        mock_report.hostile_count = 3
        mock_report.hostile_names = []
        mock_report.is_clear = False
        mock_report.threat_type = MagicMock()
        mock_report.threat_type.value = "hostile"
        mock_report.ship_types = []
        mock_report.direction = None
        mock_report.raw_text = "Tama +3"

        with patch("backend.app.mcp.tools._submit_intel", return_value=[mock_report]):
            result = submit_intel(text="Tama +3")

            assert result["reports_parsed"] == 1
            assert len(result["reports"]) == 1
            assert result["reports"][0]["system_name"] == "Tama"
            assert result["reports"][0]["hostile_count"] == 3
            assert "Tama" in result["hostile_systems"]

    def test_clear_report_not_in_hostile_systems(self):
        """Clear reports should not add systems to hostile list."""
        mock_report = MagicMock()
        mock_report.system_name = "Jita"
        mock_report.hostile_count = 0
        mock_report.hostile_names = []
        mock_report.is_clear = True
        mock_report.threat_type = MagicMock()
        mock_report.threat_type.value = "hostile"
        mock_report.ship_types = []
        mock_report.direction = None
        mock_report.raw_text = "Jita clear"

        with patch("backend.app.mcp.tools._submit_intel", return_value=[mock_report]):
            result = submit_intel(text="Jita clear")

            assert result["reports_parsed"] == 1
            assert "Jita" not in result["hostile_systems"]

    def test_multi_line_intel(self):
        """Should handle multi-line intel text."""
        mock_report1 = MagicMock()
        mock_report1.system_name = "Tama"
        mock_report1.hostile_count = 2
        mock_report1.hostile_names = []
        mock_report1.is_clear = False
        mock_report1.threat_type = MagicMock()
        mock_report1.threat_type.value = "hostile"
        mock_report1.ship_types = []
        mock_report1.direction = None
        mock_report1.raw_text = "Tama +2"

        mock_report2 = MagicMock()
        mock_report2.system_name = "Rancer"
        mock_report2.hostile_count = 5
        mock_report2.hostile_names = []
        mock_report2.is_clear = False
        mock_report2.threat_type = MagicMock()
        mock_report2.threat_type.value = "gate_camp"
        mock_report2.ship_types = ["Sabre"]
        mock_report2.direction = None
        mock_report2.raw_text = "Rancer +5 camp Sabre"

        with patch(
            "backend.app.mcp.tools._submit_intel",
            return_value=[mock_report1, mock_report2],
        ):
            result = submit_intel(text="Tama +2\nRancer +5 camp Sabre")

            assert result["reports_parsed"] == 2
            assert "Tama" in result["hostile_systems"]
            assert "Rancer" in result["hostile_systems"]

    def test_exception_handling(self):
        """Should return error dict when parser throws."""
        with patch(
            "backend.app.mcp.tools._submit_intel",
            side_effect=Exception("Parse error"),
        ):
            result = submit_intel(text="some text")
            assert "error" in result
            assert "Failed to parse intel" in result["error"]


# =============================================================================
# calculate_fatigue Tests
# =============================================================================


class TestCalculateFatigue:
    """Tests for the calculate_fatigue tool function."""

    def test_missing_light_years(self):
        """Should return validation error when light_years is missing."""
        result = calculate_fatigue(light_years=None)
        assert "error" in result

    def test_light_years_too_small(self):
        """Should return validation error for light_years below minimum."""
        result = calculate_fatigue(light_years=0.0)
        assert "error" in result

    def test_light_years_too_large(self):
        """Should return validation error for light_years above maximum."""
        result = calculate_fatigue(light_years=999.0)
        assert "error" in result

    def test_boolean_light_years(self):
        """Should return validation error for boolean light_years."""
        result = calculate_fatigue(light_years=True)
        assert "error" in result

    def test_basic_jump_no_fatigue(self):
        """Should calculate fatigue for a fresh jump with no existing fatigue."""
        result = calculate_fatigue(light_years=5.0, current_fatigue_minutes=0)

        assert "error" not in result
        assert result["distance_ly"] == 5.0
        assert result["current_fatigue_minutes"] == 0.0
        assert result["blue_timer_seconds"] > 0
        assert result["red_timer_seconds"] > 0
        assert "blue_timer_formatted" in result
        assert "red_timer_formatted" in result
        assert result["fatigue_multiplier"] == 0.0

    def test_jump_with_existing_fatigue(self):
        """Should correctly factor in existing fatigue."""
        # With existing fatigue, timers should be longer
        result_fresh = calculate_fatigue(light_years=5.0, current_fatigue_minutes=0)
        result_fatigued = calculate_fatigue(light_years=5.0, current_fatigue_minutes=30)

        assert result_fatigued["blue_timer_seconds"] > result_fresh["blue_timer_seconds"]
        assert result_fatigued["fatigue_multiplier"] > 0

    def test_one_ly_jump(self):
        """Should calculate correct timers for minimum distance jump."""
        result = calculate_fatigue(light_years=1.0, current_fatigue_minutes=0)

        # Blue timer should be at least 60 seconds (1 minute per LY minimum)
        assert result["blue_timer_seconds"] >= 60.0
        assert result["distance_ly"] == 1.0

    def test_default_fatigue_is_zero(self):
        """Should default current_fatigue_minutes to 0."""
        result = calculate_fatigue(light_years=5.0)

        assert result["current_fatigue_minutes"] == 0.0
        assert result["fatigue_multiplier"] == 0.0

    def test_formatted_timers_present(self):
        """Should include formatted timer strings."""
        result = calculate_fatigue(light_years=5.0)

        assert "blue_timer_formatted" in result
        assert "red_timer_formatted" in result
        assert isinstance(result["blue_timer_formatted"], str)
        assert isinstance(result["red_timer_formatted"], str)

    def test_result_has_all_fields(self):
        """Should return all expected fields."""
        result = calculate_fatigue(light_years=5.0)

        expected_fields = [
            "distance_ly",
            "current_fatigue_minutes",
            "blue_timer_seconds",
            "blue_timer_formatted",
            "red_timer_seconds",
            "red_timer_formatted",
            "blue_timer_added_seconds",
            "red_timer_added_seconds",
            "fatigue_multiplier",
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

    def test_negative_fatigue_rejected(self):
        """Should reject negative current_fatigue_minutes."""
        result = calculate_fatigue(light_years=5.0, current_fatigue_minutes=-10)
        assert "error" in result

    def test_via_server(self, server):
        """Should work through the MCP server tool call interface."""
        import asyncio

        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_calculate_fatigue",
                "arguments": {"light_years": 5.0},
            },
        }
        response = asyncio.get_event_loop().run_until_complete(server.handle_request(request))

        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["distance_ly"] == 5.0
        assert "blue_timer_seconds" in content


# =============================================================================
# Server tools/call Integration Tests
# =============================================================================


class TestServerToolCallRouting:
    """Test that tools/call routes correctly to the new tools."""

    @pytest.mark.asyncio
    async def test_kill_stats_tool_call(self, server):
        """Kill stats tool should route through server correctly."""
        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_universe.systems = {"Jita": mock_system}

        mock_stats = MagicMock()
        mock_stats.recent_kills = 7
        mock_stats.recent_pods = 2

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_system_kills",
                new_callable=AsyncMock,
                return_value=mock_stats,
            ),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "gatekeeper_kill_stats",
                    "arguments": {"system_name": "Jita", "hours": 12},
                },
            }
            response = await server.handle_request(request)

            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["kills"] == 7
            assert content["hours"] == 12

    @pytest.mark.asyncio
    async def test_hot_systems_tool_call(self, server):
        """Hot systems tool should route through server correctly."""
        mock_universe = MagicMock()
        mock_universe.systems = {}

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.fetch_bulk_system_stats",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "gatekeeper_hot_systems",
                    "arguments": {"hours": 6, "limit": 5},
                },
            }
            response = await server.handle_request(request)

            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["hours"] == 6

    @pytest.mark.asyncio
    async def test_submit_intel_tool_call(self, server):
        """Submit intel tool should route through server correctly."""
        mock_report = MagicMock()
        mock_report.system_name = "Tama"
        mock_report.hostile_count = 1
        mock_report.hostile_names = ["SomePlayer"]
        mock_report.is_clear = False
        mock_report.threat_type = MagicMock()
        mock_report.threat_type.value = "hostile"
        mock_report.ship_types = []
        mock_report.direction = None
        mock_report.raw_text = "Tama SomePlayer"

        with patch(
            "backend.app.mcp.tools._submit_intel",
            return_value=[mock_report],
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "tools/call",
                "params": {
                    "name": "gatekeeper_submit_intel",
                    "arguments": {"text": "Tama SomePlayer"},
                },
            }
            response = await server.handle_request(request)

            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["reports_parsed"] == 1

    @pytest.mark.asyncio
    async def test_external_links_tool_call(self, server):
        """External links tool should route through server correctly."""
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_system.region_name = "The Forge"
        mock_system.region_id = 10000002

        mock_systems_dict = MagicMock()
        mock_systems_dict.__contains__ = lambda self, key: key == "Jita"
        mock_systems_dict.get = MagicMock(
            side_effect=lambda name, default=None: mock_system if name == "Jita" else default
        )

        mock_universe = MagicMock()
        mock_universe.systems = mock_systems_dict

        with patch("backend.app.mcp.tools.load_universe", return_value=mock_universe):
            request = {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "tools/call",
                "params": {
                    "name": "gatekeeper_external_links",
                    "arguments": {"system_name": "Jita"},
                },
            }
            response = await server.handle_request(request)

            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["system_name"] == "Jita"
            assert "dotlan" in content["links"]

    @pytest.mark.asyncio
    async def test_system_neighbors_tool_call(self, server):
        """System neighbors tool should route through server correctly."""
        mock_universe = MagicMock()
        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.security = 0.9
        mock_jita.region_name = "The Forge"
        mock_universe.systems = {"Jita": mock_jita}

        with (
            patch("backend.app.mcp.tools.load_universe", return_value=mock_universe),
            patch(
                "backend.app.mcp.tools.get_neighbors",
                return_value=[],
            ),
        ):
            request = {
                "jsonrpc": "2.0",
                "id": 14,
                "method": "tools/call",
                "params": {
                    "name": "gatekeeper_system_neighbors",
                    "arguments": {"system_name": "Jita"},
                },
            }
            response = await server.handle_request(request)

            assert "result" in response
            content = json.loads(response["result"]["content"][0]["text"])
            assert content["system_name"] == "Jita"
            assert content["neighbor_count"] == 0

    @pytest.mark.asyncio
    async def test_calculate_fatigue_tool_call(self, server):
        """Calculate fatigue tool should route through server correctly."""
        request = {
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_calculate_fatigue",
                "arguments": {"light_years": 3.5, "current_fatigue_minutes": 10},
            },
        }
        response = await server.handle_request(request)

        assert "result" in response
        content = json.loads(response["result"]["content"][0]["text"])
        assert content["distance_ly"] == 3.5
        assert content["current_fatigue_minutes"] == 10.0
        assert content["fatigue_multiplier"] > 0


# =============================================================================
# Tools List Integration Test
# =============================================================================


class TestToolsListIncludesNewTools:
    """Verify tools/list returns all new tools."""

    @pytest.mark.asyncio
    async def test_tools_list_has_17_tools(self, server):
        """tools/list should return all 17 tools."""
        request = {"jsonrpc": "2.0", "id": 20, "method": "tools/list"}
        response = await server.handle_request(request)

        tools = response["result"]["tools"]
        assert len(tools) == 17

    @pytest.mark.asyncio
    async def test_tools_list_contains_new_tool_names(self, server):
        """tools/list should include all 6 new tool names."""
        request = {"jsonrpc": "2.0", "id": 21, "method": "tools/list"}
        response = await server.handle_request(request)

        tool_names = [t["name"] for t in response["result"]["tools"]]
        new_tools = [
            "gatekeeper_kill_stats",
            "gatekeeper_hot_systems",
            "gatekeeper_system_neighbors",
            "gatekeeper_external_links",
            "gatekeeper_submit_intel",
            "gatekeeper_calculate_fatigue",
        ]
        for name in new_tools:
            assert name in tool_names, f"Missing tool in tools/list: {name}"
