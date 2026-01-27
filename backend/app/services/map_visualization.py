"""Map visualization service for route and region rendering.

Provides data structures for rendering EVE Online routes and regions
with security status coloring, threat overlays, and connection types.
"""

from dataclasses import dataclass, field
from enum import Enum

from .data_loader import load_universe


class SecurityLevel(str, Enum):
    """Security status classification."""

    high_sec = "high_sec"  # 0.5 to 1.0
    low_sec = "low_sec"  # 0.1 to 0.4
    null_sec = "null_sec"  # -1.0 to 0.0


class ConnectionType(str, Enum):
    """Types of connections between systems."""

    stargate = "stargate"
    jump_bridge = "jump_bridge"
    cyno_jump = "cyno_jump"
    wormhole = "wormhole"


class ThreatLevel(str, Enum):
    """Threat classification for systems."""

    safe = "safe"
    caution = "caution"
    dangerous = "dangerous"
    deadly = "deadly"


@dataclass
class SystemNode:
    """System node for map rendering."""

    system_id: int
    system_name: str
    security_status: float
    security_level: SecurityLevel
    region_name: str | None = None
    constellation_name: str | None = None
    x: float = 0.0
    y: float = 0.0
    threat_level: ThreatLevel = ThreatLevel.safe
    kills_last_hour: int = 0
    npc_kills_last_hour: int = 0
    jumps_last_hour: int = 0
    is_route_system: bool = False
    route_index: int | None = None


@dataclass
class SystemConnection:
    """Connection between two systems."""

    from_system_id: int
    to_system_id: int
    from_system_name: str
    to_system_name: str
    connection_type: ConnectionType
    is_route_connection: bool = False


@dataclass
class RouteVisualization:
    """Complete route visualization data."""

    route_id: str
    systems: list[SystemNode] = field(default_factory=list)
    connections: list[SystemConnection] = field(default_factory=list)
    total_jumps: int = 0
    high_sec_jumps: int = 0
    low_sec_jumps: int = 0
    null_sec_jumps: int = 0
    dangerous_systems: list[str] = field(default_factory=list)
    jump_bridge_used: int = 0
    cyno_jumps_used: int = 0


@dataclass
class RegionMapData:
    """Region map with all systems and connections."""

    region_id: int
    region_name: str
    systems: list[SystemNode] = field(default_factory=list)
    connections: list[SystemConnection] = field(default_factory=list)
    bounds: dict = field(default_factory=lambda: {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0})


def get_security_level(security_status: float) -> SecurityLevel:
    """Classify security status into level."""
    if security_status >= 0.5:
        return SecurityLevel.high_sec
    elif security_status > 0.0:
        return SecurityLevel.low_sec
    else:
        return SecurityLevel.null_sec


def get_security_color(security_status: float) -> str:
    """Get hex color for security status."""
    if security_status >= 0.9:
        return "#2E8B57"  # Sea green - very safe
    elif security_status >= 0.7:
        return "#3CB371"  # Medium sea green
    elif security_status >= 0.5:
        return "#90EE90"  # Light green
    elif security_status >= 0.3:
        return "#FFA500"  # Orange
    elif security_status > 0.0:
        return "#FF4500"  # Orange red
    elif security_status > -0.5:
        return "#DC143C"  # Crimson
    else:
        return "#8B0000"  # Dark red


def get_threat_color(threat_level: ThreatLevel) -> str:
    """Get hex color for threat level overlay."""
    colors = {
        ThreatLevel.safe: "#00FF00",  # Green
        ThreatLevel.caution: "#FFFF00",  # Yellow
        ThreatLevel.dangerous: "#FF8000",  # Orange
        ThreatLevel.deadly: "#FF0000",  # Red
    }
    return colors.get(threat_level, "#00FF00")


def create_system_node(
    system_id: int,
    system_name: str,
    security_status: float,
    region_name: str | None = None,
    threat_level: ThreatLevel = ThreatLevel.safe,
    kills: int = 0,
    npc_kills: int = 0,
    jumps: int = 0,
) -> SystemNode:
    """Create a system node for visualization."""
    return SystemNode(
        system_id=system_id,
        system_name=system_name,
        security_status=round(security_status, 1),
        security_level=get_security_level(security_status),
        region_name=region_name,
        threat_level=threat_level,
        kills_last_hour=kills,
        npc_kills_last_hour=npc_kills,
        jumps_last_hour=jumps,
    )


