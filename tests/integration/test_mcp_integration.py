"""
End-to-end integration tests for all 11 MCP tools.

Each test sends a JSON-RPC request through MCPServer.handle_request()
and validates the full response payload from real services.
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
    async def test_route_with_avoid(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="Jita", destination="Amarr", avoid_systems=["Niarja"])
        )
        data = _parse_content(resp)
        path_names = [h["system_name"] for h in data["path"]]
        assert "Niarja" not in path_names

    @pytest.mark.asyncio
    async def test_route_unknown_system(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_route", origin="FakeSystem999", destination="Amarr")
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
    async def test_threat_lowsec_system(self, server):
        resp = await server.handle_request(_call("gatekeeper_system_threat", system_name="Tama"))
        data = _parse_content(resp)

        assert data["system_name"] == "Tama"
        assert data["category"] == "lowsec"
        # Lowsec base risk should be non-trivial
        assert data["risk_score"] > 0

    @pytest.mark.asyncio
    async def test_threat_unknown_system(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_system_threat", system_name="FakeSystem999")
        )
        data = _parse_content(resp)
        assert "error" in data


# ---------------------------------------------------------------------------
# 3. gatekeeper_parse_fitting
# ---------------------------------------------------------------------------
SAMPLE_EFT = """[Caracal, Travel Fit]
Damage Control II
Nanofiber Internal Structure II

50MN Microwarpdrive II
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
    async def test_parse_invalid_fitting(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_parse_fitting", eft_text="not a valid fitting")
        )
        data = _parse_content(resp)
        assert "error" in data


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
    async def test_capital_ship(self, server):
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="Archon"))
        data = _parse_content(resp)

        assert data["category"] == "capital"
        assert data["can_jump"] is True
        assert data["can_use_gates"] is False

    @pytest.mark.asyncio
    async def test_unknown_ship(self, server):
        resp = await server.handle_request(_call("gatekeeper_ship_info", ship_name="NotAShip"))
        data = _parse_content(resp)
        assert "error" in data


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
    async def test_unknown_region(self, server):
        resp = await server.handle_request(_call("gatekeeper_region_map", region_name="FakeRegion"))
        data = _parse_content(resp)
        assert "error" in data


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
    async def test_jump_range_unknown_system(self, server):
        resp = await server.handle_request(
            _call("gatekeeper_jump_range", center_system="FakeSystem")
        )
        data = _parse_content(resp)
        assert "error" in data


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
