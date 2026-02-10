"""Jump drive calculations for capital ships."""

import math
from dataclasses import dataclass
from enum import StrEnum

from .data_loader import load_universe


class CapitalShipType(StrEnum):
    """Capital ship types with jump drives."""

    JUMP_FREIGHTER = "jump_freighter"
    CARRIER = "carrier"
    DREADNOUGHT = "dreadnought"
    FORCE_AUXILIARY = "force_auxiliary"
    SUPERCARRIER = "supercarrier"
    TITAN = "titan"
    RORQUAL = "rorqual"
    BLOPS = "black_ops"  # Black Ops battleships


# Base jump range in light years (before skills)
SHIP_BASE_RANGE: dict[CapitalShipType, float] = {
    CapitalShipType.JUMP_FREIGHTER: 5.0,
    CapitalShipType.CARRIER: 5.0,
    CapitalShipType.DREADNOUGHT: 5.0,
    CapitalShipType.FORCE_AUXILIARY: 5.0,
    CapitalShipType.SUPERCARRIER: 5.0,
    CapitalShipType.TITAN: 5.0,
    CapitalShipType.RORQUAL: 5.0,
    CapitalShipType.BLOPS: 4.0,  # Black Ops have shorter range
}

# Fuel consumption per light year (isotopes)
SHIP_FUEL_PER_LY: dict[CapitalShipType, int] = {
    CapitalShipType.JUMP_FREIGHTER: 1000,
    CapitalShipType.CARRIER: 1000,
    CapitalShipType.DREADNOUGHT: 1000,
    CapitalShipType.FORCE_AUXILIARY: 1000,
    CapitalShipType.SUPERCARRIER: 1500,
    CapitalShipType.TITAN: 2500,
    CapitalShipType.RORQUAL: 1200,
    CapitalShipType.BLOPS: 300,
}

# Light year conversion factor (normalized coords to LY)
# 1 LY = 9.461e15 m, coords normalized by 1e16
# Note: Using 2D distance (x, z), actual 3D would be more accurate
LY_CONVERSION = 1.057


@dataclass
class JumpRange:
    """Jump range calculation result."""

    base_range_ly: float
    max_range_ly: float
    jdc_level: int
    jfc_level: int
    fuel_per_ly: int


@dataclass
class SystemInRange:
    """A system within jump range."""

    name: str
    system_id: int
    distance_ly: float
    security: float
    category: str
    has_npc_station: bool  # Placeholder - would need station data
    fuel_required: int


@dataclass
class JumpLeg:
    """A single jump in a capital route."""

    from_system: str
    to_system: str
    distance_ly: float
    fuel_required: int
    fatigue_added_minutes: float
    total_fatigue_minutes: float
    wait_time_minutes: float


@dataclass
class JumpRoute:
    """Complete jump route for a capital ship."""

    from_system: str
    to_system: str
    ship_type: str
    total_jumps: int
    total_distance_ly: float
    total_fuel: int
    total_fatigue_minutes: float
    total_travel_time_minutes: float
    legs: list[JumpLeg]


def calculate_jump_range(
    ship_type: CapitalShipType,
    jdc_level: int = 5,
    jfc_level: int = 5,
) -> JumpRange:
    """
    Calculate jump range for a capital ship.

    Args:
        ship_type: Type of capital ship
        jdc_level: Jump Drive Calibration skill level (0-5)
        jfc_level: Jump Fuel Conservation skill level (0-5)

    Returns:
        JumpRange with base and max range
    """
    base_range = SHIP_BASE_RANGE.get(ship_type, 5.0)

    # JDC adds 25% per level to jump range
    jdc_bonus = 1.0 + (0.25 * jdc_level)
    max_range = base_range * jdc_bonus

    # JFC reduces fuel consumption by 10% per level
    base_fuel = SHIP_FUEL_PER_LY.get(ship_type, 1000)
    jfc_reduction = 1.0 - (0.10 * jfc_level)
    fuel_per_ly = int(base_fuel * jfc_reduction)

    return JumpRange(
        base_range_ly=base_range,
        max_range_ly=max_range,
        jdc_level=jdc_level,
        jfc_level=jfc_level,
        fuel_per_ly=fuel_per_ly,
    )