def get_route_visualization(
    route: list[str],
    jump_bridges: list[tuple[str, str]] | None = None,
    cyno_jumps: list[tuple[str, str]] | None = None,
    threat_data: dict[str, ThreatLevel] | None = None,
) -> RouteVisualization | None:
    """
    Generate visualization data for a route.

    Args:
        route: List of system names in order
        jump_bridges: List of (from, to) tuples for jump bridge connections
        cyno_jumps: List of (from, to) tuples for cyno jump connections
        threat_data: Dict mapping system name to threat level

    Returns:
        RouteVisualization with all nodes and connections
    """
    if not route:
        return None

    universe = load_universe()
    if not universe:
        return None

    jump_bridges = jump_bridges or []
    cyno_jumps = cyno_jumps or []
    threat_data = threat_data or {}

    # Build sets for quick lookup
    jb_connections = {(a, b) for a, b in jump_bridges} | {(b, a) for a, b in jump_bridges}
    cyno_connections = {(a, b) for a, b in cyno_jumps} | {(b, a) for a, b in cyno_jumps}

    route_id = f"route-{route[0]}-{route[-1]}"
    systems: list[SystemNode] = []
    connections: list[SystemConnection] = []
    high_sec = low_sec = null_sec = 0
    jb_count = cyno_count = 0
    dangerous: list[str] = []

    for i, system_name in enumerate(route):
        system = universe.systems.get(system_name)
        if not system:
            continue

        threat = threat_data.get(system_name, ThreatLevel.safe)
        node = create_system_node(
            system_id=system.id,
            system_name=system_name,
            security_status=system.security,
            region_name=system.region_name,
            threat_level=threat,
        )
        node.is_route_system = True
        node.route_index = i
        systems.append(node)

        # Count security types
        if node.security_level == SecurityLevel.high_sec:
            high_sec += 1
        elif node.security_level == SecurityLevel.low_sec:
            low_sec += 1
        else:
            null_sec += 1

        # Track dangerous systems
        if threat in (ThreatLevel.dangerous, ThreatLevel.deadly):
            dangerous.append(system_name)

        # Create connection to previous system
        if i > 0:
            prev_name = route[i - 1]
            prev_system = universe.systems.get(prev_name)
            if prev_system:
                # Determine connection type
                if (prev_name, system_name) in cyno_connections:
                    conn_type = ConnectionType.cyno_jump
                    cyno_count += 1
                elif (prev_name, system_name) in jb_connections:
                    conn_type = ConnectionType.jump_bridge
                    jb_count += 1
                else:
                    conn_type = ConnectionType.stargate

                connections.append(
                    SystemConnection(
                        from_system_id=prev_system.id,
                        to_system_id=system.id,
                        from_system_name=prev_name,
                        to_system_name=system_name,
                        connection_type=conn_type,
                        is_route_connection=True,
                    )
                )

    return RouteVisualization(
        route_id=route_id,
        systems=systems,
        connections=connections,
        total_jumps=len(route) - 1 if route else 0,
        high_sec_jumps=high_sec,
        low_sec_jumps=low_sec,
        null_sec_jumps=null_sec,
        dangerous_systems=dangerous,
        jump_bridge_used=jb_count,
        cyno_jumps_used=cyno_count,
    )


def get_region_map(region_name: str) -> RegionMapData | None:
    """
    Get all systems and connections for a region.

    Args:
        region_name: Name of the region

    Returns:
        RegionMapData with all systems and gate connections
    """
    universe = load_universe()
    if not universe:
        return None

    # Find all systems in the region
    region_systems: dict[str, SystemNode] = {}
    for system_name, system in universe.systems.items():
        if system.region_name and system.region_name.lower() == region_name.lower():
            node = create_system_node(
                system_id=system.id,
                system_name=system_name,
                security_status=system.security,
                region_name=system.region_name,
            )
            region_systems[system_name] = node

    if not region_systems:
        return None

    # Find all gates between systems in this region
    connections: list[SystemConnection] = []
    seen_connections: set[tuple[str, str]] = set()

    for gate in universe.gates:
        if gate.from_system in region_systems and gate.to_system in region_systems:
            # Avoid duplicate connections (A->B and B->A)
            key = tuple(sorted([gate.from_system, gate.to_system]))
            if key not in seen_connections:
                seen_connections.add(key)
                from_sys = universe.systems[gate.from_system]
                to_sys = universe.systems[gate.to_system]
                connections.append(
                    SystemConnection(
                        from_system_id=from_sys.id,
                        to_system_id=to_sys.id,
                        from_system_name=gate.from_system,
                        to_system_name=gate.to_system,
                        connection_type=ConnectionType.stargate,
                    )
                )

    # Get region ID from first system (they should all be the same)
    region_id = 0
    for system_name in region_systems:
        system = universe.systems.get(system_name)
        if system and system.region_id:
            region_id = system.region_id
            break

    return RegionMapData(
        region_id=region_id,
        region_name=region_name,
        systems=list(region_systems.values()),
        connections=connections,
    )


