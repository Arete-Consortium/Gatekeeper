"""Tests for starmap pathfinding module."""

import math

from backend.starmap.graph.pathfinding import (
    PriorityItem,
    RouteResult,
    RouteType,
    a_star,
    count_security,
    dijkstra,
    get_weight_fn,
)


class TestRouteResult:
    """Tests for RouteResult dataclass."""

    def test_create_success_result(self):
        """Should create successful route result."""
        result = RouteResult(
            path=[1, 2, 3],
            total_jumps=2,
            security_summary={"highsec": 2, "lowsec": 1},
        )

        assert result.path == [1, 2, 3]
        assert result.total_jumps == 2
        assert result.found is True
        assert result.error is None

    def test_not_found_default_error(self):
        """Should create not-found result with default error."""
        result = RouteResult.not_found()

        assert result.path == []
        assert result.total_jumps == 0
        assert result.security_summary == {}
        assert result.found is False
        assert result.error == "No route found"

    def test_not_found_custom_error(self):
        """Should create not-found result with custom error."""
        result = RouteResult.not_found("Origin not in graph")

        assert result.found is False
        assert result.error == "Origin not in graph"


class TestPriorityItem:
    """Tests for PriorityItem dataclass."""

    def test_create_item(self):
        """Should create priority item."""
        item = PriorityItem(priority=5.0, system_id=1234, path=[1, 2])

        assert item.priority == 5.0
        assert item.system_id == 1234
        assert item.path == [1, 2]

    def test_comparison_by_priority(self):
        """Items should compare by priority only."""
        item1 = PriorityItem(priority=1.0, system_id=100, path=[1])
        item2 = PriorityItem(priority=2.0, system_id=50, path=[1, 2])

        assert item1 < item2

    def test_equal_priority(self):
        """Items with same priority should be equal in comparison."""
        item1 = PriorityItem(priority=1.0, system_id=100, path=[1])
        item2 = PriorityItem(priority=1.0, system_id=200, path=[1, 2, 3])

        # They have equal priority, so neither is less than the other
        assert not (item1 < item2)
        assert not (item2 < item1)


class TestRouteType:
    """Tests for RouteType enum."""

    def test_route_types_exist(self):
        """All route types should be defined."""
        assert RouteType.SHORTEST.value == "shortest"
        assert RouteType.SECURE.value == "secure"
        assert RouteType.INSECURE.value == "insecure"


class TestDijkstra:
    """Tests for dijkstra pathfinding function."""

    def test_direct_path(self):
        """Should find direct path between adjacent nodes."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0), (3, 1.0)],
            3: [(2, 1.0)],
        }

        path = dijkstra(graph, 1, 2)

        assert path == [1, 2]

    def test_multi_hop_path(self):
        """Should find multi-hop path."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0), (3, 1.0)],
            3: [(2, 1.0), (4, 1.0)],
            4: [(3, 1.0)],
        }

        path = dijkstra(graph, 1, 4)

        assert path == [1, 2, 3, 4]

    def test_shortest_path_with_weights(self):
        """Should find shortest weighted path."""
        graph = {
            1: [(2, 1.0), (3, 10.0)],
            2: [(1, 1.0), (3, 1.0)],
            3: [(1, 10.0), (2, 1.0)],
        }

        path = dijkstra(graph, 1, 3)

        # Should go through 2, not direct (1->2->3 = 2 vs 1->3 = 10)
        assert path == [1, 2, 3]

    def test_start_not_in_graph(self):
        """Should return empty path if start not in graph."""
        graph = {1: [(2, 1.0)], 2: [(1, 1.0)]}

        path = dijkstra(graph, 99, 2)

        assert path == []

    def test_end_not_in_graph(self):
        """Should return empty path if end not in graph."""
        graph = {1: [(2, 1.0)], 2: [(1, 1.0)]}

        path = dijkstra(graph, 1, 99)

        assert path == []

    def test_no_path_disconnected(self):
        """Should return empty path for disconnected nodes."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0)],
            3: [],  # Disconnected
        }

        path = dijkstra(graph, 1, 3)

        assert path == []

    def test_same_start_end(self):
        """Should return single node path when start equals end."""
        graph = {1: [(2, 1.0)], 2: [(1, 1.0)]}

        path = dijkstra(graph, 1, 1)

        assert path == [1]

    def test_with_avoid_set(self):
        """Should avoid specified nodes."""
        graph = {
            1: [(2, 1.0), (3, 5.0)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 5.0), (4, 1.0)],
            4: [(2, 1.0), (3, 1.0)],
        }

        # Without avoid, shortest path is 1->2->4
        path_normal = dijkstra(graph, 1, 4)
        assert path_normal == [1, 2, 4]

        # With avoid={2}, must go through 3
        path_avoid = dijkstra(graph, 1, 4, avoid={2})
        assert path_avoid == [1, 3, 4]

    def test_avoid_blocks_all_paths(self):
        """Should return empty if avoid blocks all paths."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0), (3, 1.0)],
            3: [(2, 1.0)],
        }

        path = dijkstra(graph, 1, 3, avoid={2})

        assert path == []

    def test_custom_weight_function(self):
        """Should use custom weight function."""
        graph = {
            1: [(2, 1.0), (3, 1.0)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 1.0), (4, 1.0)],
            4: [(2, 1.0), (3, 1.0)],
        }

        # Make node 2 expensive
        def weight_fn(src, dst, w):
            return 100.0 if dst == 2 else w

        path = dijkstra(graph, 1, 4, weight_fn=weight_fn)

        # Should avoid node 2 and go through 3
        assert path == [1, 3, 4]