def calculate_distance_ly(system1: str, system2: str) -> float:
    """
    Calculate light year distance between two systems.

    Note: Uses 2D coordinates (x, z) from SDE. Actual 3D distance
    would require full coordinate data.

    Args:
        system1: First system name
        system2: Second system name

    Returns:
        Distance in light years
    """
    universe = load_universe()

    if system1 not in universe.systems:
        raise ValueError(f"Unknown system: {system1}")
    if system2 not in universe.systems:
        raise ValueError(f"Unknown system: {system2}")

    pos1 = universe.systems[system1].position
    pos2 = universe.systems[system2].position

    dx = pos2.x - pos1.x
    dy = pos2.y - pos1.y
    norm_dist = math.sqrt(dx * dx + dy * dy)

    return norm_dist * LY_CONVERSION


def find_systems_in_range(
    origin: str,
    max_range_ly: float,
    security_filter: str | None = None,
) -> list[SystemInRange]:
    """
    Find all systems within jump range of origin.

    Args:
        origin: Origin system name
        max_range_ly: Maximum jump range in light years
        security_filter: Optional filter - 'lowsec', 'nullsec', or None for all

    Returns:
        List of systems within range, sorted by distance
    """
    universe = load_universe()

    if origin not in universe.systems:
        raise ValueError(f"Unknown system: {origin}")

    origin_pos = universe.systems[origin].position
    results: list[SystemInRange] = []

    for name, system in universe.systems.items():
        if name == origin:
            continue

        # Apply security filter
        if security_filter:
            if security_filter == "lowsec" and system.category != "lowsec":
                continue
            if security_filter == "nullsec" and system.category != "nullsec":
                continue

        # Calculate distance
        dx = system.position.x - origin_pos.x
        dy = system.position.y - origin_pos.y
        norm_dist = math.sqrt(dx * dx + dy * dy)
        distance_ly = norm_dist * LY_CONVERSION

        if distance_ly <= max_range_ly:
            results.append(
                SystemInRange(
                    name=name,
                    system_id=system.id,
                    distance_ly=round(distance_ly, 2),
                    security=system.security,
                    category=system.category,
                    has_npc_station=system.has_npc_station,
                    fuel_required=0,  # Calculated separately
                )
            )

    # Sort by distance
    results.sort(key=lambda x: x.distance_ly)
    return results


def calculate_jump_fatigue(
    distance_ly: float,
    current_fatigue_minutes: float = 0,
) -> tuple[float, float, float]:
    """
    Calculate jump fatigue for a single jump.

    Args:
        distance_ly: Jump distance in light years
        current_fatigue_minutes: Current accumulated fatigue

    Returns:
        Tuple of (fatigue_added, new_total_fatigue, wait_time_minutes)
    """
    # Blue timer (jump activation delay) = distance * (1 + fatigue_multiplier) minutes
    # Red timer (fatigue) = current_blue_timer * 10
    # Fatigue multiplier starts at 0, increases with each jump

    # Simplified fatigue calculation
    # Each LY adds roughly 1 minute of blue timer base
    base_blue_timer = distance_ly

    # Fatigue multiplier (simplified - real formula is more complex)
    fatigue_multiplier = current_fatigue_minutes / 600  # Rough approximation
    blue_timer = base_blue_timer * (1 + fatigue_multiplier)

    # Fatigue added is blue timer * 10
    fatigue_added = blue_timer * 10

    # New total fatigue (capped at 5 hours = 300 minutes of blue timer equivalent)
    new_total = min(current_fatigue_minutes + fatigue_added, 3000)

    # Wait time before next jump is the blue timer
    wait_time = blue_timer

    return (round(fatigue_added, 1), round(new_total, 1), round(wait_time, 1))


