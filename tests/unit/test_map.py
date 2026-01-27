"""Unit tests for map visualization API and service."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.app.api.v1.map import (
    ConnectionResponse,
    RegionMapResponse,
    RouteVisualizationRequest,
    RouteVisualizationResponse,
    SystemNodeResponse,
    SystemsInRangeResponse,
    get_constellation_map_endpoint,
    get_region_map_endpoint,
    get_security_colors,
    get_systems_in_range_endpoint,
    get_threat_colors,
    list_connection_types,
    list_security_levels,
    visualize_route,
)
from backend.app.services.map_visualization import (
    ConnectionType,
    RegionMapData,
    RouteVisualization,
    SecurityLevel,
    SystemConnection,
    SystemNode,
    ThreatLevel,
    create_system_node,
    get_security_color,
    get_security_level,
    get_threat_color,
)


class TestSecurityLevel:
    """Tests for security level classification."""

    def test_high_sec(self):
        """Test high-sec classification."""
        assert get_security_level(1.0) == SecurityLevel.high_sec
        assert get_security_level(0.9) == SecurityLevel.high_sec
        assert get_security_level(0.5) == SecurityLevel.high_sec

    def test_low_sec(self):
        """Test low-sec classification."""
        assert get_security_level(0.4) == SecurityLevel.low_sec
        assert get_security_level(0.3) == SecurityLevel.low_sec
        assert get_security_level(0.1) == SecurityLevel.low_sec

    def test_null_sec(self):
        """Test null-sec classification."""
        assert get_security_level(0.0) == SecurityLevel.null_sec
        assert get_security_level(-0.5) == SecurityLevel.null_sec
        assert get_security_level(-1.0) == SecurityLevel.null_sec


class TestSecurityColors:
    """Tests for security status colors."""

    def test_high_sec_colors(self):
        """Test high-sec colors are green shades."""
        color_1_0 = get_security_color(1.0)
        color_0_7 = get_security_color(0.7)
        color_0_5 = get_security_color(0.5)

        assert color_1_0.startswith("#")
        assert color_0_7.startswith("#")
        assert color_0_5.startswith("#")

    def test_low_sec_colors(self):
        """Test low-sec colors are orange/red shades."""
        color_0_4 = get_security_color(0.4)
        color_0_1 = get_security_color(0.1)

        assert color_0_4.startswith("#")
        assert color_0_1.startswith("#")

    def test_null_sec_colors(self):
        """Test null-sec colors are red shades."""
        color_0_0 = get_security_color(0.0)
        color_neg = get_security_color(-0.5)

        assert color_0_0.startswith("#")
        assert color_neg.startswith("#")


class TestThreatColors:
    """Tests for threat level colors."""

    def test_safe_color(self):
        """Test safe threat color is green."""
        color = get_threat_color(ThreatLevel.safe)
        assert color == "#00FF00"

    def test_caution_color(self):
        """Test caution threat color is yellow."""
        color = get_threat_color(ThreatLevel.caution)
        assert color == "#FFFF00"

    def test_dangerous_color(self):
        """Test dangerous threat color is orange."""
        color = get_threat_color(ThreatLevel.dangerous)
        assert color == "#FF8000"

    def test_deadly_color(self):
        """Test deadly threat color is red."""
        color = get_threat_color(ThreatLevel.deadly)
        assert color == "#FF0000"


class TestSystemNode:
    """Tests for SystemNode creation."""

    def test_create_system_node(self):
        """Test creating a system node."""
        node = create_system_node(
            system_id=30000142,
            system_name="Jita",
            security_status=0.9,
            region_name="The Forge",
            kills=10,
        )

        assert node.system_id == 30000142
        assert node.system_name == "Jita"
        assert node.security_status == 0.9
        assert node.security_level == SecurityLevel.high_sec
        assert node.region_name == "The Forge"
        assert node.kills_last_hour == 10

    def test_system_node_defaults(self):
        """Test system node default values."""
        node = create_system_node(
            system_id=30000001,
            system_name="Test",
            security_status=0.5,
        )

        assert node.threat_level == ThreatLevel.safe
        assert node.kills_last_hour == 0
        assert node.is_route_system is False
        assert node.route_index is None


class TestSystemConnection:
    """Tests for SystemConnection model."""

    def test_stargate_connection(self):
        """Test creating a stargate connection."""
        conn = SystemConnection(
            from_system_id=30000142,
            to_system_id=30000143,
            from_system_name="Jita",
            to_system_name="Perimeter",
            connection_type=ConnectionType.stargate,
        )

        assert conn.connection_type == ConnectionType.stargate
        assert conn.is_route_connection is False

    def test_jump_bridge_connection(self):
        """Test creating a jump bridge connection."""
        conn = SystemConnection(
            from_system_id=30000001,
            to_system_id=30000002,
            from_system_name="System A",
            to_system_name="System B",
            connection_type=ConnectionType.jump_bridge,
            is_route_connection=True,
        )

        assert conn.connection_type == ConnectionType.jump_bridge
        assert conn.is_route_connection is True


class TestRouteVisualization:
    """Tests for RouteVisualization model."""

    def test_empty_route(self):
        """Test empty route visualization."""
        viz = RouteVisualization(route_id="test-route")

        assert viz.route_id == "test-route"
        assert viz.systems == []
        assert viz.connections == []
        assert viz.total_jumps == 0

    def test_route_with_data(self):
        """Test route visualization with data."""
        node1 = create_system_node(30000142, "Jita", 0.9)
        node2 = create_system_node(30000143, "Perimeter", 0.9)

        viz = RouteVisualization(
            route_id="test-route",
            systems=[node1, node2],
            total_jumps=1,
            high_sec_jumps=1,
            dangerous_systems=["Test"],
        )

        assert len(viz.systems) == 2
        assert viz.total_jumps == 1
        assert viz.high_sec_jumps == 1
        assert "Test" in viz.dangerous_systems


class TestMapAPIEndpoints:
    """Tests for map API endpoints."""

    @pytest.mark.asyncio
    async def test_get_security_colors_endpoint(self):
        """Test security colors endpoint."""
        response = await get_security_colors()

        assert isinstance(response, dict)
        assert "1.0" in response
        assert "0.5" in response
        assert "0.0" in response
        assert "-1.0" in response

    @pytest.mark.asyncio
    async def test_get_threat_colors_endpoint(self):
        """Test threat colors endpoint."""
        response = await get_threat_colors()

        assert isinstance(response, dict)
        assert "safe" in response
        assert "caution" in response
        assert "dangerous" in response
        assert "deadly" in response

    @pytest.mark.asyncio
    async def test_list_connection_types_endpoint(self):
        """Test connection types endpoint."""
        response = await list_connection_types()

        assert isinstance(response, list)
        assert "stargate" in response
        assert "jump_bridge" in response
        assert "cyno_jump" in response

    @pytest.mark.asyncio
    async def test_list_security_levels_endpoint(self):
        """Test security levels endpoint."""
        response = await list_security_levels()

        assert isinstance(response, list)
        assert "high_sec" in response
        assert "low_sec" in response
        assert "null_sec" in response

    @pytest.mark.asyncio
    async def test_visualize_route_too_short(self):
        """Test route visualization with too few systems."""
        request = RouteVisualizationRequest(route=["Jita"])

        with pytest.raises(HTTPException) as exc_info:
            await visualize_route(request)

        assert exc_info.value.status_code == 400
        assert "at least 2 systems" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_route_visualization")
    async def test_visualize_route_success(self, mock_viz):
        """Test successful route visualization."""
        mock_viz.return_value = RouteVisualization(
            route_id="test",
            systems=[
                create_system_node(30000142, "Jita", 0.9),
                create_system_node(30000143, "Perimeter", 0.9),
            ],
            total_jumps=1,
            high_sec_jumps=1,
        )

        request = RouteVisualizationRequest(route=["Jita", "Perimeter"])
        response = await visualize_route(request)

        assert isinstance(response, RouteVisualizationResponse)
        assert len(response.systems) == 2
        assert response.total_jumps == 1

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_route_visualization")
    async def test_visualize_route_not_found(self, mock_viz):
        """Test route visualization when route can't be generated."""
        mock_viz.return_value = None

        request = RouteVisualizationRequest(route=["System1", "System2"])

        with pytest.raises(HTTPException) as exc_info:
            await visualize_route(request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_region_map")
    async def test_get_region_map_success(self, mock_region):
        """Test successful region map retrieval."""
        mock_region.return_value = RegionMapData(
            region_id=10000002,
            region_name="The Forge",
            systems=[create_system_node(30000142, "Jita", 0.9)],
        )

        response = await get_region_map_endpoint("The Forge")

        assert isinstance(response, RegionMapResponse)
        assert response.region_name == "The Forge"
        assert response.system_count == 1

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_region_map")
    async def test_get_region_map_not_found(self, mock_region):
        """Test region map not found."""
        mock_region.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_region_map_endpoint("NotARealRegion")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_constellation_map")
    async def test_get_constellation_map_success(self, mock_const):
        """Test successful constellation map retrieval."""
        mock_const.return_value = RegionMapData(
            region_id=20000001,
            region_name="Kimotoro",
            systems=[create_system_node(30000142, "Jita", 0.9)],
        )

        response = await get_constellation_map_endpoint("Kimotoro")

        assert isinstance(response, RegionMapResponse)
        assert response.region_name == "Kimotoro"

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_constellation_map")
    async def test_get_constellation_map_not_found(self, mock_const):
        """Test constellation map not found."""
        mock_const.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_constellation_map_endpoint("NotAConstellation")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_systems_in_range")
    async def test_get_systems_in_range_success(self, mock_range):
        """Test successful systems in range retrieval."""
        systems = [create_system_node(30000142, "Jita", 0.9)]
        connections = []
        mock_range.return_value = (systems, connections)

        response = await get_systems_in_range_endpoint("Jita", max_jumps=5)

        assert isinstance(response, SystemsInRangeResponse)
        assert response.center_system == "Jita"
        assert response.max_jumps == 5
        assert response.system_count == 1

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.map.get_systems_in_range")
    async def test_get_systems_in_range_not_found(self, mock_range):
        """Test systems in range with invalid center system."""
        mock_range.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_systems_in_range_endpoint("NotASystem")

        assert exc_info.value.status_code == 404


class TestSystemNodeResponse:
    """Tests for SystemNodeResponse model."""

    def test_from_node(self):
        """Test creating response from system node."""
        node = SystemNode(
            system_id=30000142,
            system_name="Jita",
            security_status=0.9,
            security_level=SecurityLevel.high_sec,
            region_name="The Forge",
            threat_level=ThreatLevel.safe,
            kills_last_hour=5,
            is_route_system=True,
            route_index=0,
        )

        response = SystemNodeResponse.from_node(node)

        assert response.system_id == 30000142
        assert response.system_name == "Jita"
        assert response.security_status == 0.9
        assert response.security_level == "high_sec"
        assert response.threat_level == "safe"
        assert response.is_route_system is True
        assert response.route_index == 0


class TestConnectionResponse:
    """Tests for ConnectionResponse model."""

    def test_from_connection(self):
        """Test creating response from connection."""
        conn = SystemConnection(
            from_system_id=30000142,
            to_system_id=30000143,
            from_system_name="Jita",
            to_system_name="Perimeter",
            connection_type=ConnectionType.stargate,
            is_route_connection=True,
        )

        response = ConnectionResponse.from_connection(conn)

        assert response.from_system_id == 30000142
        assert response.to_system_id == 30000143
        assert response.from_system_name == "Jita"
        assert response.to_system_name == "Perimeter"
        assert response.connection_type == "stargate"
        assert response.is_route_connection is True


class TestRegionMapResponse:
    """Tests for RegionMapResponse model."""

    def test_from_region_data(self):
        """Test creating response from region data."""
        data = RegionMapData(
            region_id=10000002,
            region_name="The Forge",
            systems=[create_system_node(30000142, "Jita", 0.9)],
            connections=[
                SystemConnection(
                    from_system_id=30000142,
                    to_system_id=30000143,
                    from_system_name="Jita",
                    to_system_name="Perimeter",
                    connection_type=ConnectionType.stargate,
                )
            ],
        )

        response = RegionMapResponse.from_region_data(data)

        assert response.region_id == 10000002
        assert response.region_name == "The Forge"
        assert response.system_count == 1
        assert response.connection_count == 1


class TestRouteVisualizationResponse:
    """Tests for RouteVisualizationResponse model."""

    def test_from_visualization(self):
        """Test creating response from visualization."""
        viz = RouteVisualization(
            route_id="test-123",
            systems=[create_system_node(30000142, "Jita", 0.9)],
            total_jumps=5,
            high_sec_jumps=3,
            low_sec_jumps=1,
            null_sec_jumps=1,
            dangerous_systems=["Tama"],
            jump_bridge_used=1,
        )

        response = RouteVisualizationResponse.from_visualization(viz)

        assert response.route_id == "test-123"
        assert response.total_jumps == 5
        assert response.high_sec_jumps == 3
        assert response.low_sec_jumps == 1
        assert response.null_sec_jumps == 1
        assert "Tama" in response.dangerous_systems
        assert response.jump_bridge_used == 1
