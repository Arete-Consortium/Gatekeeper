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

# Fuel isotope types - EVE type IDs
FUEL_ISOTOPES: dict[str, tuple[int, str]] = {
    "nitrogen": (17888, "Nitrogen Isotopes"),
    "helium": (16274, "Helium Isotopes"),
    "oxygen": (17887, "Oxygen Isotopes"),
    "hydrogen": (17889, "Hydrogen Isotopes"),
}

# Default fuel type by ship category (user can override based on their specific hull race)
DEFAULT_FUEL_TYPE: dict[CapitalShipType, str] = {
    CapitalShipType.JUMP_FREIGHTER: "nitrogen",
    CapitalShipType.CARRIER: "helium",
    CapitalShipType.DREADNOUGHT: "helium",
    CapitalShipType.FORCE_AUXILIARY: "helium",
    CapitalShipType.SUPERCARRIER: "helium",
    CapitalShipType.TITAN: "helium",
    CapitalShipType.RORQUAL: "oxygen",
    CapitalShipType.BLOPS: "hydrogen",
}

# Light year conversion factor (normalized coords to LY)
# Coords are EVE meters / 1e15, so 1 LY = 9.461e15m / 1e15 = 9.461 units.
# Conversion = 1 / 9.461 = 0.10570
# Note: Using 2D distance (x-z plane). Distances are approximate
# since EVE's universe has a Y component we don't capture.
LY_CONVERSION = 0.10570


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
    # Destination system intel (populated after route calculation)
    to_system_id: int = 0
    to_security_status: float = 0.0
    to_category: str = ""
    to_region_name: str = ""
    to_has_npc_station: bool = False


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
    fuel_type_id: int = 0
    fuel_type_name: str = ""


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


# Categories where a cyno can be lit (jump destination).
# Highsec: cynos are blocked. WH space: no cyno mechanics.
# Pochven: can jump OUT of but not INTO (no cyno).
CYNO_VALID_CATEGORIES = {"lowsec", "nullsec"}


def find_systems_in_range(
    origin: str,
    max_range_ly: float,
    security_filter: str | None = None,
    cyno_only: bool = False,
) -> list[SystemInRange]:
    """
    Find all systems within jump range of origin.

    Args:
        origin: Origin system name
        max_range_ly: Maximum jump range in light years
        security_filter: Optional filter - 'lowsec', 'nullsec', or None for all
        cyno_only: If True, only include systems where a cyno can be lit
            (lowsec/nullsec). Excludes highsec, WH, and Pochven.

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

        # Cyno filter: only lowsec/nullsec can receive jumps
        # Pochven shows as nullsec but cannot receive cynos (jump OUT only)
        if cyno_only:
            if system.category not in CYNO_VALID_CATEGORIES:
                continue
            if system.region_name == "Pochven":
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
    fuel_type: str | None = None,
    prefer_stations: bool = True,
) -> JumpRoute:
    """Plan a jump route between two systems.

    Args:
        from_system: Origin system.
        to_system: Destination system.
        ship_type: Type of capital ship.
        jdc_level: Jump Drive Calibration skill level.
        jfc_level: Jump Fuel Conservation skill level.
        midpoints: Optional list of specific midpoint systems to use.
        fuel_type: Fuel isotope key (nitrogen/helium/oxygen/hydrogen).
            Defaults to the ship category's default fuel type.
        prefer_stations: Prefer systems with NPC stations for waypoints.

    Returns:
        JumpRoute with complete route details.
    """
    jump_range = calculate_jump_range(ship_type, jdc_level, jfc_level)
    universe = load_universe()

    # Resolve fuel type
    resolved_fuel = fuel_type or DEFAULT_FUEL_TYPE.get(ship_type, "helium")
    fuel_info = FUEL_ISOTOPES.get(resolved_fuel, FUEL_ISOTOPES["helium"])
    fuel_type_id, fuel_type_name = fuel_info

    # If midpoints specified, use them directly
    if midpoints:
        waypoints = [from_system] + midpoints + [to_system]
    else:
        # Auto-plan route using greedy approach
        waypoints = _auto_plan_waypoints(
            from_system, to_system, jump_range.max_range_ly, prefer_stations
        )

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

        # Look up destination system intel
        dest_sys = universe.systems.get(dest)
        legs.append(
            JumpLeg(
                from_system=origin,
                to_system=dest,
                distance_ly=round(distance, 2),
                fuel_required=fuel,
                fatigue_added_minutes=fatigue_added,
                total_fatigue_minutes=current_fatigue,
                wait_time_minutes=wait_time,
                to_system_id=dest_sys.id if dest_sys else 0,
                to_security_status=dest_sys.security if dest_sys else 0.0,
                to_category=dest_sys.category if dest_sys else "",
                to_region_name=dest_sys.region_name if dest_sys else "",
                to_has_npc_station=dest_sys.has_npc_station if dest_sys else False,
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
        fuel_type_id=fuel_type_id,
        fuel_type_name=fuel_type_name,
    )


def _auto_plan_waypoints(
    from_system: str,
    to_system: str,
    max_range_ly: float,
    prefer_stations: bool = True,
) -> list[str]:
    """Automatically plan waypoints for a jump route using greedy approach.

    Finds systems that get closest to destination while staying in range.
    Scores candidates by remaining distance with penalties/bonuses for
    security class and NPC station availability.

    Args:
        from_system: Origin system.
        to_system: Destination system.
        max_range_ly: Maximum jump range.
        prefer_stations: Prefer systems with NPC stations.

    Returns:
        List of waypoint system names including origin and destination.
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

        # Find systems in range (cyno-eligible only: lowsec/nullsec)
        in_range = find_systems_in_range(current, max_range_ly, cyno_only=True)

        if not in_range:
            raise ValueError(f"No systems in range from {current}")

        # Find the system that gets us closest to destination
        best_system = None
        best_score = float("inf")

        for candidate in in_range:
            try:
                remaining = calculate_distance_ly(candidate.name, to_system)

                # Apply scoring penalties
                score = remaining

                # Prefer lowsec over nullsec (safer for cynos)
                if candidate.category == "nullsec":
                    score += 0.5

                # Prefer systems with NPC stations (can dock, safer cyno)
                if prefer_stations and not candidate.has_npc_station:
                    score += 1.0

                if score < best_score:
                    best_score = score
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
