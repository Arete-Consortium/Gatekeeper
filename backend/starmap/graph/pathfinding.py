"""Pathfinding algorithms for EVE universe navigation.

Implements Dijkstra and A* algorithms with support for:
- Multiple route preferences (shortest, secure, insecure)
- System avoidance
- Custom edge weights
"""

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import aiosqlite

from backend.starmap.sde.schema import get_db_path


class RouteType(Enum):
    """Route optimization preference."""

    SHORTEST = "shortest"  # Minimum jumps
    SECURE = "secure"  # Prefer highsec
    INSECURE = "insecure"  # Prefer lowsec/nullsec (avoid gate camps)


@dataclass
class RouteResult:
    """Result of a pathfinding operation."""

    path: list[int]  # System IDs in order
    total_jumps: int
    security_summary: dict[str, int]  # Count by security class
    found: bool = True
    error: str | None = None

    @classmethod
    def not_found(cls, error: str = "No route found") -> "RouteResult":
        """Create a not-found result."""
        return cls(
            path=[],
            total_jumps=0,
            security_summary={},
            found=False,
            error=error,
        )


@dataclass(order=True)
class PriorityItem:
    """Item in priority queue for Dijkstra/A*."""

    priority: float
    system_id: int = field(compare=False)
    path: list[int] = field(compare=False)


async def load_graph_from_db(
    db_path: str | None = None,
) -> tuple[dict[int, list[tuple[int, float]]], dict[int, tuple[float, float, str]]]:
    """Load universe graph from database.

    Returns:
        Tuple of:
        - adjacency: Dict mapping system_id -> [(neighbor_id, weight), ...]
        - system_info: Dict mapping system_id -> (x, y, security_class)
    """
    if db_path is None:
        db_path = str(get_db_path())

    adjacency: dict[int, list[tuple[int, float]]] = {}
    system_info: dict[int, tuple[float, float, str]] = {}

    async with aiosqlite.connect(db_path) as db:
        # Load connections
        cursor = await db.execute(
            """
            SELECT from_system_id, to_system_id, base_weight, security_weight
            FROM system_connections
            """
        )
        async for row in cursor:
            from_sys, to_sys, base_weight, sec_weight = row
            if from_sys not in adjacency:
                adjacency[from_sys] = []
            adjacency[from_sys].append((to_sys, base_weight + sec_weight))

        # Load system info for A* heuristic
        cursor = await db.execute(
            """
            SELECT system_id, map_x, map_y, security_class
            FROM solar_systems
            """
        )
        async for row in cursor:
            system_id, map_x, map_y, sec_class = row
            system_info[system_id] = (map_x or 0, map_y or 0, sec_class or "nullsec")

    return adjacency, system_info


def dijkstra(
    adjacency: dict[int, list[tuple[int, float]]],
    start: int,
    end: int,
    avoid: set[int] | None = None,
    weight_fn: Callable[[int, int, float], float] | None = None,
) -> list[int]:
    """Dijkstra's algorithm for shortest path.

    Args:
        adjacency: Graph adjacency list
        start: Starting system ID
        end: Destination system ID
        avoid: Set of system IDs to avoid
        weight_fn: Optional function to modify edge weights

    Returns:
        List of system IDs forming the path, or empty list if no path
    """
    if start not in adjacency or end not in adjacency:
        return []

    avoid = avoid or set()

    # Priority queue: (distance, system_id, path)
    heap: list[PriorityItem] = [PriorityItem(0, start, [start])]
    visited: set[int] = set()

    while heap:
        item = heapq.heappop(heap)
        current_dist = item.priority
        current = item.system_id
        path = item.path

        if current == end:
            return path

        if current in visited:
            continue
        visited.add(current)

        for neighbor, weight in adjacency.get(current, []):
            if neighbor in visited or neighbor in avoid:
                continue

            # Apply custom weight function if provided
            if weight_fn:
                weight = weight_fn(current, neighbor, weight)

            new_dist = current_dist + weight
            heapq.heappush(
                heap,
                PriorityItem(new_dist, neighbor, path + [neighbor]),
            )

    return []  # No path found


def a_star(
    adjacency: dict[int, list[tuple[int, float]]],
    system_info: dict[int, tuple[float, float, str]],
    start: int,
    end: int,
    avoid: set[int] | None = None,
    weight_fn: Callable[[int, int, float], float] | None = None,
) -> list[int]:
    """A* algorithm for shortest path with heuristic.

    Uses 2D map distance as heuristic for faster pathfinding.

    Args:
        adjacency: Graph adjacency list
        system_info: Dict of system_id -> (x, y, security_class)
        start: Starting system ID
        end: Destination system ID
        avoid: Set of system IDs to avoid
        weight_fn: Optional function to modify edge weights

    Returns:
        List of system IDs forming the path, or empty list if no path
    """
    if start not in adjacency or end not in adjacency:
        return []

    avoid = avoid or set()

    # Get destination coordinates for heuristic
    end_x, end_y, _ = system_info.get(end, (0, 0, "nullsec"))

    def heuristic(system_id: int) -> float:
        """Estimate distance to goal using map coordinates."""
        x, y, _ = system_info.get(system_id, (0, 0, "nullsec"))
        # Scale down since map coordinates are 0-1000 and we want jump estimates
        return math.sqrt((x - end_x) ** 2 + (y - end_y) ** 2) / 50

    # Priority queue: (f_score, system_id, path, g_score)
    heap: list[tuple[float, int, list[int], float]] = [(heuristic(start), start, [start], 0)]
    visited: set[int] = set()
    g_scores: dict[int, float] = {start: 0}

    while heap:
        _, current, path, g_score = heapq.heappop(heap)

        if current == end:
            return path

        if current in visited:
            continue
        visited.add(current)

        for neighbor, weight in adjacency.get(current, []):
            if neighbor in visited or neighbor in avoid:
                continue

            if weight_fn:
                weight = weight_fn(current, neighbor, weight)

            tentative_g = g_score + weight

            if neighbor not in g_scores or tentative_g < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor)
                heapq.heappush(
                    heap,
                    (f_score, neighbor, path + [neighbor], tentative_g),
                )

    return []


