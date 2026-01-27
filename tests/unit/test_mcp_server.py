"""
Tests for MCP server module.

Improves coverage for backend/app/mcp/server.py
"""

import pytest

from backend.app.mcp.server import JSONRPC_VERSION, MCP_PROTOCOL_VERSION, VERSION, MCPServer


@pytest.fixture
def server():
    """Create a fresh MCP server instance."""
    return MCPServer()


class TestMCPServerInit:
    """Tests for MCPServer initialization."""

    def test_server_initializes_with_tools(self, server):
        """Server should initialize with registered tools."""
        assert server.tools is not None
        assert len(server.tools) > 0
        assert not server.initialized

    def test_all_expected_tools_registered(self, server):
        """All expected tools should be registered."""
        expected_tools = [
            "gatekeeper_route",
            "gatekeeper_parse_fitting",
            "gatekeeper_analyze_fitting",
            "gatekeeper_ship_info",
            "gatekeeper_system_threat",
            "gatekeeper_region_map",
            "gatekeeper_jump_range",
            "gatekeeper_create_alert",
            "gatekeeper_list_alerts",
        ]
        for tool_name in expected_tools:
            assert tool_name in server.tools

    def test_tool_has_required_fields(self, server):
        """Each tool should have name, description, and inputSchema."""
        for tool_name, tool in server.tools.items():
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["name"] == tool_name


class TestHandleInitialize:
    """Tests for initialize request handling."""

    @pytest.mark.asyncio
    async def test_initialize_returns_correct_response(self, server):
        """Initialize should return protocol version and capabilities."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
        response = await server.handle_request(request)

        assert response["jsonrpc"] == JSONRPC_VERSION
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]
        assert response["result"]["serverInfo"]["name"] == "eve-gatekeeper"
        assert response["result"]["serverInfo"]["version"] == VERSION


class TestHandleInitialized:
    """Tests for initialized notification handling."""

    @pytest.mark.asyncio
    async def test_initialized_sets_flag(self, server):
        """Initialized notification should set the initialized flag."""
        assert not server.initialized

        request = {"jsonrpc": "2.0", "method": "initialized"}
        response = await server.handle_request(request)

        assert response is None  # Notifications don't get responses
        assert server.initialized


class TestHandleToolsList:
    """Tests for tools/list request handling."""

    @pytest.mark.asyncio
    async def test_tools_list_returns_all_tools(self, server):
        """tools/list should return all registered tools."""
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = await server.handle_request(request)

        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == len(server.tools)

    @pytest.mark.asyncio
    async def test_tools_list_format(self, server):
        """Each tool in list should have name, description, inputSchema."""
        request = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        response = await server.handle_request(request)

        for tool in response["result"]["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool


class TestHandlePing:
    """Tests for ping request handling."""

    @pytest.mark.asyncio
    async def test_ping_returns_empty_result(self, server):
        """Ping should return empty result."""
        request = {"jsonrpc": "2.0", "id": 4, "method": "ping"}
        response = await server.handle_request(request)

        assert response["id"] == 4
        assert response["result"] == {}


class TestHandleUnknownMethod:
    """Tests for unknown method handling."""

    @pytest.mark.asyncio
    async def test_unknown_method_returns_error(self, server):
        """Unknown method should return method not found error."""
        request = {"jsonrpc": "2.0", "id": 5, "method": "unknown/method"}
        response = await server.handle_request(request)

        assert response["id"] == 5
        assert "error" in response
        assert response["error"]["code"] == -32601
        assert "Method not found" in response["error"]["message"]


class TestHandleToolCall:
    """Tests for tools/call request handling."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, server):
        """Calling unknown tool should return error."""
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        }
        response = await server.handle_request(request)

        assert response["id"] == 6
        assert "error" in response
        assert response["error"]["code"] == -32602
        assert "Unknown tool" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_parse_fitting_tool(self, server):
        """parse_fitting tool should work with valid EFT."""
        eft_text = "[Caracal, Test Fit]\nLight Missile Launcher II"
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_parse_fitting",
                "arguments": {"eft_text": eft_text},
            },
        }
        response = await server.handle_request(request)

        assert response["id"] == 7
        assert "result" in response
        assert "content" in response["result"]
        assert len(response["result"]["content"]) > 0
        assert response["result"]["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_analyze_fitting_tool(self, server):
        """analyze_fitting tool should work with valid EFT."""
        eft_text = "[Caracal, Test Fit]\nLight Missile Launcher II"
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_analyze_fitting",
                "arguments": {"eft_text": eft_text},
            },
        }
        response = await server.handle_request(request)

        assert response["id"] == 8
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_ship_info_tool(self, server):
        """ship_info tool should return ship information."""
        request = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_ship_info",
                "arguments": {"ship_name": "Caracal"},
            },
        }
        response = await server.handle_request(request)

        assert response["id"] == 9
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_list_alerts_tool(self, server):
        """list_alerts tool should return alerts list."""
        request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_list_alerts",
                "arguments": {},
            },
        }
        response = await server.handle_request(request)

        assert response["id"] == 10
        assert "result" in response
        assert "content" in response["result"]

    @pytest.mark.asyncio
    async def test_tool_error_returns_error_content(self, server):
        """Tool that raises exception should return error content."""
        # Use invalid EFT to trigger parsing error
        request = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "gatekeeper_parse_fitting",
                "arguments": {"eft_text": "invalid eft format"},
            },
        }
        response = await server.handle_request(request)

        assert response["id"] == 11
        assert "result" in response
        assert "content" in response["result"]
        # Error should be indicated (lowercase "error" in JSON response)
        assert (
            response["result"].get("isError", False)
            or "error" in response["result"]["content"][0]["text"]
        )


