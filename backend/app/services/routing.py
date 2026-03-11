import math

from ..models.route import RouteHop, RouteResponse, WaypointLeg, WaypointRouteResponse
from .data_loader import load_risk_config, load_universe
from .jumpbridge import get_active_bridges
from .pochven import get_active_pochven, is_pochven_enabled
from .risk_engine import compute_risk
from .thera import get_active_thera

# Edge type markers for distinguishing gates from bridges
EDGE_GATE = "gate"
EDGE_BRIDGE = "bridge"
EDGE_THERA = "thera"
EDGE_POCHVEN = "pochven"
EDGE_WORMHOLE = "wormhole"


def _build_graph(
    avoid: set[str] | None = None,
    use_bridges: bool = False,
    use_thera: bool = False,
    use_pochven: bool = False,
    use_wormholes: bool = False,
) -> tuple[dict[str, dict[str, float]], dict[tuple[str, str], str]]:
    """
    Build navigation graph from universe data.

    Args:
        avoid: Set of system names to exclude from the graph
        use_bridges: Whether to include Ansiblex jump bridges
        use_thera: Whether to include Thera wormhole shortcuts
        use_pochven: Whether to include Pochven filament connections
        use_wormholes: Whether to include user-submitted wormhole connections

    Returns:
        Tuple of (adjacency dict, edge type dict)
        - Adjacency: system -> {neighbor -> distance}
        - Edge types: (from, to) -> "gate", "bridge", "thera", "pochven", or "wormhole"
    """
    universe = load_universe()
    avoid = avoid or set()

    # Exclude avoided systems from the graph
    graph: dict[str, dict[str, float]] = {
        name: {} for name in universe.systems if name not in avoid
    }
    edge_types: dict[tuple[str, str], str] = {}

    # Add stargate connections
    for gate in universe.gates:
        # Skip gates involving avoided systems
        if gate.from_system in avoid or gate.to_system in avoid:
            continue
        if gate.from_system in graph and gate.to_system in graph:
            graph[gate.from_system][gate.to_system] = gate.distance
            graph[gate.to_system][gate.from_system] = gate.distance
            edge_types[(gate.from_system, gate.to_system)] = EDGE_GATE
            edge_types[(gate.to_system, gate.from_system)] = EDGE_GATE

    # Add jump bridge connections
    if use_bridges:
        bridges = get_active_bridges()
        for bridge in bridges:
            if bridge.from_system in avoid or bridge.to_system in avoid:
                continue
            if bridge.from_system in graph and bridge.to_system in graph:
                # Jump bridges have distance 1 (instant travel)
                # Only add if not already connected (or prefer bridge)
                graph[bridge.from_system][bridge.to_system] = 1.0
                graph[bridge.to_system][bridge.from_system] = 1.0
                edge_types[(bridge.from_system, bridge.to_system)] = EDGE_BRIDGE
                edge_types[(bridge.to_system, bridge.from_system)] = EDGE_BRIDGE

    # Add Thera wormhole connections
    if use_thera:
        thera_connections = get_active_thera()
        for conn in thera_connections:
            if conn.in_system_name in avoid or conn.out_system_name in avoid:
                continue
            if conn.in_system_name in graph and conn.out_system_name in graph:
                # Weight 2: system→Thera + Thera→system
                graph[conn.in_system_name][conn.out_system_name] = 2.0
                graph[conn.out_system_name][conn.in_system_name] = 2.0
                edge_types[(conn.in_system_name, conn.out_system_name)] = EDGE_THERA
                edge_types[(conn.out_system_name, conn.in_system_name)] = EDGE_THERA

    # Add Pochven filament connections
    if use_pochven and is_pochven_enabled():
        pochven_connections = get_active_pochven()
        for pconn in pochven_connections:
            if pconn.from_system in avoid or pconn.to_system in avoid:
                continue
            if pconn.from_system in graph and pconn.to_system in graph:
                # Weight 1: direct filament connection
                graph[pconn.from_system][pconn.to_system] = 1.0
                edge_types[(pconn.from_system, pconn.to_system)] = EDGE_POCHVEN
                if pconn.bidirectional:
                    graph[pconn.to_system][pconn.from_system] = 1.0
                    edge_types[(pconn.to_system, pconn.from_system)] = EDGE_POCHVEN

    # Add user-submitted wormhole connections
    if use_wormholes:
        from .wormhole import get_wormhole_service

        wh_service = get_wormhole_service()
        for wh_conn in wh_service.get_active_wormholes():
            if wh_conn.from_system in avoid or wh_conn.to_system in avoid:
                continue
            if wh_conn.from_system in graph and wh_conn.to_system in graph:
                # Weight 1: wormhole is direct connection
                graph[wh_conn.from_system][wh_conn.to_system] = 1.0
                edge_types[(wh_conn.from_system, wh_conn.to_system)] = EDGE_WORMHOLE
                if wh_conn.bidirectional:
                    graph[wh_conn.to_system][wh_conn.from_system] = 1.0
                    edge_types[(wh_conn.to_system, wh_conn.from_system)] = EDGE_WORMHOLE

    return graph, edge_types


