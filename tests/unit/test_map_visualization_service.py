"""Unit tests for map_visualization service functions."""

from unittest.mock import patch, MagicMock

import pytest

from backend.app.services.map_visualization import (
    ConnectionType,
    RegionMapData,
    RouteVisualization,
    SecurityLevel,
    SystemConnection,
    SystemNode,
    ThreatLevel,
    get_constellation_map,
    get_region_map,
    get_route_visualization,
    get_systems_in_range,
)


class MockSystem:
    """Mock system for testing."""

    def __init__(
        self,
        system_id: int,
        name: str,
        security: float,
        region: str = "Test Region",
        constellation: str = "Test Constellation",
        region_id: int = 10000001,
    ):
        self.system_id = system_id
        self.security = security
        self.region = region
        self.constellation = constellation
        self.region_id = region_id
        self.name = name


class MockGate:
    """Mock gate for testing."""

    def __init__(self, from_system: str, to_system: str):
        self.from_system = from_system
        self.to_system = to_system


class MockUniverse:
    """Mock universe for testing."""

    def __init__(self, systems: dict, gates: list):
        self.systems = systems
        self.gates = gates


def create_test_universe():
    """Create a test universe with sample data."""
    systems = {
        "Jita": MockSystem(30000142, "Jita", 0.9, "The Forge", "Kimotoro"),
        "Perimeter": MockSystem(30000143, "Perimeter", 0.9, "The Forge", "Kimotoro"),
        "New Caldari": MockSystem(30000144, "New Caldari", 1.0, "The Forge", "Kimotoro"),
        "Tama": MockSystem(30002813, "Tama", 0.3, "The Citadel", "Iidoken"),
        "Nourvukaiken": MockSystem(30002811, "Nourvukaiken", 0.4, "The Citadel", "Iidoken"),
        "HED-GP": MockSystem(30001161, "HED-GP", -0.4, "Catch", "JWZ2-V"),
        "SV5-8N": MockSystem(30001162, "SV5-8N", -0.5, "Catch", "JWZ2-V"),
    }
    gates = [
        MockGate("Jita", "Perimeter"),
        MockGate("Perimeter", "Jita"),
        MockGate("Perimeter", "New Caldari"),
        MockGate("New Caldari", "Perimeter"),
        MockGate("Jita", "New Caldari"),
        MockGate("New Caldari", "Jita"),
        MockGate("Tama", "Nourvukaiken"),
        MockGate("Nourvukaiken", "Tama"),
        MockGate("HED-GP", "SV5-8N"),
        MockGate("SV5-8N", "HED-GP"),
    ]
    return MockUniverse(systems, gates)


