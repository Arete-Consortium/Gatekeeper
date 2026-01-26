"""Universe graph management and utilities."""

import math
from dataclasses import dataclass
from typing import Any

import aiosqlite

from backend.starmap.sde.models import SolarSystem
from backend.starmap.sde.schema import get_db_path


@dataclass
class SystemDistance:
    """System with distance from origin."""

    system: SolarSystem
    distance_ly: float


class UniverseGraph:
    """High-level interface for universe graph operations.

    Provides methods for:
    - Jump range calculations
    - Distance computations
    - Neighbor lookups
    - Statistical queries
    """

    # EVE coordinate scaling (1 LY in meters)
    LIGHT_YEAR_METERS = 9.461e15

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())
        self._system_cache: dict[int, SolarSystem] = {}
        self._adjacency: dict[int, list[int]] | None = None

    async def _ensure_loaded(self) -> None:
        """Ensure adjacency data is loaded."""
        if self._adjacency is not None:
            return

        self._adjacency = {}
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT from_system_id, to_system_id FROM system_connections")
            async for row in cursor:
                from_sys, to_sys = row
                if from_sys not in self._adjacency:
                    self._adjacency[from_sys] = []
                self._adjacency[from_sys].append(to_sys)

    async def get_system(self, system_id: int) -> SolarSystem | None:
        """Get system by ID with caching."""
        if system_id in self._system_cache:
            return self._system_cache[system_id]

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT system_id, constellation_id, region_id, name,
                       x, y, z, map_x, map_y, security_status, security_class,
                       star_id, is_wormhole, is_pochven
                FROM solar_systems
                WHERE system_id = ?
                """,
                (system_id,),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            system = SolarSystem(
                system_id=row["system_id"],
                constellation_id=row["constellation_id"],
                region_id=row["region_id"],
                name=row["name"],
                x=row["x"],
                y=row["y"],
                z=row["z"],
                map_x=row["map_x"],
                map_y=row["map_y"],
                security_status=row["security_status"],
                security_class=row["security_class"],
                star_id=row["star_id"],
                is_wormhole=bool(row["is_wormhole"]),
                is_pochven=bool(row["is_pochven"]),
            )
            self._system_cache[system_id] = system
            return system

    async def get_neighbors(self, system_id: int) -> list[SolarSystem]:
        """Get directly connected systems."""
        await self._ensure_loaded()
        assert self._adjacency is not None  # Set by _ensure_loaded

        neighbor_ids = self._adjacency.get(system_id, [])
        neighbors = []

        for nid in neighbor_ids:
            system = await self.get_system(nid)
            if system:
                neighbors.append(system)

        return neighbors

    def calculate_distance_ly(
        self,
        system1: SolarSystem,
        system2: SolarSystem,
    ) -> float:
        """Calculate distance between two systems in light years.

        Uses 3D Euclidean distance from SDE coordinates.
        """
        dx = system2.x - system1.x
        dy = system2.y - system1.y
        dz = system2.z - system1.z

        distance_meters = math.sqrt(dx * dx + dy * dy + dz * dz)
        return distance_meters / self.LIGHT_YEAR_METERS

    async def get_systems_in_range(
        self,
        origin_id: int,
        max_range_ly: float,
        exclude_wormholes: bool = True,
    ) -> list[SystemDistance]:
        """Get all systems within jump range of origin.

        Args:
            origin_id: Origin system ID
            max_range_ly: Maximum range in light years
            exclude_wormholes: Whether to exclude wormhole systems

        Returns:
            List of systems with their distances, sorted by distance
        """
        origin = await self.get_system(origin_id)
        if not origin:
            return []

        results = []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Build query
            query = """
                SELECT system_id, constellation_id, region_id, name,
                       x, y, z, map_x, map_y, security_status, security_class,
                       star_id, is_wormhole, is_pochven
                FROM solar_systems
                WHERE system_id != ?
            """
            params: list[Any] = [origin_id]

            if exclude_wormholes:
                query += " AND is_wormhole = 0"

            cursor = await db.execute(query, params)

            async for row in cursor:
                system = SolarSystem(
                    system_id=row["system_id"],
                    constellation_id=row["constellation_id"],
                    region_id=row["region_id"],
                    name=row["name"],
                    x=row["x"],
                    y=row["y"],
                    z=row["z"],
                    map_x=row["map_x"],
                    map_y=row["map_y"],
                    security_status=row["security_status"],
                    security_class=row["security_class"],
                    star_id=row["star_id"],
                    is_wormhole=bool(row["is_wormhole"]),
                    is_pochven=bool(row["is_pochven"]),
                )

                distance = self.calculate_distance_ly(origin, system)
                if distance <= max_range_ly:
                    results.append(SystemDistance(system=system, distance_ly=distance))

        # Sort by distance
        results.sort(key=lambda x: x.distance_ly)
        return results

    async def search_systems(
        self,
        query: str,
        limit: int = 20,
    ) -> list[SolarSystem]:
        """Search for systems by name.

        Args:
            query: Search string (case-insensitive, partial match)
            limit: Maximum results to return

        Returns:
            List of matching systems
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT system_id, constellation_id, region_id, name,
                       x, y, z, map_x, map_y, security_status, security_class,
                       star_id, is_wormhole, is_pochven
                FROM solar_systems
                WHERE name LIKE ?
                ORDER BY
                    CASE WHEN name = ? THEN 0
                         WHEN name LIKE ? THEN 1
                         ELSE 2
                    END,
                    name
                LIMIT ?
                """,
                (f"%{query}%", query, f"{query}%", limit),
            )

            results = []
            async for row in cursor:
                system = SolarSystem(
                    system_id=row["system_id"],
                    constellation_id=row["constellation_id"],
                    region_id=row["region_id"],
                    name=row["name"],
                    x=row["x"],
                    y=row["y"],
                    z=row["z"],
                    map_x=row["map_x"],
                    map_y=row["map_y"],
                    security_status=row["security_status"],
                    security_class=row["security_class"],
                    star_id=row["star_id"],
                    is_wormhole=bool(row["is_wormhole"]),
                    is_pochven=bool(row["is_pochven"]),
                )
                results.append(system)

            return results

    async def get_region_systems(self, region_id: int) -> list[SolarSystem]:
        """Get all systems in a region."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT system_id, constellation_id, region_id, name,
                       x, y, z, map_x, map_y, security_status, security_class,
                       star_id, is_wormhole, is_pochven
                FROM solar_systems
                WHERE region_id = ?
                ORDER BY name
                """,
                (region_id,),
            )

            results = []
            async for row in cursor:
                system = SolarSystem(
                    system_id=row["system_id"],
                    constellation_id=row["constellation_id"],
                    region_id=row["region_id"],
                    name=row["name"],
                    x=row["x"],
                    y=row["y"],
                    z=row["z"],
                    map_x=row["map_x"],
                    map_y=row["map_y"],
                    security_status=row["security_status"],
                    security_class=row["security_class"],
                    star_id=row["star_id"],
                    is_wormhole=bool(row["is_wormhole"]),
                    is_pochven=bool(row["is_pochven"]),
                )
                results.append(system)

            return results

    async def get_all_systems_for_map(
        self,
        region_id: int | None = None,
        exclude_wormholes: bool = True,
    ) -> list[SolarSystem]:
        """Get all systems with map coordinates for rendering.

        Args:
            region_id: Optional filter by region
            exclude_wormholes: Whether to exclude wormhole systems

        Returns:
            List of systems with valid map coordinates
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            query = """
                SELECT system_id, constellation_id, region_id, name,
                       x, y, z, map_x, map_y, security_status, security_class,
                       star_id, is_wormhole, is_pochven
                FROM solar_systems
                WHERE map_x IS NOT NULL AND map_y IS NOT NULL
            """
            params: list[Any] = []

            if region_id:
                query += " AND region_id = ?"
                params.append(region_id)

            if exclude_wormholes:
                query += " AND is_wormhole = 0"

            cursor = await db.execute(query, params)

            results = []
            async for row in cursor:
                system = SolarSystem(
                    system_id=row["system_id"],
                    constellation_id=row["constellation_id"],
                    region_id=row["region_id"],
                    name=row["name"],
                    x=row["x"],
                    y=row["y"],
                    z=row["z"],
                    map_x=row["map_x"],
                    map_y=row["map_y"],
                    security_status=row["security_status"],
                    security_class=row["security_class"],
                    star_id=row["star_id"],
                    is_wormhole=bool(row["is_wormhole"]),
                    is_pochven=bool(row["is_pochven"]),
                )
                results.append(system)

            return results

    async def get_all_connections(
        self,
        region_id: int | None = None,
    ) -> list[tuple[int, int]]:
        """Get all stargate connections.

        Args:
            region_id: Optional filter by region

        Returns:
            List of (from_system_id, to_system_id) tuples
        """
        async with aiosqlite.connect(self.db_path) as db:
            if region_id:
                # Only connections within the region
                cursor = await db.execute(
                    """
                    SELECT DISTINCT c.from_system_id, c.to_system_id
                    FROM system_connections c
                    JOIN solar_systems s1 ON c.from_system_id = s1.system_id
                    JOIN solar_systems s2 ON c.to_system_id = s2.system_id
                    WHERE s1.region_id = ? AND s2.region_id = ?
                    """,
                    (region_id, region_id),
                )
            else:
                cursor = await db.execute(
                    "SELECT from_system_id, to_system_id FROM system_connections"
                )

            return [(row[0], row[1]) async for row in cursor]

    async def get_all_regions(self) -> list[dict[str, Any]]:
        """Get all regions with system counts."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT r.region_id, r.name,
                       COUNT(s.system_id) as system_count
                FROM regions r
                LEFT JOIN solar_systems s ON r.region_id = s.region_id
                WHERE r.region_id < 11000000  -- Exclude wormhole regions
                GROUP BY r.region_id, r.name
                ORDER BY r.name
                """
            )

            return [
                {
                    "region_id": row["region_id"],
                    "name": row["name"],
                    "system_count": row["system_count"],
                }
                async for row in cursor
            ]

    async def get_region_name(self, region_id: int) -> str | None:
        """Get region name by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM regions WHERE region_id = ?",
                (region_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_statistics(self) -> dict[str, Any]:
        """Get universe statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            stats: dict[str, Any] = {}

            # Helper to safely fetch count
            async def fetch_count(query: str) -> int:
                cursor = await db.execute(query)
                row = await cursor.fetchone()
                return int(row[0]) if row else 0

            # System counts
            stats["total_systems"] = await fetch_count("SELECT COUNT(*) FROM solar_systems")
            stats["highsec_systems"] = await fetch_count(
                "SELECT COUNT(*) FROM solar_systems WHERE security_class = 'highsec'"
            )
            stats["lowsec_systems"] = await fetch_count(
                "SELECT COUNT(*) FROM solar_systems WHERE security_class = 'lowsec'"
            )
            stats["nullsec_systems"] = await fetch_count(
                "SELECT COUNT(*) FROM solar_systems WHERE security_class = 'nullsec'"
            )
            stats["wormhole_systems"] = await fetch_count(
                "SELECT COUNT(*) FROM solar_systems WHERE is_wormhole = 1"
            )

            # Connection counts
            stats["total_connections"] = await fetch_count(
                "SELECT COUNT(*) FROM system_connections"
            )
            stats["total_regions"] = await fetch_count("SELECT COUNT(*) FROM regions")

            return stats