def _dijkstra(
    graph: dict[str, dict[str, float]], start: str, end: str, profile: str
) -> tuple[list[str], float]:
    cfg = load_risk_config()
    profile_cfg = cfg.routing_profiles.get(profile, cfg.routing_profiles["shortest"])
    risk_factor = profile_cfg.get("risk_factor", 0.0)

    dist: dict[str, float] = dict.fromkeys(graph, math.inf)
    prev: dict[str, str | None] = dict.fromkeys(graph)
    visited: set[str] = set()

    dist[start] = 0.0

    while visited != set(graph.keys()):
        current = min((n for n in graph if n not in visited), key=lambda n: dist[n])
        if dist[current] == math.inf:
            break
        visited.add(current)
        if current == end:
            break

        for neighbor, base_cost in graph[current].items():
            risk_report = compute_risk(neighbor)
            risk_penalty = risk_factor * (risk_report.score / 100.0)
            cost = base_cost * (1.0 + risk_penalty)

            alt = dist[current] + cost
            if alt < dist[neighbor]:
                dist[neighbor] = alt
                prev[neighbor] = current

    if dist[end] == math.inf:
        return [], math.inf

    node = end
    path: list[str] = []
    while node is not None:
        path.append(node)
        node = prev[node]  # type: ignore
    path.reverse()
    return path, dist[end]


def _resolve_system_name(name: str, systems: dict) -> str:
    """Resolve a system name case-insensitively. Returns canonical name or original."""
    if name in systems:
        return name
    lower = name.lower()
    for canonical in systems:
        if canonical.lower() == lower:
            return canonical
    return name


def compute_route(
    from_system: str,
    to_system: str,
    profile: str = "shortest",
    avoid: set[str] | None = None,
    use_bridges: bool = False,
    use_thera: bool = False,
    use_pochven: bool = False,
    use_wormholes: bool = False,
) -> RouteResponse:
    """
    Compute a route between two systems.

    Args:
        from_system: Origin system name
        to_system: Destination system name
        profile: Routing profile ('shortest', 'safer', 'paranoid')
        avoid: Set of system names to avoid in routing
        use_bridges: Whether to use Ansiblex jump bridges
        use_thera: Whether to use Thera wormhole shortcuts
        use_pochven: Whether to use Pochven filament connections
        use_wormholes: Whether to use user-submitted wormhole connections

    Returns:
        RouteResponse with path details
    """
    universe = load_universe()
    avoid = avoid or set()

    # Case-insensitive system name resolution
    from_system = _resolve_system_name(from_system, universe.systems)
    to_system = _resolve_system_name(to_system, universe.systems)

    if from_system not in universe.systems:
        raise ValueError(f"Unknown from_system: {from_system}")
    if to_system not in universe.systems:
        raise ValueError(f"Unknown to_system: {to_system}")
    if from_system in avoid:
        raise ValueError(f"Cannot avoid origin system: {from_system}")
    if to_system in avoid:
        raise ValueError(f"Cannot avoid destination system: {to_system}")

    graph, edge_types = _build_graph(
        avoid,
        use_bridges=use_bridges,
        use_thera=use_thera,
        use_pochven=use_pochven,
        use_wormholes=use_wormholes,
    )
    path_names, total_cost = _dijkstra(graph, from_system, to_system, profile)
    if not path_names:
        raise ValueError("No route found")

    hops: list[RouteHop] = []
    total_risk = 0.0
    max_risk = 0.0
    cumulative_cost = 0.0
    bridges_used = 0
    thera_used = 0
    pochven_used = 0
    wormholes_used = 0

    for idx, name in enumerate(path_names):
        rr = compute_risk(name)
        total_risk += rr.score
        max_risk = max(max_risk, rr.score)

        # Determine connection type
        connection_type = EDGE_GATE
        if idx > 0:
            prev_name = path_names[idx - 1]
            edge_cost = graph[prev_name][name]
            cumulative_cost += edge_cost
            connection_type = edge_types.get((prev_name, name), EDGE_GATE)
            if connection_type == EDGE_BRIDGE:
                bridges_used += 1
            elif connection_type == EDGE_THERA:
                thera_used += 1
            elif connection_type == EDGE_POCHVEN:
                pochven_used += 1
            elif connection_type == EDGE_WORMHOLE:
                wormholes_used += 1

        hops.append(
            RouteHop(
                system_name=name,
                system_id=universe.systems[name].id,
                cumulative_jumps=idx,
                cumulative_cost=cumulative_cost,
                risk_score=rr.score,
                connection_type=connection_type,
                pirate_suppressed=rr.pirate_suppressed,
            )
        )

    avg_risk = total_risk / len(path_names)

    return RouteResponse(
        from_system=from_system,
        to_system=to_system,
        profile=profile,
        total_jumps=len(path_names) - 1,
        total_cost=total_cost,
        max_risk=max_risk,
        avg_risk=avg_risk,
        path=hops,
        bridges_used=bridges_used,
        thera_used=thera_used,
        pochven_used=pochven_used,
        wormholes_used=wormholes_used,
    )