def plan_jump_route(
    from_system: str,
    to_system: str,
    ship_type: CapitalShipType = CapitalShipType.JUMP_FREIGHTER,
    jdc_level: int = 5,
    jfc_level: int = 5,
    midpoints: list[str] | None = None,
) -> JumpRoute:
    """
    Plan a jump route between two systems.

    Args:
        from_system: Origin system
        to_system: Destination system
        ship_type: Type of capital ship
        jdc_level: Jump Drive Calibration skill level
        jfc_level: Jump Fuel Conservation skill level
        midpoints: Optional list of specific midpoint systems to use

    Returns:
        JumpRoute with complete route details
    """
    jump_range = calculate_jump_range(ship_type, jdc_level, jfc_level)

    # If midpoints specified, use them directly
    if midpoints:
        waypoints = [from_system] + midpoints + [to_system]
    else:
        # Auto-plan route using greedy approach
        waypoints = _auto_plan_waypoints(from_system, to_system, jump_range.max_range_ly)

    # Calculate each leg
    legs: list[JumpLeg] = []
    total_fuel = 0
    total_distance = 0.0
    current_fatigue = 0.0
    total_wait_time = 0.0

    for i in range(len(waypoints) - 1):
        origin = waypoints[i]
        dest = waypoints[i + 1]

        distance = calculate_distance_ly(origin, dest)
        if distance > jump_range.max_range_ly:
            raise ValueError(
                f"Jump from {origin} to {dest} ({distance:.1f} LY) "
                f"exceeds max range ({jump_range.max_range_ly:.1f} LY)"
            )

        fuel = int(distance * jump_range.fuel_per_ly)
        fatigue_added, current_fatigue, wait_time = calculate_jump_fatigue(
            distance, current_fatigue
        )

        legs.append(
            JumpLeg(
                from_system=origin,
                to_system=dest,
                distance_ly=round(distance, 2),
                fuel_required=fuel,
                fatigue_added_minutes=fatigue_added,
                total_fatigue_minutes=current_fatigue,
                wait_time_minutes=wait_time,
            )
        )

        total_fuel += fuel
        total_distance += distance
        total_wait_time += wait_time

    return JumpRoute(
        from_system=from_system,
        to_system=to_system,
        ship_type=ship_type.value,
        total_jumps=len(legs),
        total_distance_ly=round(total_distance, 2),
        total_fuel=total_fuel,
        total_fatigue_minutes=current_fatigue,
        total_travel_time_minutes=round(total_wait_time, 1),
        legs=legs,
    )


def _auto_plan_waypoints(
    from_system: str,
    to_system: str,
    max_range_ly: float,
) -> list[str]:
    """
    Automatically plan waypoints for a jump route using greedy approach.

    Finds systems that get closest to destination while staying in range.
    Prefers lowsec over nullsec for safety (NPC stations for cynos).

    Args:
        from_system: Origin system
        to_system: Destination system
        max_range_ly: Maximum jump range

    Returns:
        List of waypoint system names including origin and destination
    """
    waypoints = [from_system]
    current = from_system

    # Safety limit to prevent infinite loops
    max_iterations = 50

    for _ in range(max_iterations):
        if current == to_system:
            break

        # Check if we can reach destination directly
        try:
            direct_distance = calculate_distance_ly(current, to_system)
            if direct_distance <= max_range_ly:
                waypoints.append(to_system)
                break
        except ValueError:
            break

        # Find systems in range
        in_range = find_systems_in_range(current, max_range_ly)

        if not in_range:
            raise ValueError(f"No systems in range from {current}")

        # Find the system that gets us closest to destination
        best_system = None
        best_remaining_distance = float("inf")

        for candidate in in_range:
            try:
                remaining = calculate_distance_ly(candidate.name, to_system)
                # Prefer lowsec over nullsec (safer for cynos)
                # Add small penalty for nullsec
                if candidate.category == "nullsec":
                    remaining += 0.5

                if remaining < best_remaining_distance:
                    best_remaining_distance = remaining
                    best_system = candidate.name
            except ValueError:
                continue

        if best_system is None:
            raise ValueError(f"Cannot find path from {current} to {to_system}")

        waypoints.append(best_system)
        current = best_system

    if waypoints[-1] != to_system:
        raise ValueError(f"Could not complete route to {to_system}")

    return waypoints