class TestExecuteTool:
    """Tests for _execute_tool method."""

    @pytest.mark.asyncio
    async def test_execute_tool_no_handler(self, server):
        """_execute_tool should raise for tool with no handler."""
        # This shouldn't happen in normal operation, but test the path
        with pytest.raises(ValueError, match="No handler for tool"):
            await server._execute_tool("nonexistent_tool", {})


class TestResponseHelpers:
    """Tests for response helper methods."""

    def test_success_response_format(self, server):
        """_success_response should create correct format."""
        response = server._success_response(42, {"data": "test"})

        assert response["jsonrpc"] == JSONRPC_VERSION
        assert response["id"] == 42
        assert response["result"] == {"data": "test"}

    def test_error_response_format(self, server):
        """_error_response should create correct format."""
        response = server._error_response(43, -32600, "Test error")

        assert response["jsonrpc"] == JSONRPC_VERSION
        assert response["id"] == 43
        assert "error" in response
        assert response["error"]["code"] == -32600
        assert response["error"]["message"] == "Test error"

    def test_success_response_with_none_id(self, server):
        """_success_response should handle None id."""
        response = server._success_response(None, {})
        assert response["id"] is None

    def test_error_response_with_string_id(self, server):
        """_error_response should handle string id."""
        response = server._error_response("req-123", -32600, "Error")
        assert response["id"] == "req-123"


class TestHandleRequestExceptionPath:
    """Tests for exception handling in handle_request."""

    @pytest.mark.asyncio
    async def test_exception_in_handler_returns_error(self, server):
        """Exception during request handling should return error response."""
        # Create a request that will cause an exception by manipulating the server
        original_handle = server._handle_initialize

        def broken_handler(*args, **kwargs):
            raise RuntimeError("Simulated failure")

        server._handle_initialize = broken_handler

        request = {"jsonrpc": "2.0", "id": 99, "method": "initialize", "params": {}}
        response = await server.handle_request(request)

        assert response["id"] == 99
        assert "error" in response
        assert response["error"]["code"] == -32603
        assert "Simulated failure" in response["error"]["message"]

        # Restore
        server._handle_initialize = original_handle


class TestToolInputSchemas:
    """Tests for tool input schema definitions."""

    def test_route_tool_schema(self, server):
        """Route tool should have correct schema."""
        tool = server.tools["gatekeeper_route"]
        schema = tool["inputSchema"]

        assert schema["type"] == "object"
        assert "origin" in schema["properties"]
        assert "destination" in schema["properties"]
        assert "profile" in schema["properties"]
        assert "avoid_systems" in schema["properties"]
        assert "origin" in schema["required"]
        assert "destination" in schema["required"]

    def test_parse_fitting_tool_schema(self, server):
        """Parse fitting tool should have correct schema."""
        tool = server.tools["gatekeeper_parse_fitting"]
        schema = tool["inputSchema"]

        assert "eft_text" in schema["properties"]
        assert "eft_text" in schema["required"]

    def test_jump_range_tool_schema(self, server):
        """Jump range tool should have correct schema."""
        tool = server.tools["gatekeeper_jump_range"]
        schema = tool["inputSchema"]

        assert "center_system" in schema["properties"]
        assert "max_jumps" in schema["properties"]
        assert schema["properties"]["max_jumps"]["minimum"] == 1
        assert schema["properties"]["max_jumps"]["maximum"] == 20

    def test_create_alert_tool_schema(self, server):
        """Create alert tool should have correct schema."""
        tool = server.tools["gatekeeper_create_alert"]
        schema = tool["inputSchema"]

        assert "webhook_url" in schema["properties"]
        assert "webhook_type" in schema["properties"]
        assert "systems" in schema["properties"]
        assert "min_value" in schema["properties"]
        assert "webhook_url" in schema["required"]


class TestMissingParamsHandling:
    """Tests for handling requests with missing params."""

    @pytest.mark.asyncio
    async def test_request_without_params(self, server):
        """Request without params should use empty dict."""
        request = {"jsonrpc": "2.0", "id": 100, "method": "ping"}
        response = await server.handle_request(request)

        assert response["id"] == 100
        assert "result" in response

    @pytest.mark.asyncio
    async def test_request_without_method(self, server):
        """Request without method should handle gracefully."""
        request = {"jsonrpc": "2.0", "id": 101}
        response = await server.handle_request(request)

        assert response["id"] == 101
        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_request_without_id(self, server):
        """Request without id should use None."""
        request = {"jsonrpc": "2.0", "method": "ping"}
        response = await server.handle_request(request)

        assert response["id"] is None
        assert "result" in response