def compute_waypoint_route(
    from_system: str,
    waypoints: list[str],
    profile: str = "shortest",
    avoid: set[str] | None = None,
    use_bridges: bool = False,
    use_thera: bool = False,
    use_pochven: bool = False,
    use_wormholes: bool = False,
    optimize: bool = False,
) -> WaypointRouteResponse:
    """
    Compute a multi-stop route through waypoints.

    Args:
        from_system: Origin system name
        waypoints: Ordered list of waypoint system names
        profile: Routing profile ('shortest', 'safer', 'paranoid')
        avoid: Set of system names to avoid
        use_bridges: Whether to use Ansiblex jump bridges
        use_thera: Whether to use Thera wormhole shortcuts
        use_pochven: Whether to use Pochven filament connections
        use_wormholes: Whether to use user-submitted wormhole connections
        optimize: If True, reorder waypoints using nearest-neighbor heuristic

    Returns:
        WaypointRouteResponse with leg details
    """
    universe = load_universe()
    avoid = avoid or set()

    # Validate all systems
    if from_system not in universe.systems:
        raise ValueError(f"Unknown from_system: {from_system}")
    for wp in waypoints:
        if wp not in universe.systems:
            raise ValueError(f"Unknown waypoint system: {wp}")

    original_order = list(waypoints)
    ordered_waypoints = list(waypoints)

    # Nearest-neighbor optimization
    if optimize and len(waypoints) > 1:
        remaining = list(waypoints)
        optimized: list[str] = []
        current = from_system

        while remaining:
            best_wp = None
            best_jumps = float("inf")
            for wp in remaining:
                try:
                    route = compute_route(
                        current,
                        wp,
                        profile,
                        avoid=avoid,
                        use_bridges=use_bridges,
                        use_thera=use_thera,
                        use_pochven=use_pochven,
                        use_wormholes=use_wormholes,
                    )
                    if route.total_jumps < best_jumps:
                        best_jumps = route.total_jumps
                        best_wp = wp
                except ValueError:
                    continue

            if best_wp is None:
                raise ValueError(f"No route found to remaining waypoints from {current}")
            optimized.append(best_wp)
            remaining.remove(best_wp)
            current = best_wp

        ordered_waypoints = optimized

    # Compute legs
    legs: list[WaypointLeg] = []
    total_jumps = 0
    total_cost = 0.0
    total_bridges = 0
    total_thera = 0
    total_pochven = 0
    total_wormholes = 0
    current = from_system

    for wp in ordered_waypoints:
        route = compute_route(
            current,
            wp,
            profile,
            avoid=avoid,
            use_bridges=use_bridges,
            use_thera=use_thera,
            use_pochven=use_pochven,
            use_wormholes=use_wormholes,
        )
        leg = WaypointLeg(
            from_system=current,
            to_system=wp,
            jumps=route.total_jumps,
            cost=route.total_cost,
            bridges_used=route.bridges_used,
            thera_used=route.thera_used,
            pochven_used=route.pochven_used,
            wormholes_used=route.wormholes_used,
            path_systems=[hop.system_name for hop in route.path],
        )
        legs.append(leg)
        total_jumps += route.total_jumps
        total_cost += route.total_cost
        total_bridges += route.bridges_used
        total_thera += route.thera_used
        total_pochven += route.pochven_used
        total_wormholes += route.wormholes_used
        current = wp

    return WaypointRouteResponse(
        from_system=from_system,
        waypoints=ordered_waypoints,
        optimized=optimize,
        original_order=original_order if optimize else [],
        total_jumps=total_jumps,
        total_cost=total_cost,
        legs=legs,
        total_bridges_used=total_bridges,
        total_thera_used=total_thera,
        total_pochven_used=total_pochven,
        total_wormholes_used=total_wormholes,
    )