class TestAStar:
    """Tests for A* pathfinding function."""

    def test_direct_path(self):
        """Should find direct path."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0)],
        }
        system_info = {
            1: (0.0, 0.0, "highsec"),
            2: (10.0, 0.0, "highsec"),
        }

        path = a_star(graph, system_info, 1, 2)

        assert path == [1, 2]

    def test_multi_hop_path(self):
        """Should find multi-hop path."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0), (3, 1.0)],
            3: [(2, 1.0)],
        }
        system_info = {
            1: (0.0, 0.0, "highsec"),
            2: (10.0, 0.0, "highsec"),
            3: (20.0, 0.0, "highsec"),
        }

        path = a_star(graph, system_info, 1, 3)

        assert path == [1, 2, 3]

    def test_start_not_in_graph(self):
        """Should return empty path if start not in graph."""
        graph = {1: [(2, 1.0)], 2: [(1, 1.0)]}
        system_info = {1: (0, 0, "highsec"), 2: (10, 0, "highsec")}

        path = a_star(graph, system_info, 99, 2)

        assert path == []

    def test_end_not_in_graph(self):
        """Should return empty path if end not in graph."""
        graph = {1: [(2, 1.0)], 2: [(1, 1.0)]}
        system_info = {1: (0, 0, "highsec"), 2: (10, 0, "highsec")}

        path = a_star(graph, system_info, 1, 99)

        assert path == []

    def test_with_avoid_set(self):
        """Should avoid specified nodes."""
        graph = {
            1: [(2, 1.0), (3, 1.0)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 1.0), (4, 1.0)],
            4: [(2, 1.0), (3, 1.0)],
        }
        system_info = {
            1: (0.0, 0.0, "highsec"),
            2: (10.0, 0.0, "highsec"),
            3: (5.0, 10.0, "highsec"),
            4: (15.0, 5.0, "highsec"),
        }

        path = a_star(graph, system_info, 1, 4, avoid={2})

        # Must go through 3
        assert 2 not in path
        assert path[0] == 1
        assert path[-1] == 4

    def test_uses_heuristic_for_efficiency(self):
        """A* should use heuristic to guide search."""
        # Create a graph where heuristic helps
        graph = {
            1: [(2, 1.0), (3, 1.0)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 1.0), (5, 1.0)],
            4: [(2, 1.0), (6, 1.0)],
            5: [(3, 1.0)],
            6: [(4, 1.0)],
        }
        # Goal is 6, which is far from 3 but close to 2
        system_info = {
            1: (0.0, 0.0, "highsec"),
            2: (100.0, 0.0, "highsec"),
            3: (0.0, 100.0, "highsec"),
            4: (200.0, 0.0, "highsec"),
            5: (0.0, 200.0, "highsec"),
            6: (300.0, 0.0, "highsec"),
        }

        path = a_star(graph, system_info, 1, 6)

        # Should find path through 2,4 not 3,5
        assert path == [1, 2, 4, 6]

    def test_custom_weight_function(self):
        """Should use custom weight function."""
        graph = {
            1: [(2, 1.0), (3, 1.0)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 1.0), (4, 1.0)],
            4: [(2, 1.0), (3, 1.0)],
        }
        system_info = {
            1: (0.0, 0.0, "highsec"),
            2: (10.0, 0.0, "highsec"),
            3: (5.0, 10.0, "highsec"),
            4: (15.0, 5.0, "highsec"),
        }

        # Make node 2 expensive
        def weight_fn(src, dst, w):
            return 100.0 if dst == 2 else w

        path = a_star(graph, system_info, 1, 4, weight_fn=weight_fn)

        # Should avoid node 2 and go through 3
        assert 2 not in path

    def test_missing_system_info_defaults(self):
        """Should handle missing system info with defaults."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0), (3, 1.0)],
            3: [(2, 1.0)],
        }
        # Only partial system_info
        system_info = {1: (0.0, 0.0, "highsec")}

        path = a_star(graph, system_info, 1, 3)

        # Should still find path
        assert path == [1, 2, 3]


class TestGetWeightFn:
    """Tests for get_weight_fn function."""

    def test_shortest_always_one(self):
        """SHORTEST should return weight 1 for all edges."""
        system_info = {
            1: (0, 0, "highsec"),
            2: (0, 0, "lowsec"),
            3: (0, 0, "nullsec"),
        }

        fn = get_weight_fn(RouteType.SHORTEST, system_info)

        assert fn(1, 2, 5.0) == 1.0
        assert fn(2, 3, 10.0) == 1.0
        assert fn(3, 1, 100.0) == 1.0

    def test_secure_prefers_highsec(self):
        """SECURE should prefer highsec systems."""
        system_info = {
            1: (0, 0, "highsec"),
            2: (0, 0, "lowsec"),
            3: (0, 0, "nullsec"),
        }

        fn = get_weight_fn(RouteType.SECURE, system_info)

        # Destination security determines weight
        weight_to_highsec = fn(1, 1, 1.0)
        weight_to_lowsec = fn(1, 2, 1.0)
        weight_to_nullsec = fn(1, 3, 1.0)

        assert weight_to_highsec < weight_to_lowsec < weight_to_nullsec
        assert weight_to_highsec == 1.0
        assert weight_to_lowsec == 5.0
        assert weight_to_nullsec == 10.0

    def test_insecure_prefers_lowsec_nullsec(self):
        """INSECURE should prefer lowsec/nullsec."""
        system_info = {
            1: (0, 0, "highsec"),
            2: (0, 0, "lowsec"),
            3: (0, 0, "nullsec"),
        }

        fn = get_weight_fn(RouteType.INSECURE, system_info)

        weight_to_highsec = fn(1, 1, 1.0)
        weight_to_lowsec = fn(1, 2, 1.0)
        weight_to_nullsec = fn(1, 3, 1.0)

        assert weight_to_highsec > weight_to_lowsec
        assert weight_to_highsec > weight_to_nullsec
        assert weight_to_highsec == 5.0
        assert weight_to_lowsec == 1.0
        assert weight_to_nullsec == 1.0

    def test_secure_unknown_defaults_nullsec(self):
        """Unknown system should default to nullsec weights."""
        system_info = {}

        fn = get_weight_fn(RouteType.SECURE, system_info)

        # Unknown system gets nullsec treatment (weight 10)
        weight = fn(1, 99, 1.0)
        assert weight == 10.0

    def test_insecure_unknown_defaults_nullsec(self):
        """Unknown system should default to nullsec (low weight for insecure)."""
        system_info = {}

        fn = get_weight_fn(RouteType.INSECURE, system_info)

        # Unknown defaults to nullsec, which insecure likes (weight 1)
        weight = fn(1, 99, 1.0)
        assert weight == 1.0


class TestCountSecurity:
    """Tests for count_security function."""

    def test_empty_path(self):
        """Should return zero counts for empty path."""
        system_info = {}

        result = count_security([], system_info)

        assert result == {"highsec": 0, "lowsec": 0, "nullsec": 0, "wormhole": 0}

    def test_all_highsec(self):
        """Should count all highsec systems."""
        system_info = {
            1: (0, 0, "highsec"),
            2: (0, 0, "highsec"),
            3: (0, 0, "highsec"),
        }

        result = count_security([1, 2, 3], system_info)

        assert result["highsec"] == 3
        assert result["lowsec"] == 0
        assert result["nullsec"] == 0

    def test_mixed_security(self):
        """Should count mixed security correctly."""
        system_info = {
            1: (0, 0, "highsec"),
            2: (0, 0, "lowsec"),
            3: (0, 0, "nullsec"),
            4: (0, 0, "wormhole"),
        }

        result = count_security([1, 2, 3, 4], system_info)

        assert result["highsec"] == 1
        assert result["lowsec"] == 1
        assert result["nullsec"] == 1
        assert result["wormhole"] == 1

    def test_unknown_system_defaults_nullsec(self):
        """Unknown systems should be counted as nullsec."""
        system_info = {1: (0, 0, "highsec")}

        result = count_security([1, 99], system_info)

        assert result["highsec"] == 1
        assert result["nullsec"] == 1

    def test_unknown_security_class_defaults_nullsec(self):
        """Unknown security class should be counted as nullsec."""
        system_info = {
            1: (0, 0, "highsec"),
            2: (0, 0, "unknown_class"),
        }

        result = count_security([1, 2], system_info)

        assert result["highsec"] == 1
        assert result["nullsec"] == 1


class TestDijkstraEdgeCases:
    """Edge cases for Dijkstra algorithm."""

    def test_revisiting_node_via_longer_path(self):
        """Should not revisit nodes via longer paths."""
        # Graph where node 2 can be reached two ways
        graph = {
            1: [(2, 1.0), (3, 0.5)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 0.5), (2, 0.5)],  # 3->2 is faster than 1->2
            4: [(2, 1.0)],
        }

        path = dijkstra(graph, 1, 4)

        # Should find path through 3 then 2 (1->3->2->4 = 2.0) vs (1->2->4 = 2.0)
        # Both are equal, but we should reach 4
        assert path[-1] == 4
        assert 2 in path


class TestAStarEdgeCases:
    """Edge cases for A* algorithm."""

    def test_revisiting_node_via_better_path(self):
        """Should update g_score when better path found."""
        graph = {
            1: [(2, 10.0), (3, 1.0)],
            2: [(1, 10.0), (4, 1.0)],
            3: [(1, 1.0), (2, 1.0)],  # 3->2 much shorter than 1->2
            4: [(2, 1.0)],
        }
        system_info = {
            1: (0.0, 0.0, "highsec"),
            2: (100.0, 0.0, "highsec"),
            3: (50.0, 50.0, "highsec"),
            4: (150.0, 0.0, "highsec"),
        }

        path = a_star(graph, system_info, 1, 4)

        # Should find shorter path 1->3->2->4 = 3, not 1->2->4 = 11
        assert path == [1, 3, 2, 4]

    def test_no_path_when_destination_unreachable(self):
        """Should return empty path for unreachable destination."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0)],
            3: [],  # Disconnected
        }
        system_info = {
            1: (0.0, 0.0, "highsec"),
            2: (10.0, 0.0, "highsec"),
            3: (100.0, 0.0, "highsec"),
        }

        path = a_star(graph, system_info, 1, 3)

        assert path == []


