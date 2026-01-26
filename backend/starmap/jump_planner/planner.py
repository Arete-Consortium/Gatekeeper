"""Capital ship jump route planner.

Computes optimal jump routes for capital ships including:
- Multi-leg routes with midpoints
- Fuel calculations
- Cyno beacon awareness
- Jump fatigue considerations
"""

import heapq
import math
from dataclasses import dataclass, field

import aiosqlite

from backend.starmap.graph.universe_graph import UniverseGraph
from backend.starmap.sde.models import SolarSystem
from backend.starmap.sde.schema import get_db_path

from .ship_data import (
    CAPITAL_SHIPS,
    CapitalShipData,
    calculate_effective_range,
    calculate_fuel_consumption,
)


@dataclass
class JumpLeg:
    """A single leg of a capital jump route."""

    from_system: SolarSystem
    to_system: SolarSystem
    distance_ly: float
    fuel_required: int
    is_cyno_beacon: bool = False  # Whether destination has a cyno beacon
    fatigue_generated: float = 0.0  # Jump fatigue in minutes


@dataclass
class JumpRoute:
    """Complete capital jump route."""

    origin: SolarSystem
    destination: SolarSystem
    legs: list[JumpLeg]
    total_distance_ly: float
    total_fuel: int
    total_legs: int
    ship_type: str
    effective_range: float

    @property
    def midpoint_systems(self) -> list[SolarSystem]:
        """Get all midpoint systems (excluding origin and destination)."""
        if len(self.legs) <= 1:
            return []
        return [leg.to_system for leg in self.legs[:-1]]


@dataclass(order=True)
class PriorityNode:
    """Node in jump route priority queue."""

    priority: float  # Total estimated cost
    system_id: int = field(compare=False)
    path: list[int] = field(compare=False)
    total_fuel: int = field(compare=False)
    total_distance: float = field(compare=False)


