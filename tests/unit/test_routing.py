"""Unit tests for routing service."""

import pytest

from backend.app.api.v1.routing import (
    RouteHistoryEntry,
    RouteHistoryResponse,
    _add_to_history,
    clear_route_history,
    get_history,
    get_route_history,
)
from backend.app.services.routing import _build_graph, _dijkstra, compute_route


class TestBuildGraph:
    """Tests for graph building function."""

    def test_build_graph_creates_bidirectional_edges(self):
        """Test that graph has bidirectional edges."""
        graph, edge_types = _build_graph()

        # Jita -> Perimeter should exist
        assert "Perimeter" in graph["Jita"]
        # Perimeter -> Jita should also exist
        assert "Jita" in graph["Perimeter"]

    def test_build_graph_includes_all_systems(self):
        """Test that graph includes key systems."""
        graph, edge_types = _build_graph()

        assert "Jita" in graph
        assert "Perimeter" in graph
        assert "Amarr" in graph


class TestDijkstra:
    """Tests for Dijkstra pathfinding."""

    def test_dijkstra_finds_direct_path(self):
        """Test finding a direct path between adjacent systems."""
        graph, _ = _build_graph()
        path, cost = _dijkstra(graph, "Jita", "Perimeter", "shortest")

        assert path == ["Jita", "Perimeter"]
        assert cost == 1.0

    def test_dijkstra_finds_multi_hop_path(self):
        """Test finding a multi-hop path."""
        graph, _ = _build_graph()
        path, cost = _dijkstra(graph, "Jita", "Urlen", "shortest")

        assert path == ["Jita", "Perimeter", "Urlen"]
        assert cost == 2.0  # 1 + 1

    def test_dijkstra_same_start_end(self):
        """Test path when start equals end."""
        graph, _ = _build_graph()
        path, cost = _dijkstra(graph, "Jita", "Jita", "shortest")

        assert path == ["Jita"]
        assert cost == 0.0


class TestComputeRoute:
    """Tests for compute_route function."""

    def test_compute_route_basic(self):
        """Test basic route calculation."""
        response = compute_route("Jita", "Perimeter", "shortest")

        assert response.from_system == "Jita"
        assert response.to_system == "Perimeter"
        assert response.profile == "shortest"
        assert response.total_jumps == 1
        assert len(response.path) == 2

    def test_compute_route_path_details(self):
        """Test that route path contains proper hop details."""
        response = compute_route("Jita", "Urlen", "shortest")

        assert len(response.path) == 3

        # First hop
        assert response.path[0].system_name == "Jita"
        assert response.path[0].cumulative_jumps == 0

        # Last hop
        assert response.path[2].system_name == "Urlen"
        assert response.path[2].cumulative_jumps == 2

    def test_compute_route_risk_stats(self):
        """Test that route includes risk statistics."""
        response = compute_route("Jita", "Urlen", "shortest")

        assert response.max_risk >= 0
        assert response.avg_risk >= 0
        assert response.max_risk >= response.avg_risk or response.max_risk == response.avg_risk

    def test_compute_route_unknown_from_system(self):
        """Test error when from_system is unknown."""
        with pytest.raises(ValueError, match="Unknown from_system"):
            compute_route("NonExistent", "Jita", "shortest")

    def test_compute_route_unknown_to_system(self):
        """Test error when to_system is unknown."""
        with pytest.raises(ValueError, match="Unknown to_system"):
            compute_route("Jita", "NonExistent", "shortest")

    def test_compute_route_different_profiles(self):
        """Test that different profiles may produce different costs."""
        shortest = compute_route("Jita", "Urlen", "shortest")
        safer = compute_route("Jita", "Urlen", "safer")

        # Both should find a valid route
        assert shortest.total_jumps >= 1
        assert safer.total_jumps >= 1

        # Safer profile adds risk penalty, so cost should be >= shortest
        assert safer.total_cost >= shortest.total_cost

    def test_compute_route_cumulative_cost(self):
        """Test that cumulative cost increases along the path."""
        response = compute_route("Jita", "Urlen", "shortest")

        prev_cost = 0
        for hop in response.path:
            assert hop.cumulative_cost >= prev_cost
            prev_cost = hop.cumulative_cost


class TestRouteHistory:
    """Tests for route history feature."""

    def setup_method(self):
        """Clear history before each test."""
        clear_route_history()

    def test_add_to_history(self):
        """Test adding a route to history."""
        route = compute_route("Jita", "Perimeter", "shortest")
        _add_to_history(route)

        history = get_route_history()
        assert len(history) == 1
        assert history[0].from_system == "Jita"
        assert history[0].to_system == "Perimeter"

    def test_history_maintains_order(self):
        """Test that newer routes are first."""
        route1 = compute_route("Jita", "Perimeter", "shortest")
        route2 = compute_route("Jita", "Urlen", "shortest")

        _add_to_history(route1)
        _add_to_history(route2)

        history = get_route_history()
        assert len(history) == 2
        # Most recent first
        assert history[0].to_system == "Urlen"
        assert history[1].to_system == "Perimeter"

    def test_history_entry_fields(self):
        """Test that history entry has all fields."""
        route = compute_route("Jita", "Urlen", "safer")
        _add_to_history(route)

        entry = get_route_history()[0]
        assert entry.from_system == "Jita"
        assert entry.to_system == "Urlen"
        assert entry.profile == "safer"
        assert entry.total_jumps == route.total_jumps
        assert entry.calculated_at is not None

    def test_get_history_endpoint(self):
        """Test get_history endpoint."""
        route = compute_route("Jita", "Perimeter", "shortest")
        _add_to_history(route)

        response = get_history(limit=10)
        assert response.total == 1
        assert len(response.routes) == 1
        assert response.routes[0].from_system == "Jita"

    def test_get_history_respects_limit(self):
        """Test that limit parameter works."""
        for _ in range(5):
            route = compute_route("Jita", "Perimeter", "shortest")
            _add_to_history(route)

        response = get_history(limit=3)
        assert response.total == 5
        assert len(response.routes) == 3

    def test_clear_history(self):
        """Test clearing history."""
        route = compute_route("Jita", "Perimeter", "shortest")
        _add_to_history(route)

        assert len(get_route_history()) == 1

        clear_route_history()

        assert len(get_route_history()) == 0

    def test_history_stores_bridges_used(self):
        """Test that bridges_used is stored."""
        route = compute_route("Jita", "Perimeter", "shortest")
        _add_to_history(route)

        entry = get_route_history()[0]
        assert entry.bridges_used == route.bridges_used


class TestRouteHistoryModels:
    """Tests for route history Pydantic models."""

    def test_history_entry_model(self):
        """Test RouteHistoryEntry model."""
        entry = RouteHistoryEntry(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            total_jumps=15,
            bridges_used=2,
        )

        assert entry.from_system == "Jita"
        assert entry.to_system == "Amarr"
        assert entry.total_jumps == 15
        assert entry.bridges_used == 2
        assert entry.calculated_at is not None

    def test_history_response_model(self):
        """Test RouteHistoryResponse model."""
        entry = RouteHistoryEntry(
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            total_jumps=15,
        )

        response = RouteHistoryResponse(total=1, routes=[entry])

        assert response.total == 1
        assert len(response.routes) == 1
