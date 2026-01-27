"""Unit tests for Thera MCP tools."""

from unittest.mock import patch

import pytest

from backend.app.mcp.server import MCPServer
from backend.app.mcp.tools import (
    calculate_route,
    get_thera_connections,
    get_thera_status,
)
from backend.app.models.thera import TheraConnection


def _make_connection(**kwargs) -> TheraConnection:
    """Create a test TheraConnection."""
    defaults = {
        "id": 1,
        "in_system_id": 31000005,
        "in_system_name": "Thera",
        "out_system_id": 30000142,
        "out_system_name": "Jita",
        "wh_type": "Q003",
        "max_ship_size": "battleship",
        "remaining_hours": 10.0,
        "completed": False,
    }
    defaults.update(kwargs)
    return TheraConnection(**defaults)


MOCK_CONNECTIONS = [
    _make_connection(id=1, out_system_name="Jita", max_ship_size="battleship"),
    _make_connection(
        id=2, out_system_name="Amarr", max_ship_size="frigate", out_system_id=30000143
    ),
    _make_connection(
        id=3, out_system_name="Dodixie", max_ship_size="battleship", out_system_id=30000144
    ),
]


class TestGetTheraConnections:
    """Tests for get_thera_connections tool."""

    @pytest.mark.asyncio
    @patch("backend.app.mcp.tools.get_active_thera")
    async def test_returns_connections(self, mock_thera):
        """Test get_thera_connections returns connections."""
        mock_thera.return_value = MOCK_CONNECTIONS

        result = await get_thera_connections()

        assert result["total"] == 3
        assert len(result["connections"]) == 3
        assert result["connections"][0]["out_system_name"] == "Jita"

    @pytest.mark.asyncio
    @patch("backend.app.mcp.tools.get_active_thera")
    async def test_filter_by_ship_size(self, mock_thera):
        """Test get_thera_connections with ship size filter."""
        mock_thera.return_value = MOCK_CONNECTIONS

        result = await get_thera_connections(max_ship_size="frigate")

        assert result["total"] == 1
        assert result["connections"][0]["out_system_name"] == "Amarr"

    @pytest.mark.asyncio
    @patch("backend.app.mcp.tools.get_active_thera")
    async def test_empty_results(self, mock_thera):
        """Test get_thera_connections with no connections."""
        mock_thera.return_value = []

        result = await get_thera_connections()

        assert result["total"] == 0
        assert result["connections"] == []


class TestGetTheraStatus:
    """Tests for get_thera_status tool."""

    @pytest.mark.asyncio
    @patch("backend.app.mcp.tools.get_active_thera")
    @patch("backend.app.mcp.tools.get_thera_last_error")
    @patch("backend.app.mcp.tools.get_thera_cache_age")
    async def test_returns_status(self, mock_age, mock_error, mock_thera):
        """Test get_thera_status returns status dict."""
        mock_age.return_value = 120.0
        mock_error.return_value = None
        mock_thera.return_value = MOCK_CONNECTIONS

        result = await get_thera_status()

        assert result["cache_age"] == 120.0
        assert result["connection_count"] == 3
        assert result["api_healthy"] is True
        assert result["last_error"] is None

    @pytest.mark.asyncio
    @patch("backend.app.mcp.tools.get_active_thera")
    @patch("backend.app.mcp.tools.get_thera_last_error")
    @patch("backend.app.mcp.tools.get_thera_cache_age")
    async def test_error_state(self, mock_age, mock_error, mock_thera):
        """Test get_thera_status with error state."""
        mock_age.return_value = 600.0
        mock_error.return_value = "Connection timeout"
        mock_thera.return_value = []

        result = await get_thera_status()

        assert result["api_healthy"] is False
        assert result["last_error"] == "Connection timeout"
        assert result["connection_count"] == 0


class TestCalculateRouteThera:
    """Tests for calculate_route with use_thera parameter."""

    @patch("backend.app.mcp.tools.compute_route")
    def test_route_with_thera(self, mock_route):
        """Test calculate_route passes use_thera=True to compute_route."""
        from backend.app.models.route import RouteResponse

        mock_route.return_value = RouteResponse(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            total_jumps=8,
            total_cost=8.0,
            max_risk=3.0,
            avg_risk=1.5,
            path=[],
            thera_used=1,
        )

        result = calculate_route("Jita", "Amarr", use_thera=True)

        assert result["thera_used"] == 1
        mock_route.assert_called_once_with(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=None,
            use_thera=True,
        )

    @patch("backend.app.mcp.tools.compute_route")
    def test_route_without_thera(self, mock_route):
        """Test calculate_route defaults use_thera=False."""
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

        calculate_route("Jita", "Amarr")

        mock_route.assert_called_once_with(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid=None,
            use_thera=False,
        )


class TestMCPServerTheraRegistration:
    """Tests for Thera tool registration in MCP server."""

    def test_thera_tools_registered(self):
        """Test MCP server registers thera tools."""
        server = MCPServer()

        assert "gatekeeper_thera_connections" in server.tools
        assert "gatekeeper_thera_status" in server.tools

    @pytest.mark.asyncio
    async def test_tools_list_includes_thera(self):
        """Test tools/list includes thera tools."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
        }

        response = await server.handle_request(request)

        tool_names = [t["name"] for t in response["result"]["tools"]]
        assert "gatekeeper_thera_connections" in tool_names
        assert "gatekeeper_thera_status" in tool_names

    def test_route_schema_has_use_thera(self):
        """Test route tool schema includes use_thera parameter."""
        server = MCPServer()
        route_tool = server.tools["gatekeeper_route"]
        props = route_tool["inputSchema"]["properties"]

        assert "use_thera" in props
        assert props["use_thera"]["type"] == "boolean"
