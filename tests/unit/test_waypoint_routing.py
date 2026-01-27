"""Unit tests for waypoint routing service."""

import pytest

from backend.app.services.routing import compute_waypoint_route


class TestComputeWaypointRoute:
    """Tests for compute_waypoint_route function."""

    def test_ordered_waypoint_route_three_stops(self):
        """Test computing an ordered route through three waypoints."""
        result = compute_waypoint_route(
            from_system="Jita",
            waypoints=["Perimeter", "Urlen", "Sirppala"],
        )

        assert result.from_system == "Jita"
        assert result.waypoints == ["Perimeter", "Urlen", "Sirppala"]
        assert len(result.legs) == 3
        assert result.legs[0].from_system == "Jita"
        assert result.legs[0].to_system == "Perimeter"
        assert result.legs[1].from_system == "Perimeter"
        assert result.legs[1].to_system == "Urlen"
        assert result.legs[2].from_system == "Urlen"
        assert result.legs[2].to_system == "Sirppala"
        assert result.total_jumps == sum(leg.jumps for leg in result.legs)
        assert result.optimized is False

    def test_single_waypoint(self):
        """Test single waypoint behaves like normal A->B route."""
        result = compute_waypoint_route(
            from_system="Jita",
            waypoints=["Perimeter"],
        )

        assert len(result.legs) == 1
        assert result.legs[0].from_system == "Jita"
        assert result.legs[0].to_system == "Perimeter"
        assert result.total_jumps == 1

    def test_optimize_reorders_waypoints(self):
        """Test that optimize=True can reorder waypoints."""
        result = compute_waypoint_route(
            from_system="Jita",
            waypoints=["Perimeter", "Urlen"],
            optimize=True,
        )

        assert result.optimized is True
        assert result.original_order == ["Perimeter", "Urlen"]
        assert len(result.legs) == 2
        # With nearest-neighbor from Jita, Perimeter (1 jump) should come first
        assert result.waypoints[0] == "Perimeter"

    def test_bridges_and_thera_params_passed_through(self):
        """Test that use_bridges and use_thera are passed to each leg."""
        # Should not raise - just verifying params flow through
        result = compute_waypoint_route(
            from_system="Jita",
            waypoints=["Perimeter"],
            use_bridges=True,
            use_thera=True,
        )

        assert len(result.legs) == 1

    def test_unknown_origin_raises(self):
        """Test unknown origin system raises ValueError."""
        with pytest.raises(ValueError, match="Unknown from_system"):
            compute_waypoint_route(
                from_system="NonExistent",
                waypoints=["Jita"],
            )

    def test_unknown_waypoint_raises(self):
        """Test unknown waypoint system raises ValueError."""
        with pytest.raises(ValueError, match="Unknown waypoint system"):
            compute_waypoint_route(
                from_system="Jita",
                waypoints=["NonExistent"],
            )

    def test_avoid_systems_across_legs(self):
        """Test that avoided systems are respected across all legs."""
        # Route through systems avoiding Perimeter
        # This should still work if alternate paths exist
        result = compute_waypoint_route(
            from_system="Jita",
            waypoints=["Urlen"],
            avoid={"Perimeter"},
        )

        # Perimeter should not appear in any leg's path
        for leg in result.legs:
            assert "Perimeter" not in leg.path_systems

    def test_total_cost_is_sum_of_legs(self):
        """Test total cost equals sum of leg costs."""
        result = compute_waypoint_route(
            from_system="Jita",
            waypoints=["Perimeter", "Urlen"],
        )

        expected_cost = sum(leg.cost for leg in result.legs)
        assert abs(result.total_cost - expected_cost) < 0.001

    def test_leg_path_systems_populated(self):
        """Test that each leg has path_systems filled in."""
        result = compute_waypoint_route(
            from_system="Jita",
            waypoints=["Perimeter"],
        )

        assert len(result.legs[0].path_systems) >= 2
        assert result.legs[0].path_systems[0] == "Jita"
        assert result.legs[0].path_systems[-1] == "Perimeter"