class TestGetWeightFnEdgeCases:
    """Edge cases for get_weight_fn."""

    def test_default_fallback(self):
        """Should return identity function for unknown RouteType."""
        from unittest.mock import MagicMock

        # Create a mock RouteType that isn't SHORTEST, SECURE, or INSECURE
        fake_route_type = MagicMock()
        fake_route_type.__eq__ = lambda s, o: False  # Never equal

        system_info = {1: (0, 0, "highsec")}

        fn = get_weight_fn(fake_route_type, system_info)

        # Should return the original weight unchanged
        assert fn(1, 2, 5.0) == 5.0
        assert fn(1, 2, 100.0) == 100.0


class TestPathfindingIntegration:
    """Integration tests for pathfinding components."""

    def test_dijkstra_with_weight_fn(self):
        """Should correctly combine dijkstra with weight function."""
        graph = {
            1: [(2, 1.0), (3, 1.0)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 1.0), (4, 1.0)],
            4: [(2, 1.0), (3, 1.0)],
        }
        system_info = {
            1: (0, 0, "highsec"),
            2: (0, 0, "lowsec"),
            3: (0, 0, "highsec"),
            4: (0, 0, "highsec"),
        }

        weight_fn = get_weight_fn(RouteType.SECURE, system_info)
        path = dijkstra(graph, 1, 4, weight_fn=weight_fn)

        # Should go through highsec (3), not lowsec (2)
        assert path == [1, 3, 4]

    def test_a_star_with_weight_fn(self):
        """Should correctly combine A* with weight function."""
        graph = {
            1: [(2, 1.0), (3, 1.0)],
            2: [(1, 1.0), (4, 1.0)],
            3: [(1, 1.0), (4, 1.0)],
            4: [(2, 1.0), (3, 1.0)],
        }
        system_info = {
            1: (0, 0, "highsec"),
            2: (10, 0, "lowsec"),
            3: (5, 5, "highsec"),
            4: (15, 5, "highsec"),
        }

        weight_fn = get_weight_fn(RouteType.SECURE, system_info)
        path = a_star(graph, system_info, 1, 4, weight_fn=weight_fn)

        # Should go through highsec (3), not lowsec (2)
        assert path == [1, 3, 4]

    def test_full_route_calculation(self):
        """Should calculate complete route with security counts."""
        graph = {
            1: [(2, 1.0)],
            2: [(1, 1.0), (3, 1.0)],
            3: [(2, 1.0), (4, 1.0)],
            4: [(3, 1.0)],
        }
        system_info = {
            1: (0, 0, "highsec"),
            2: (10, 0, "highsec"),
            3: (20, 0, "lowsec"),
            4: (30, 0, "nullsec"),
        }

        path = dijkstra(graph, 1, 4)
        security = count_security(path, system_info)

        assert path == [1, 2, 3, 4]
        assert security["highsec"] == 2
        assert security["lowsec"] == 1
        assert security["nullsec"] == 1
