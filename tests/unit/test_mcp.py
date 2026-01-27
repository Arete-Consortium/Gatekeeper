"""Unit tests for MCP server and tools."""

import json
from unittest.mock import patch

import pytest

from backend.app.mcp.server import MCPServer
from backend.app.mcp.tools import (
    analyze_fitting,
    calculate_route,
    check_system_threat,
    create_alert_subscription,
    get_jump_range,
    get_region_info,
    get_ship_info,
    list_alert_subscriptions,
    parse_fitting,
)
from backend.app.services.webhooks import clear_subscriptions

# Sample EFT fitting
SAMPLE_FITTING = """[Caracal, Travel Fit]
Damage Control II
Nanofiber Internal Structure II

50MN Microwarpdrive II
"""


@pytest.fixture(autouse=True)
def clear_subs():
    """Clear subscriptions before each test."""
    clear_subscriptions()
    yield
    clear_subscriptions()


class TestMCPServer:
    """Tests for MCPServer class."""

    def test_server_init(self):
        """Test server initialization."""
        server = MCPServer()
        assert not server.initialized
        assert len(server.tools) > 0

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """Test initialize request."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }

        response = await server.handle_request(request)

        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "eve-gatekeeper"

    @pytest.mark.asyncio
    async def test_handle_initialized(self):
        """Test initialized notification."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "method": "initialized",
        }

        response = await server.handle_request(request)

        assert response is None  # No response for notifications
        assert server.initialized

    @pytest.mark.asyncio
    async def test_handle_tools_list(self):
        """Test tools/list request."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
        }

        response = await server.handle_request(request)

        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) > 0

        # Check tool structure
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "gatekeeper_route" in tool_names
        assert "gatekeeper_parse_fitting" in tool_names

    @pytest.mark.asyncio
    async def test_handle_tool_call_parse_fitting(self):
        """Test tools/call for parse_fitting."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_parse_fitting",
                "arguments": {"eft_text": SAMPLE_FITTING},
            },
        }

        response = await server.handle_request(request)

        assert response["id"] == 3
        assert "result" in response
        assert "content" in response["result"]

        # Parse the content
        content = response["result"]["content"][0]["text"]
        data = json.loads(content)
        assert data["ship_name"] == "Caracal"

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self):
        """Test unknown method."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "unknown/method",
        }

        response = await server.handle_request(request)

        assert response["id"] == 4
        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self):
        """Test unknown tool call."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {},
            },
        }

        response = await server.handle_request(request)

        assert response["id"] == 5
        assert "error" in response

    @pytest.mark.asyncio
    async def test_handle_ping(self):
        """Test ping request."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "ping",
        }

        response = await server.handle_request(request)

        assert response["id"] == 6
        assert response["result"] == {}


class TestCalculateRoute:
    """Tests for calculate_route tool."""

    @patch("backend.app.mcp.tools.compute_route")
    def test_basic_route(self, mock_route):
        """Test basic route returns serialized RouteResponse."""
        from backend.app.models.route import RouteResponse

        mock_route.return_value = RouteResponse(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            total_jumps=10,
            total_cost=10.0,
            max_risk=5.0,
            avg_risk=2.5,
            path=[],
        )

        result = calculate_route("Jita", "Amarr")

        assert result["from_system"] == "Jita"
        assert result["to_system"] == "Amarr"
        assert result["total_jumps"] == 10
        mock_route.assert_called_once()

    @patch("backend.app.mcp.tools.compute_route")
    def test_route_unknown_system(self, mock_route):
        """Test route with unknown system returns error dict."""
        mock_route.side_effect = ValueError("Unknown from_system: FakeSystem")

        result = calculate_route("FakeSystem", "Amarr")

        assert "error" in result
        assert "FakeSystem" in result["error"]


class TestParseFitting:
    """Tests for parse_fitting tool."""

    def test_parse_valid_fitting(self):
        """Test parsing valid fitting."""
        result = parse_fitting(SAMPLE_FITTING)

        assert result["ship_name"] == "Caracal"
        assert result["ship_category"] == "cruiser"
        assert "Damage Control II" in result["modules"]
        assert result["travel_capabilities"]["has_align_mods"] is True

    def test_parse_invalid_fitting(self):
        """Test parsing invalid fitting."""
        result = parse_fitting("not a valid fitting")

        assert "error" in result


class TestAnalyzeFitting:
    """Tests for analyze_fitting tool."""

    def test_analyze_valid_fitting(self):
        """Test analyzing valid fitting."""
        result = analyze_fitting(SAMPLE_FITTING)

        assert "fitting" in result
        assert "travel_recommendation" in result
        assert result["fitting"]["ship_name"] == "Caracal"
        assert result["travel_recommendation"]["can_use_gates"] is True

    def test_analyze_invalid_fitting(self):
        """Test analyzing invalid fitting."""
        result = analyze_fitting("invalid")

        assert "error" in result


class TestGetShipInfo:
    """Tests for get_ship_info tool."""

    def test_known_ship(self):
        """Test getting info for known ship."""
        result = get_ship_info("Caracal")

        assert result["ship_name"] == "Caracal"
        assert result["category"] == "cruiser"
        assert result["can_jump"] is False

    def test_capital_ship(self):
        """Test getting info for capital ship."""
        result = get_ship_info("Archon")

        assert result["category"] == "capital"
        assert result["can_jump"] is True
        assert result["can_use_gates"] is False

    def test_unknown_ship(self):
        """Test getting info for unknown ship."""
        result = get_ship_info("NotARealShip")

        assert "error" in result


class TestCheckSystemThreat:
    """Tests for check_system_threat tool."""

    @patch("backend.app.mcp.tools.risk_to_color", return_value="#FF0000")
    @patch("backend.app.mcp.tools.compute_risk")
    def test_check_threat(self, mock_risk, mock_color):
        """Test checking system threat returns risk structure."""
        from backend.app.models.risk import RiskBreakdown, RiskReport

        mock_risk.return_value = RiskReport(
            system_name="Tama",
            system_id=30002813,
            category="lowsec",
            security=0.3,
            score=15.0,
            breakdown=RiskBreakdown(
                security_component=5.0,
                kills_component=7.0,
                pods_component=3.0,
            ),
        )

        result = check_system_threat("Tama")

        assert result["system_name"] == "Tama"
        assert result["risk_score"] == 15.0
        assert result["risk_color"] == "#FF0000"
        assert "breakdown" in result

    @patch("backend.app.mcp.tools.compute_risk")
    def test_check_threat_unknown_system(self, mock_risk):
        """Test unknown system returns error dict."""
        mock_risk.side_effect = ValueError("Unknown system: FakeSystem")

        result = check_system_threat("FakeSystem")

        assert "error" in result
        assert "FakeSystem" in result["error"]


class TestGetRegionInfo:
    """Tests for get_region_info tool."""

    @patch("backend.app.mcp.tools.get_region_map")
    def test_get_region_success(self, mock_region):
        """Test getting region info."""
        from backend.app.services.map_visualization import RegionMapData, create_system_node

        mock_region.return_value = RegionMapData(
            region_id=10000002,
            region_name="The Forge",
            systems=[
                create_system_node(30000142, "Jita", 0.9),
                create_system_node(30000143, "Perimeter", 0.9),
            ],
        )

        result = get_region_info("The Forge")

        assert result["region_name"] == "The Forge"
        assert result["system_count"] == 2
        assert result["security_breakdown"]["high_sec"] == 2

    @patch("backend.app.mcp.tools.get_region_map")
    def test_get_region_not_found(self, mock_region):
        """Test getting unknown region."""
        mock_region.return_value = None

        result = get_region_info("NotARegion")

        assert "error" in result


class TestGetJumpRange:
    """Tests for get_jump_range tool."""

    @patch("backend.app.mcp.tools.get_systems_in_range")
    def test_get_range_success(self, mock_range):
        """Test getting systems in range."""
        from backend.app.services.map_visualization import create_system_node

        systems = [
            create_system_node(30000142, "Jita", 0.9),
            create_system_node(30000143, "Perimeter", 0.9),
        ]
        mock_range.return_value = (systems, [])

        result = get_jump_range("Jita", max_jumps=5)

        assert result["center_system"] == "Jita"
        assert result["max_jumps"] == 5
        assert result["total_systems"] == 2

    @patch("backend.app.mcp.tools.get_systems_in_range")
    def test_get_range_not_found(self, mock_range):
        """Test getting range for unknown system."""
        mock_range.return_value = None

        result = get_jump_range("NotASystem")

        assert "error" in result

    def test_max_jumps_clamped(self):
        """Test max_jumps is clamped to valid range."""
        with patch("backend.app.mcp.tools.get_systems_in_range") as mock_range:
            mock_range.return_value = ([], [])

            result = get_jump_range("Jita", max_jumps=100)
            assert result["max_jumps"] == 20

            result = get_jump_range("Jita", max_jumps=0)
            assert result["max_jumps"] == 1


class TestAlertSubscriptions:
    """Tests for alert subscription tools."""

    @pytest.mark.asyncio
    async def test_create_subscription(self):
        """Test creating a subscription."""
        result = await create_alert_subscription(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
            systems=["Jita", "Amarr"],
            min_value=100000000,
        )

        assert result["status"] == "created"
        assert "subscription_id" in result
        assert result["webhook_type"] == "discord"

    @pytest.mark.asyncio
    async def test_create_subscription_invalid_type(self):
        """Test creating subscription with invalid type."""
        result = await create_alert_subscription(
            webhook_url="https://example.com/webhook",
            webhook_type="invalid",
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_list_subscriptions_empty(self):
        """Test listing subscriptions when empty."""
        result = await list_alert_subscriptions()

        assert result["total"] == 0
        assert result["subscriptions"] == []

    @pytest.mark.asyncio
    async def test_list_subscriptions_with_data(self):
        """Test listing subscriptions with data."""
        await create_alert_subscription(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type="discord",
        )

        result = await list_alert_subscriptions()

        assert result["total"] == 1
        assert len(result["subscriptions"]) == 1
