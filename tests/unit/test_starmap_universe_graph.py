"""Tests for starmap universe graph module."""

import math

from backend.starmap.graph.universe_graph import SystemDistance, UniverseGraph
from backend.starmap.sde.models import SolarSystem


class TestSystemDistance:
    """Tests for SystemDistance dataclass."""

    def test_create_system_distance(self):
        """Should create system distance with required fields."""
        system = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Test",
            x=0,
            y=0,
            z=0,
        )

        sd = SystemDistance(system=system, distance_ly=5.5)

        assert sd.system == system
        assert sd.distance_ly == 5.5


class TestUniverseGraphConstants:
    """Tests for UniverseGraph constants."""

    def test_light_year_meters(self):
        """Should have correct light year conversion constant."""
        assert UniverseGraph.LIGHT_YEAR_METERS == 9.461e15


class TestUniverseGraphInit:
    """Tests for UniverseGraph initialization."""

    def test_init_default_path(self):
        """Should use default database path."""
        graph = UniverseGraph()

        assert graph.db_path is not None
        assert graph._system_cache == {}
        assert graph._adjacency is None

    def test_init_custom_path(self):
        """Should accept custom database path."""
        graph = UniverseGraph(db_path="/tmp/test.db")

        assert graph.db_path == "/tmp/test.db"


class TestCalculateDistanceLy:
    """Tests for calculate_distance_ly method."""

    def test_same_system(self):
        """Should return 0 for same coordinates."""
        graph = UniverseGraph()

        sys1 = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Test1",
            x=1e15,
            y=2e15,
            z=3e15,
        )
        sys2 = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Test2",
            x=1e15,
            y=2e15,
            z=3e15,
        )

        distance = graph.calculate_distance_ly(sys1, sys2)

        assert distance == 0.0

    def test_one_light_year(self):
        """Should correctly calculate 1 LY distance."""
        graph = UniverseGraph()

        sys1 = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=0,
            y=0,
            z=0,
        )
        sys2 = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Dest",
            x=UniverseGraph.LIGHT_YEAR_METERS,
            y=0,
            z=0,
        )

        distance = graph.calculate_distance_ly(sys1, sys2)

        assert abs(distance - 1.0) < 0.0001

    def test_diagonal_distance(self):
        """Should correctly calculate 3D diagonal distance."""
        graph = UniverseGraph()

        # 3-4-5 triangle scaled to LY
        ly = UniverseGraph.LIGHT_YEAR_METERS

        sys1 = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=0,
            y=0,
            z=0,
        )
        sys2 = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Dest",
            x=3 * ly,
            y=4 * ly,
            z=0,
        )

        distance = graph.calculate_distance_ly(sys1, sys2)

        # sqrt(3^2 + 4^2) = 5
        assert abs(distance - 5.0) < 0.0001

    def test_3d_distance(self):
        """Should correctly calculate full 3D distance."""
        graph = UniverseGraph()

        ly = UniverseGraph.LIGHT_YEAR_METERS

        sys1 = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=0,
            y=0,
            z=0,
        )
        sys2 = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Dest",
            x=1 * ly,
            y=2 * ly,
            z=2 * ly,
        )

        distance = graph.calculate_distance_ly(sys1, sys2)

        # sqrt(1^2 + 2^2 + 2^2) = sqrt(9) = 3
        assert abs(distance - 3.0) < 0.0001

    def test_negative_coordinates(self):
        """Should handle negative coordinates correctly."""
        graph = UniverseGraph()

        ly = UniverseGraph.LIGHT_YEAR_METERS

        sys1 = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=-5 * ly,
            y=0,
            z=0,
        )
        sys2 = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Dest",
            x=5 * ly,
            y=0,
            z=0,
        )

        distance = graph.calculate_distance_ly(sys1, sys2)

        assert abs(distance - 10.0) < 0.0001

    def test_very_small_distance(self):
        """Should handle very small distances."""
        graph = UniverseGraph()

        ly = UniverseGraph.LIGHT_YEAR_METERS

        sys1 = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=0,
            y=0,
            z=0,
        )
        sys2 = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Dest",
            x=0.001 * ly,
            y=0,
            z=0,
        )

        distance = graph.calculate_distance_ly(sys1, sys2)

        assert abs(distance - 0.001) < 0.00001

    def test_large_distance(self):
        """Should handle large distances (across EVE universe)."""
        graph = UniverseGraph()

        ly = UniverseGraph.LIGHT_YEAR_METERS

        sys1 = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=0,
            y=0,
            z=0,
        )
        sys2 = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Dest",
            x=100 * ly,
            y=100 * ly,
            z=100 * ly,
        )

        distance = graph.calculate_distance_ly(sys1, sys2)

        # sqrt(100^2 * 3) = 100 * sqrt(3) ≈ 173.2
        expected = 100 * math.sqrt(3)
        assert abs(distance - expected) < 0.01