class TestGetRouteVisualization:
    """Tests for get_route_visualization function."""

    @patch("backend.app.services.map_visualization.load_universe")
    def test_empty_route_returns_none(self, mock_load):
        """Test that empty route returns None."""
        result = get_route_visualization([])
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_no_universe_returns_none(self, mock_load):
        """Test that missing universe returns None."""
        mock_load.return_value = None
        result = get_route_visualization(["Jita", "Perimeter"])
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_basic_route_visualization(self, mock_load):
        """Test basic route visualization."""
        mock_load.return_value = create_test_universe()

        result = get_route_visualization(["Jita", "Perimeter"])

        assert result is not None
        assert isinstance(result, RouteVisualization)
        assert result.route_id == "route-Jita-Perimeter"
        assert len(result.systems) == 2
        assert len(result.connections) == 1
        assert result.total_jumps == 1
        assert result.high_sec_jumps == 2  # Both systems are high-sec

    @patch("backend.app.services.map_visualization.load_universe")
    def test_route_with_jump_bridges(self, mock_load):
        """Test route visualization with jump bridges."""
        mock_load.return_value = create_test_universe()

        result = get_route_visualization(
            ["Jita", "Perimeter"],
            jump_bridges=[("Jita", "Perimeter")],
        )

        assert result is not None
        assert result.jump_bridge_used == 1
        assert result.connections[0].connection_type == ConnectionType.jump_bridge

    @patch("backend.app.services.map_visualization.load_universe")
    def test_route_with_cyno_jumps(self, mock_load):
        """Test route visualization with cyno jumps."""
        mock_load.return_value = create_test_universe()

        result = get_route_visualization(
            ["HED-GP", "SV5-8N"],
            cyno_jumps=[("HED-GP", "SV5-8N")],
        )

        assert result is not None
        assert result.cyno_jumps_used == 1
        assert result.connections[0].connection_type == ConnectionType.cyno_jump

    @patch("backend.app.services.map_visualization.load_universe")
    def test_route_with_threat_data(self, mock_load):
        """Test route visualization with threat data."""
        mock_load.return_value = create_test_universe()

        threat_data = {
            "Tama": ThreatLevel.dangerous,
            "Nourvukaiken": ThreatLevel.deadly,
        }

        result = get_route_visualization(
            ["Tama", "Nourvukaiken"],
            threat_data=threat_data,
        )

        assert result is not None
        assert "Tama" in result.dangerous_systems
        assert "Nourvukaiken" in result.dangerous_systems

    @patch("backend.app.services.map_visualization.load_universe")
    def test_route_security_counts(self, mock_load):
        """Test route security type counting."""
        mock_load.return_value = create_test_universe()

        # Route through high, low, null
        result = get_route_visualization(["Jita", "Tama", "HED-GP"])

        assert result is not None
        assert result.high_sec_jumps == 1  # Jita
        assert result.low_sec_jumps == 1  # Tama
        assert result.null_sec_jumps == 1  # HED-GP

    @patch("backend.app.services.map_visualization.load_universe")
    def test_route_skips_unknown_systems(self, mock_load):
        """Test that unknown systems in route are skipped."""
        mock_load.return_value = create_test_universe()

        result = get_route_visualization(["Jita", "UnknownSystem", "Perimeter"])

        assert result is not None
        # Should only have Jita and Perimeter
        assert len(result.systems) == 2


class TestGetRegionMap:
    """Tests for get_region_map function."""

    @patch("backend.app.services.map_visualization.load_universe")
    def test_no_universe_returns_none(self, mock_load):
        """Test that missing universe returns None."""
        mock_load.return_value = None
        result = get_region_map("The Forge")
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_unknown_region_returns_none(self, mock_load):
        """Test that unknown region returns None."""
        mock_load.return_value = create_test_universe()
        result = get_region_map("NonExistent Region")
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_basic_region_map(self, mock_load):
        """Test basic region map retrieval."""
        mock_load.return_value = create_test_universe()

        result = get_region_map("The Forge")

        assert result is not None
        assert isinstance(result, RegionMapData)
        assert result.region_name == "The Forge"
        assert len(result.systems) == 3  # Jita, Perimeter, New Caldari
        assert result.region_id == 10000001

    @patch("backend.app.services.map_visualization.load_universe")
    def test_region_map_case_insensitive(self, mock_load):
        """Test region map retrieval is case-insensitive."""
        mock_load.return_value = create_test_universe()

        result = get_region_map("the forge")

        assert result is not None
        assert result.region_name == "the forge"  # Uses the input case

    @patch("backend.app.services.map_visualization.load_universe")
    def test_region_map_connections(self, mock_load):
        """Test region map includes connections."""
        mock_load.return_value = create_test_universe()

        result = get_region_map("The Forge")

        assert result is not None
        # Should have unique connections (not duplicates)
        assert len(result.connections) > 0
        # All connections should be stargates
        for conn in result.connections:
            assert conn.connection_type == ConnectionType.stargate