def get_weight_fn(
    route_type: RouteType,
    system_info: dict[int, tuple[float, float, str]],
) -> Callable[[int, int, float], float]:
    """Get weight function for route type.

    Args:
        route_type: Type of route preference
        system_info: System security info

    Returns:
        Weight modification function
    """
    if route_type == RouteType.SHORTEST:
        return lambda src, dst, w: 1.0  # All edges weight 1

    if route_type == RouteType.SECURE:

        def secure_weight(src: int, dst: int, base: float) -> float:
            _, _, sec_class = system_info.get(dst, (0, 0, "nullsec"))
            if sec_class == "highsec":
                return 1.0
            if sec_class == "lowsec":
                return 5.0  # Avoid lowsec
            return 10.0  # Strongly avoid nullsec

        return secure_weight

    if route_type == RouteType.INSECURE:

        def insecure_weight(src: int, dst: int, base: float) -> float:
            _, _, sec_class = system_info.get(dst, (0, 0, "nullsec"))
            if sec_class == "highsec":
                return 5.0  # Avoid highsec (gate camps less likely in lowsec)
            return 1.0

        return insecure_weight

    return lambda src, dst, w: w


def count_security(
    path: list[int],
    system_info: dict[int, tuple[float, float, str]],
) -> dict[str, int]:
    """Count systems by security class in path.

    Args:
        path: List of system IDs
        system_info: System security info

    Returns:
        Dict of security_class -> count
    """
    counts: dict[str, int] = {"highsec": 0, "lowsec": 0, "nullsec": 0, "wormhole": 0}

    for system_id in path:
        _, _, sec_class = system_info.get(system_id, (0, 0, "nullsec"))
        if sec_class in counts:
            counts[sec_class] += 1
        else:
            counts["nullsec"] += 1  # Default unknown to nullsec

    return counts


async def find_route(
    origin: int,
    destination: int,
    route_type: RouteType = RouteType.SHORTEST,
    db_path: str | None = None,
) -> RouteResult:
    """Find a route between two systems.

    Args:
        origin: Starting system ID
        destination: Destination system ID
        route_type: Route preference
        db_path: Optional database path

    Returns:
        RouteResult with path and metadata
    """
    adjacency, system_info = await load_graph_from_db(db_path)

    if origin not in adjacency:
        return RouteResult.not_found(f"Origin system {origin} not found in graph")
    if destination not in adjacency:
        return RouteResult.not_found(f"Destination system {destination} not found")

    weight_fn = get_weight_fn(route_type, system_info)

    # Use A* for faster pathfinding
    path = a_star(adjacency, system_info, origin, destination, weight_fn=weight_fn)

    if not path:
        return RouteResult.not_found()

    return RouteResult(
        path=path,
        total_jumps=len(path) - 1,
        security_summary=count_security(path, system_info),
    )


async def find_route_avoid(
    origin: int,
    destination: int,
    avoid_systems: list[int] | None = None,
    avoid_regions: list[int] | None = None,
    route_type: RouteType = RouteType.SHORTEST,
    db_path: str | None = None,
) -> RouteResult:
    """Find a route avoiding specified systems/regions.

    Args:
        origin: Starting system ID
        destination: Destination system ID
        avoid_systems: List of system IDs to avoid
        avoid_regions: List of region IDs to avoid
        route_type: Route preference
        db_path: Optional database path

    Returns:
        RouteResult with path and metadata
    """
    adjacency, system_info = await load_graph_from_db(db_path)

    avoid = set(avoid_systems or [])

    # If avoiding regions, load systems in those regions
    if avoid_regions:
        async with aiosqlite.connect(db_path or str(get_db_path())) as db:
            placeholders = ",".join("?" * len(avoid_regions))
            cursor = await db.execute(
                f"SELECT system_id FROM solar_systems WHERE region_id IN ({placeholders})",
                avoid_regions,
            )
            async for row in cursor:
                avoid.add(row[0])

    if origin not in adjacency:
        return RouteResult.not_found(f"Origin system {origin} not found in graph")
    if destination not in adjacency:
        return RouteResult.not_found(f"Destination system {destination} not found")

    weight_fn = get_weight_fn(route_type, system_info)

    path = a_star(adjacency, system_info, origin, destination, avoid=avoid, weight_fn=weight_fn)

    if not path:
        return RouteResult.not_found()

    return RouteResult(
        path=path,
        total_jumps=len(path) - 1,
        security_summary=count_security(path, system_info),
    )