class JumpPlanner:
    """Capital ship jump route planner.

    Computes optimal routes considering:
    - Ship jump range (with skills)
    - Fuel consumption
    - System security restrictions
    - Cyno beacon availability
    """

    # Fatigue formula: base * distance
    FATIGUE_BASE = 10.0  # Base fatigue per jump (minutes)

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())
        self.universe = UniverseGraph(self.db_path)
        self._system_positions: dict[int, tuple[float, float, float]] = {}

    async def _load_system_positions(self) -> None:
        """Load all system 3D positions for distance calculations."""
        if self._system_positions:
            return

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT system_id, x, y, z FROM solar_systems")
            async for row in cursor:
                self._system_positions[row[0]] = (row[1], row[2], row[3])

    def _calculate_distance(self, from_id: int, to_id: int) -> float:
        """Calculate distance between two systems in LY."""
        if from_id not in self._system_positions or to_id not in self._system_positions:
            return float("inf")

        x1, y1, z1 = self._system_positions[from_id]
        x2, y2, z2 = self._system_positions[to_id]

        distance_m = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)
        return distance_m / 9.461e15  # Convert to LY

    async def get_jumpable_systems(
        self,
        from_system_id: int,
        max_range_ly: float,
        exclude_highsec: bool = True,
    ) -> list[tuple[int, float]]:
        """Get all systems reachable in one jump.

        Args:
            from_system_id: Origin system ID
            max_range_ly: Maximum jump range in LY
            exclude_highsec: Exclude highsec systems (can't cyno there)

        Returns:
            List of (system_id, distance_ly) tuples
        """
        await self._load_system_positions()

        results = []
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT system_id, x, y, z, security_class
                FROM solar_systems
                WHERE system_id != ?
            """
            if exclude_highsec:
                query += " AND security_class != 'highsec'"

            cursor = await db.execute(query, (from_system_id,))

            origin_pos = self._system_positions.get(from_system_id)
            if not origin_pos:
                return []

            async for row in cursor:
                sys_id, x, y, z, _ = row
                distance_m = math.sqrt(
                    (x - origin_pos[0]) ** 2 + (y - origin_pos[1]) ** 2 + (z - origin_pos[2]) ** 2
                )
                distance_ly = distance_m / 9.461e15

                if distance_ly <= max_range_ly:
                    results.append((sys_id, distance_ly))

        return results

    async def plan_route(
        self,
        origin_id: int,
        destination_id: int,
        ship_type_id: int,
        jdc_level: int = 5,
        jfc_level: int = 5,
        jf_level: int = 0,
        avoid_systems: list[int] | None = None,
        prefer_beacons: bool = True,
    ) -> JumpRoute | None:
        """Plan an optimal capital jump route.

        Uses A* to find route minimizing total fuel consumption.

        Args:
            origin_id: Starting system ID
            destination_id: Destination system ID
            ship_type_id: Capital ship type ID
            jdc_level: Jump Drive Calibration skill level
            jfc_level: Jump Fuel Conservation skill level
            jf_level: Jump Freighter skill level (for JFs)
            avoid_systems: Systems to avoid
            prefer_beacons: Prefer systems with cyno beacons

        Returns:
            JumpRoute or None if no route possible
        """
        ship_data = CAPITAL_SHIPS.get(ship_type_id)
        if not ship_data:
            return None

        await self._load_system_positions()

        # Calculate effective range
        effective_range = calculate_effective_range(ship_data.base_range_ly, jdc_level)

        origin = await self.universe.get_system(origin_id)
        destination = await self.universe.get_system(destination_id)

        if not origin or not destination:
            return None

        # Check if direct jump is possible
        direct_distance = self._calculate_distance(origin_id, destination_id)
        if direct_distance <= effective_range:
            fuel = calculate_fuel_consumption(
                ship_data.base_fuel_need,
                direct_distance,
                jfc_level,
                jf_level,
                ship_data.is_jump_freighter,
            )
            return JumpRoute(
                origin=origin,
                destination=destination,
                legs=[
                    JumpLeg(
                        from_system=origin,
                        to_system=destination,
                        distance_ly=direct_distance,
                        fuel_required=fuel,
                    )
                ],
                total_distance_ly=direct_distance,
                total_fuel=fuel,
                total_legs=1,
                ship_type=ship_data.name,
                effective_range=effective_range,
            )

        # A* search for multi-leg route
        avoid = set(avoid_systems or [])

        # Heuristic: straight-line distance to destination
        def heuristic(system_id: int) -> float:
            return self._calculate_distance(system_id, destination_id)

        # Priority queue: (f_score, system_id, path, total_fuel, total_distance)
        start_node = PriorityNode(
            priority=heuristic(origin_id),
            system_id=origin_id,
            path=[origin_id],
            total_fuel=0,
            total_distance=0.0,
        )
        heap: list[PriorityNode] = [start_node]
        visited: set[int] = set()
        g_scores: dict[int, float] = {origin_id: 0}

        while heap:
            current = heapq.heappop(heap)

            if current.system_id == destination_id:
                # Build route from path
                return await self._build_route(
                    current.path,
                    ship_data,
                    jfc_level,
                    jf_level,
                    effective_range,
                )

            if current.system_id in visited:
                continue
            visited.add(current.system_id)

            # Get all systems in jump range
            reachable = await self.get_jumpable_systems(
                current.system_id,
                effective_range,
                exclude_highsec=True,
            )

            for neighbor_id, distance_ly in reachable:
                if neighbor_id in visited or neighbor_id in avoid:
                    continue

                # Calculate fuel for this leg
                fuel = calculate_fuel_consumption(
                    ship_data.base_fuel_need,
                    distance_ly,
                    jfc_level,
                    jf_level,
                    ship_data.is_jump_freighter,
                )

                # Use fuel as cost (minimize total fuel)
                tentative_g = current.total_fuel + fuel

                if neighbor_id not in g_scores or tentative_g < g_scores[neighbor_id]:
                    g_scores[neighbor_id] = tentative_g
                    f_score = tentative_g + heuristic(neighbor_id) * 100  # Scale heuristic

                    heapq.heappush(
                        heap,
                        PriorityNode(
                            priority=f_score,
                            system_id=neighbor_id,
                            path=current.path + [neighbor_id],
                            total_fuel=tentative_g,
                            total_distance=current.total_distance + distance_ly,
                        ),
                    )

        return None  # No route found

    async def _build_route(
        self,
        path: list[int],
        ship_data: CapitalShipData,
        jfc_level: int,
        jf_level: int,
        effective_range: float,
    ) -> JumpRoute:
        """Build a JumpRoute from a path of system IDs."""
        legs = []
        total_fuel = 0
        total_distance = 0.0

        for i in range(len(path) - 1):
            from_id = path[i]
            to_id = path[i + 1]

            from_system = await self.universe.get_system(from_id)
            to_system = await self.universe.get_system(to_id)

            if not from_system or not to_system:
                continue

            distance = self._calculate_distance(from_id, to_id)
            fuel = calculate_fuel_consumption(
                ship_data.base_fuel_need,
                distance,
                jfc_level,
                jf_level,
                ship_data.is_jump_freighter,
            )

            legs.append(
                JumpLeg(
                    from_system=from_system,
                    to_system=to_system,
                    distance_ly=distance,
                    fuel_required=fuel,
                    fatigue_generated=self.FATIGUE_BASE * (1 + distance),
                )
            )

            total_fuel += fuel
            total_distance += distance

        origin = await self.universe.get_system(path[0])
        destination = await self.universe.get_system(path[-1])

        return JumpRoute(
            origin=origin,  # type: ignore
            destination=destination,  # type: ignore
            legs=legs,
            total_distance_ly=total_distance,
            total_fuel=total_fuel,
            total_legs=len(legs),
            ship_type=ship_data.name,
            effective_range=effective_range,
        )

    async def get_range_sphere(
        self,
        origin_id: int,
        ship_type_id: int,
        jdc_level: int = 5,
    ) -> list[tuple[SolarSystem, float]]:
        """Get all systems within jump range for visualization.

        Args:
            origin_id: Center system ID
            ship_type_id: Ship type for range calculation
            jdc_level: JDC skill level

        Returns:
            List of (system, distance_ly) within range
        """
        ship_data = CAPITAL_SHIPS.get(ship_type_id)
        if not ship_data:
            return []

        effective_range = calculate_effective_range(ship_data.base_range_ly, jdc_level)

        results = await self.universe.get_systems_in_range(
            origin_id,
            effective_range,
            exclude_wormholes=True,
        )

        return [(r.system, r.distance_ly) for r in results]