class TestGetConstellationMap:
    """Tests for get_constellation_map function."""

    @patch("backend.app.services.map_visualization.load_universe")
    def test_no_universe_returns_none(self, mock_load):
        """Test that missing universe returns None."""
        mock_load.return_value = None
        result = get_constellation_map("Kimotoro")
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_unknown_constellation_returns_none(self, mock_load):
        """Test that unknown constellation returns None."""
        mock_load.return_value = create_test_universe()
        result = get_constellation_map("NonExistent Constellation")
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_basic_constellation_map(self, mock_load):
        """Test basic constellation map retrieval."""
        mock_load.return_value = create_test_universe()

        result = get_constellation_map("Kimotoro")

        assert result is not None
        assert isinstance(result, RegionMapData)
        assert len(result.systems) == 3  # Jita, Perimeter, New Caldari

    @patch("backend.app.services.map_visualization.load_universe")
    def test_constellation_map_case_insensitive(self, mock_load):
        """Test constellation map retrieval is case-insensitive."""
        mock_load.return_value = create_test_universe()

        result = get_constellation_map("kimotoro")

        assert result is not None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_constellation_map_connections(self, mock_load):
        """Test constellation map includes connections."""
        mock_load.return_value = create_test_universe()

        result = get_constellation_map("Kimotoro")

        assert result is not None
        assert len(result.connections) > 0


class TestGetSystemsInRange:
    """Tests for get_systems_in_range function."""

    @patch("backend.app.services.map_visualization.load_universe")
    def test_no_universe_returns_none(self, mock_load):
        """Test that missing universe returns None."""
        mock_load.return_value = None
        result = get_systems_in_range("Jita", max_jumps=5)
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_unknown_system_returns_none(self, mock_load):
        """Test that unknown center system returns None."""
        mock_load.return_value = create_test_universe()
        result = get_systems_in_range("UnknownSystem", max_jumps=5)
        assert result is None

    @patch("backend.app.services.map_visualization.load_universe")
    def test_basic_systems_in_range(self, mock_load):
        """Test basic systems in range retrieval."""
        mock_load.return_value = create_test_universe()

        result = get_systems_in_range("Jita", max_jumps=1)

        assert result is not None
        systems, connections = result
        assert len(systems) >= 1  # At least Jita itself
        # Jita should be at distance 0
        jita_node = next((s for s in systems if s.system_name == "Jita"), None)
        assert jita_node is not None
        assert jita_node.route_index == 0  # Distance from center

    @patch("backend.app.services.map_visualization.load_universe")
    def test_systems_in_range_finds_neighbors(self, mock_load):
        """Test that systems in range finds neighboring systems."""
        mock_load.return_value = create_test_universe()

        result = get_systems_in_range("Jita", max_jumps=1)

        assert result is not None
        systems, _ = result
        system_names = [s.system_name for s in systems]
        # Should include Jita and its neighbors
        assert "Jita" in system_names
        assert "Perimeter" in system_names or "New Caldari" in system_names

    @patch("backend.app.services.map_visualization.load_universe")
    def test_systems_in_range_with_connections(self, mock_load):
        """Test systems in range includes connections."""
        mock_load.return_value = create_test_universe()

        result = get_systems_in_range("Jita", max_jumps=2, include_connections=True)

        assert result is not None
        systems, connections = result
        assert len(connections) > 0

    @patch("backend.app.services.map_visualization.load_universe")
    def test_systems_in_range_without_connections(self, mock_load):
        """Test systems in range without connections."""
        mock_load.return_value = create_test_universe()

        result = get_systems_in_range("Jita", max_jumps=2, include_connections=False)

        assert result is not None
        systems, connections = result
        assert len(connections) == 0

    @patch("backend.app.services.map_visualization.load_universe")
    def test_systems_in_range_distance_tracking(self, mock_load):
        """Test that system distance is tracked correctly."""
        mock_load.return_value = create_test_universe()

        result = get_systems_in_range("Jita", max_jumps=2)

        assert result is not None
        systems, _ = result

        # Find systems at each distance
        distances = {s.system_name: s.route_index for s in systems}
        assert distances.get("Jita") == 0  # Center is at distance 0

    @patch("backend.app.services.map_visualization.load_universe")
    def test_systems_in_range_respects_max_jumps(self, mock_load):
        """Test that max_jumps limit is respected."""
        mock_load.return_value = create_test_universe()

        result_1 = get_systems_in_range("Jita", max_jumps=1)
        result_5 = get_systems_in_range("Jita", max_jumps=5)

        assert result_1 is not None
        assert result_5 is not None
        systems_1, _ = result_1
        systems_5, _ = result_5

        # More jumps should find more or equal systems
        assert len(systems_5) >= len(systems_1)
