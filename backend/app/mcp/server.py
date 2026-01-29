"""
EVE Gatekeeper MCP Server - Model Context Protocol server for Claude Code integration.

Exposes EVE Gatekeeper functionality as MCP tools for route planning,
fitting analysis, alert management, and map visualization.

Usage:
    gatekeeper-mcp  # Start the MCP server (stdio transport)

Configuration in Claude Code:
    Add to ~/.claude.json:
    {
        "mcpServers": {
            "eve-gatekeeper": {
                "command": "gatekeeper-mcp"
            }
        }
    }
"""

import asyncio
import json
import sys
from collections.abc import Callable
from typing import Any, cast

from .tools import (
    analyze_fitting,
    calculate_route,
    check_system_threat,
    create_alert_subscription,
    get_jump_range,
    get_region_info,
    get_ship_info,
    get_thera_connections,
    get_thera_status,
    list_alert_subscriptions,
    parse_fitting,
)

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"
VERSION = "1.2.0"


class MCPServer:
    """MCP Server implementation for EVE Gatekeeper."""

    def __init__(self):
        self.tools = self._register_tools()
        self.initialized = False

    def _register_tools(self) -> dict[str, dict]:
        """Register available tools."""
        return {
            "gatekeeper_route": {
                "name": "gatekeeper_route",
                "description": "Calculate a route between two EVE Online systems. Returns jump count, security breakdown, and dangerous systems.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Origin system name (e.g., Jita)",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination system name (e.g., Amarr)",
                        },
                        "profile": {
                            "type": "string",
                            "description": "Route profile: shortest, safer, paranoid",
                            "enum": ["shortest", "safer", "paranoid"],
                            "default": "shortest",
                        },
                        "avoid_systems": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Systems to avoid (e.g., ['Tama', 'Rancer'])",
                            "default": [],
                        },
                        "use_thera": {
                            "type": "boolean",
                            "description": "Consider Thera wormhole shortcuts for routing",
                            "default": False,
                        },
                    },
                    "required": ["origin", "destination"],
                },
            },
            "gatekeeper_parse_fitting": {
                "name": "gatekeeper_parse_fitting",
                "description": "Parse an EVE Online EFT format fitting and extract ship info, modules, and travel capabilities.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "eft_text": {
                            "type": "string",
                            "description": "EFT format fitting text (starts with [ShipName, FitName])",
                        },
                    },
                    "required": ["eft_text"],
                },
            },
            "gatekeeper_analyze_fitting": {
                "name": "gatekeeper_analyze_fitting",
                "description": "Parse a fitting and get travel recommendations including routing profile suggestions and safety tips.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "eft_text": {
                            "type": "string",
                            "description": "EFT format fitting text",
                        },
                    },
                    "required": ["eft_text"],
                },
            },
            "gatekeeper_ship_info": {
                "name": "gatekeeper_ship_info",
                "description": "Get information about an EVE Online ship including category and jump capability.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "ship_name": {
                            "type": "string",
                            "description": "Ship type name (e.g., Caracal, Archon)",
                        },
                    },
                    "required": ["ship_name"],
                },
            },
            "gatekeeper_system_threat": {
                "name": "gatekeeper_system_threat",
                "description": "Check the current threat level and recent activity for an EVE Online system.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "system_name": {
                            "type": "string",
                            "description": "System name to check (e.g., Tama)",
                        },
                    },
                    "required": ["system_name"],
                },
            },
            "gatekeeper_region_map": {
                "name": "gatekeeper_region_map",
                "description": "Get region information including system count and security breakdown.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "region_name": {
                            "type": "string",
                            "description": "Region name (e.g., The Forge, Domain)",
                        },
                    },
                    "required": ["region_name"],
                },
            },
            "gatekeeper_jump_range": {
                "name": "gatekeeper_jump_range",
                "description": "Get all systems within a certain jump range of a center system.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "center_system": {
                            "type": "string",
                            "description": "Center system name",
                        },
                        "max_jumps": {
                            "type": "integer",
                            "description": "Maximum jump distance (1-20)",
                            "default": 5,
                            "minimum": 1,
                            "maximum": 20,
                        },
                    },
                    "required": ["center_system"],
                },
            },
            "gatekeeper_create_alert": {
                "name": "gatekeeper_create_alert",
                "description": "Create a kill alert subscription for Discord or Slack webhook notifications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "webhook_url": {
                            "type": "string",
                            "description": "Discord or Slack webhook URL",
                        },
                        "webhook_type": {
                            "type": "string",
                            "description": "Webhook type: discord or slack",
                            "enum": ["discord", "slack"],
                            "default": "discord",
                        },
                        "systems": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Systems to watch (empty = all)",
                            "default": [],
                        },
                        "min_value": {
                            "type": "number",
                            "description": "Minimum ISK value for alerts",
                            "default": None,
                        },
                    },
                    "required": ["webhook_url"],
                },
            },
            "gatekeeper_list_alerts": {
                "name": "gatekeeper_list_alerts",
                "description": "List all active kill alert subscriptions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            "gatekeeper_thera_connections": {
                "name": "gatekeeper_thera_connections",
                "description": "Get active Thera wormhole connections from EVE-Scout. Thera connections provide shortcuts through New Eden.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "max_ship_size": {
                            "type": "string",
                            "description": "Filter by max ship size (e.g., 'frigate', 'battleship')",
                        },
                    },
                },
            },
            "gatekeeper_thera_status": {
                "name": "gatekeeper_thera_status",
                "description": "Check Thera connection cache status and EVE-Scout API health.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        }

    async def handle_request(self, request: dict) -> dict | None:
        """Handle an incoming JSON-RPC request."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        try:
            if method == "initialize":
                return self._handle_initialize(req_id, params)
            elif method == "initialized":
                self.initialized = True
                return None  # No response for notifications
            elif method == "tools/list":
                return self._handle_tools_list(req_id)
            elif method == "tools/call":
                return await self._handle_tool_call(req_id, params)
            elif method == "ping":
                return self._success_response(req_id, {})
            else:
                return self._error_response(req_id, -32601, f"Method not found: {method}")
        except Exception as e:
            return self._error_response(req_id, -32603, str(e))

    def _handle_initialize(self, req_id: Any, params: dict) -> dict:
        """Handle initialize request."""
        return self._success_response(
            req_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "eve-gatekeeper",
                    "version": VERSION,
                },
            },
        )

    def _handle_tools_list(self, req_id: Any) -> dict:
        """Handle tools/list request."""
        tools = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"],
            }
            for tool in self.tools.values()
        ]
        return self._success_response(req_id, {"tools": tools})

    async def _handle_tool_call(self, req_id: Any, params: dict) -> dict:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        # Validate tool_name is provided
        if tool_name is None or tool_name == "":
            return self._error_response(
                req_id, -32602, "Missing required parameter: 'name' (tool name)"
            )

        # Validate tool_name is a string
        if not isinstance(tool_name, str):
            return self._error_response(
                req_id, -32602, f"Invalid type for 'name': expected string, got {type(tool_name).__name__}"
            )

        if tool_name not in self.tools:
            return self._error_response(req_id, -32602, f"Unknown tool: {tool_name}")

        # Validate arguments is a dict
        if arguments is not None and not isinstance(arguments, dict):
            return self._error_response(
                req_id, -32602, f"Invalid type for 'arguments': expected object, got {type(arguments).__name__}"
            )

        arguments = arguments or {}

        try:
            result = await self._execute_tool(tool_name, arguments)

            # Ensure result is JSON serializable
            try:
                result_text = json.dumps(result, indent=2, default=str)
            except (TypeError, ValueError) as json_err:
                return self._success_response(
                    req_id,
                    {
                        "content": [{"type": "text", "text": f"Error: Failed to serialize result: {str(json_err)}"}],
                        "isError": True,
                    },
                )

            return self._success_response(
                req_id,
                {
                    "content": [{"type": "text", "text": result_text}],
                },
            )
        except TypeError as e:
            # Likely a missing required argument
            return self._success_response(
                req_id,
                {
                    "content": [{"type": "text", "text": json.dumps({
                        "error": f"Invalid arguments: {str(e)}",
                        "hint": "Check that all required parameters are provided with correct types",
                    }, indent=2)}],
                    "isError": True,
                },
            )
        except Exception as e:
            return self._success_response(
                req_id,
                {
                    "content": [{"type": "text", "text": json.dumps({
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }, indent=2)}],
                    "isError": True,
                },
            )

    async def _execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute a tool and return the result."""
        tool_map = {
            "gatekeeper_route": calculate_route,
            "gatekeeper_parse_fitting": parse_fitting,
            "gatekeeper_analyze_fitting": analyze_fitting,
            "gatekeeper_ship_info": get_ship_info,
            "gatekeeper_system_threat": check_system_threat,
            "gatekeeper_region_map": get_region_info,
            "gatekeeper_jump_range": get_jump_range,
            "gatekeeper_create_alert": create_alert_subscription,
            "gatekeeper_list_alerts": list_alert_subscriptions,
            "gatekeeper_thera_connections": get_thera_connections,
            "gatekeeper_thera_status": get_thera_status,
        }

        handler = tool_map.get(tool_name)
        if handler is None:
            raise ValueError(f"No handler for tool: {tool_name}")

        # Cast to callable after None check
        func = cast(Callable[..., Any], handler)
        if asyncio.iscoroutinefunction(func):
            return await func(**arguments)
        return func(**arguments)

    def _success_response(self, req_id: Any, result: Any) -> dict:
        """Create a success response."""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "result": result,
        }

    def _error_response(self, req_id: Any, code: int, message: str) -> dict:
        """Create an error response."""
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": req_id,
            "error": {"code": code, "message": message},
        }


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    server = MCPServer()

    async def read_message() -> dict[str, Any] | None:
        """Read a JSON-RPC message from stdin."""
        line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
        if not line:
            return None
        try:
            return cast(dict[str, Any], json.loads(line.strip()))
        except json.JSONDecodeError:
            return None

    def write_message(message: dict) -> None:
        """Write a JSON-RPC message to stdout."""
        if message is not None:
            sys.stdout.write(json.dumps(message) + "\n")
            sys.stdout.flush()

    while True:
        request = await read_message()
        if request is None:
            break
        response = await server.handle_request(request)
        if response is not None:
            write_message(response)


def main() -> None:
    """Entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