def get_systems_in_range(
    center_system: str,
    max_jumps: int = 5,
    include_connections: bool = True,
) -> tuple[list[SystemNode], list[SystemConnection]] | None:
    """
    Get all systems within a number of jumps from center.

    Args:
        center_system: System to center on
        max_jumps: Maximum jump distance
        include_connections: Whether to include gate connections

    Returns:
        Tuple of (systems, connections) or None if center not found
    """
    universe = load_universe()
    if not universe or center_system not in universe.systems:
        return None

    # Build adjacency map
    adjacency: dict[str, set[str]] = {}
    for gate in universe.gates:
        if gate.from_system not in adjacency:
            adjacency[gate.from_system] = set()
        if gate.to_system not in adjacency:
            adjacency[gate.to_system] = set()
        adjacency[gate.from_system].add(gate.to_system)
        adjacency[gate.to_system].add(gate.from_system)

    # BFS to find all systems in range
    visited: dict[str, int] = {center_system: 0}
    queue = [center_system]

    while queue:
        current = queue.pop(0)
        current_distance = visited[current]

        if current_distance >= max_jumps:
            continue

        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                visited[neighbor] = current_distance + 1
                queue.append(neighbor)

    # Create system nodes
    systems: list[SystemNode] = []
    for system_name, distance in visited.items():
        system = universe.systems.get(system_name)
        if system:
            node = create_system_node(
                system_id=system.id,
                system_name=system_name,
                security_status=system.security,
                region_name=system.region_name,
            )
            node.route_index = distance  # Use route_index as jump distance
            systems.append(node)

    # Create connections if requested
    connections: list[SystemConnection] = []
    if include_connections:
        seen: set[tuple[str, str]] = set()
        for system_name in visited:
            for neighbor in adjacency.get(system_name, []):
                if neighbor in visited:
                    key = tuple(sorted([system_name, neighbor]))
                    if key not in seen:
                        seen.add(key)
                        from_sys = universe.systems[system_name]
                        to_sys = universe.systems[neighbor]
                        connections.append(
                            SystemConnection(
                                from_system_id=from_sys.id,
                                to_system_id=to_sys.id,
                                from_system_name=system_name,
                                to_system_name=neighbor,
                                connection_type=ConnectionType.stargate,
                            )
                        )

    return systems, connections


def get_constellation_map(constellation_name: str) -> RegionMapData | None:
    """
    Get all systems and connections for a constellation.

    Args:
        constellation_name: Name of the constellation

    Returns:
        RegionMapData (reused structure) with constellation data
    """
    universe = load_universe()
    if not universe:
        return None

    # Find all systems in the constellation
    const_systems: dict[str, SystemNode] = {}
    region_name = None

    for system_name, system in universe.systems.items():
        if (
            system.constellation_name
            and system.constellation_name.lower() == constellation_name.lower()
        ):
            node = create_system_node(
                system_id=system.id,
                system_name=system_name,
                security_status=system.security,
                region_name=system.region_name,
            )
            node.constellation_name = system.constellation_name
            const_systems[system_name] = node
            if not region_name and system.region_name:
                region_name = system.region_name

    if not const_systems:
        return None

    # Find all gates between systems in this constellation
    connections: list[SystemConnection] = []
    seen_connections: set[tuple[str, str]] = set()

    for gate in universe.gates:
        if gate.from_system in const_systems and gate.to_system in const_systems:
            key = tuple(sorted([gate.from_system, gate.to_system]))
            if key not in seen_connections:
                seen_connections.add(key)
                from_sys = universe.systems[gate.from_system]
                to_sys = universe.systems[gate.to_system]
                connections.append(
                    SystemConnection(
                        from_system_id=from_sys.id,
                        to_system_id=to_sys.id,
                        from_system_name=gate.from_system,
                        to_system_name=gate.to_system,
                        connection_type=ConnectionType.stargate,
                    )
                )

    return RegionMapData(
        region_id=0,  # Constellation doesn't have region ID
        region_name=region_name or constellation_name,
        systems=list(const_systems.values()),
        connections=connections,
    )
