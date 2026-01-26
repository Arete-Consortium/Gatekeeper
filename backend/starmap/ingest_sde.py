#!/usr/bin/env python3
"""SDE Ingestion Script for EVE Starmap.

This script populates the universe database using ESI endpoints.
It fetches regions, constellations, systems, and stargates,
then computes derived data like 2D projections and graph connections.

Usage:
    python -m scripts.ingest_sde [--reset] [--skip-stargates]

Options:
    --reset          Drop and recreate all tables before ingestion
    --skip-stargates Skip stargate fetching (faster for testing)
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.starmap.sde.schema import create_tables, get_db_path, reset_database

# ESI Configuration
ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_DATASOURCE = "tranquility"
CONCURRENCY_LIMIT = 20  # Max concurrent requests
REQUEST_TIMEOUT = 30.0


class ESIClient:
    """Async ESI client with rate limiting and retries."""

    def __init__(self, concurrency: int = CONCURRENCY_LIMIT):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ESIClient":
        self.client = httpx.AsyncClient(
            base_url=ESI_BASE_URL,
            timeout=REQUEST_TIMEOUT,
            params={"datasource": ESI_DATASOURCE},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self.client:
            await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def get(self, endpoint: str, **params: Any) -> Any:
        """Make a GET request to ESI with retry logic."""
        async with self.semaphore:
            if not self.client:
                raise RuntimeError("Client not initialized")
            response = await self.client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()


def compute_2d_projection(x: float, y: float, z: float) -> tuple[float, float]:
    """Project 3D coordinates to 2D for map display.

    Uses a simple top-down projection (x, z) with Y as depth.
    Coordinates are normalized to a 0-1000 range.
    """
    # EVE uses a coordinate system where:
    # - X increases to the right (galactic east)
    # - Y increases upward (galactic north)
    # - Z increases toward the viewer (galactic south)

    # For 2D map, we use X and Z (top-down view)
    # Scale factors based on typical EVE coordinate ranges
    # Universe spans roughly ±5e17 meters in each dimension

    scale = 5e17
    map_x = (x / scale + 1) * 500  # Normalize to 0-1000
    map_y = (z / scale + 1) * 500

    return map_x, map_y


def classify_security(security_status: float, is_wormhole: bool = False) -> str:
    """Classify system security status."""
    if is_wormhole:
        return "wormhole"
    if security_status >= 0.45:  # Rounds to 0.5
        return "highsec"
    if security_status > 0.0:
        return "lowsec"
    return "nullsec"


async def fetch_all_regions(client: ESIClient) -> list[int]:
    """Fetch list of all region IDs."""
    print("Fetching region list...")
    result: list[int] = await client.get("/universe/regions/")
    return result


async def fetch_region_details(client: ESIClient, region_id: int) -> dict[str, Any]:
    """Fetch details for a single region."""
    result: dict[str, Any] = await client.get(f"/universe/regions/{region_id}/")
    return result


async def fetch_constellation_details(client: ESIClient, constellation_id: int) -> dict[str, Any]:
    """Fetch details for a single constellation."""
    result: dict[str, Any] = await client.get(f"/universe/constellations/{constellation_id}/")
    return result


async def fetch_system_details(client: ESIClient, system_id: int) -> dict[str, Any]:
    """Fetch details for a single solar system."""
    result: dict[str, Any] = await client.get(f"/universe/systems/{system_id}/")
    return result


async def fetch_stargate_details(client: ESIClient, stargate_id: int) -> dict[str, Any]:
    """Fetch details for a single stargate."""
    result: dict[str, Any] = await client.get(f"/universe/stargates/{stargate_id}/")
    return result


async def ingest_regions(db: aiosqlite.Connection, client: ESIClient) -> dict[int, dict[str, Any]]:
    """Fetch and insert all regions."""
    print("\n=== Ingesting Regions ===")

    region_ids = await fetch_all_regions(client)
    print(f"Found {len(region_ids)} regions")

    regions = {}
    tasks = [fetch_region_details(client, rid) for rid in region_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    insert_count = 0
    for rid, result in zip(region_ids, results, strict=False):
        if isinstance(result, BaseException):
            print(f"  Error fetching region {rid}: {result}")
            continue

        regions[rid] = result

        # Extract position (center of region)
        pos = result.get("position", {})
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        z = pos.get("z", 0)

        await db.execute(
            """
            INSERT OR REPLACE INTO regions
            (region_id, name, description, x, y, z, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["region_id"],
                result["name"],
                result.get("description"),
                x,
                y,
                z,
                datetime.utcnow().isoformat(),
            ),
        )
        insert_count += 1

        if insert_count % 20 == 0:
            print(f"  Inserted {insert_count} regions...")

    await db.commit()
    print(f"Inserted {insert_count} regions")
    return regions


async def ingest_constellations(
    db: aiosqlite.Connection,
    client: ESIClient,
    regions: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Fetch and insert all constellations."""
    print("\n=== Ingesting Constellations ===")

    # Collect all constellation IDs from regions
    constellation_ids = []
    for region_data in regions.values():
        constellation_ids.extend(region_data.get("constellations", []))

    print(f"Found {len(constellation_ids)} constellations")

    constellations = {}
    # Batch fetch constellations
    tasks = [fetch_constellation_details(client, cid) for cid in constellation_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    insert_count = 0
    for cid, result in zip(constellation_ids, results, strict=False):
        if isinstance(result, BaseException):
            print(f"  Error fetching constellation {cid}: {result}")
            continue

        constellations[cid] = result

        pos = result.get("position", {})
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        z = pos.get("z", 0)

        await db.execute(
            """
            INSERT OR REPLACE INTO constellations
            (constellation_id, region_id, name, x, y, z, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["constellation_id"],
                result["region_id"],
                result["name"],
                x,
                y,
                z,
                datetime.utcnow().isoformat(),
            ),
        )
        insert_count += 1

        if insert_count % 100 == 0:
            print(f"  Inserted {insert_count} constellations...")

    await db.commit()
    print(f"Inserted {insert_count} constellations")
    return constellations


async def ingest_systems(
    db: aiosqlite.Connection,
    client: ESIClient,
    constellations: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Fetch and insert all solar systems."""
    print("\n=== Ingesting Solar Systems ===")

    # Collect all system IDs from constellations
    system_ids = []
    constellation_map = {}  # system_id -> constellation_id
    for const_data in constellations.values():
        for sid in const_data.get("systems", []):
            system_ids.append(sid)
            constellation_map[sid] = const_data["constellation_id"]

    print(f"Found {len(system_ids)} solar systems")

    systems = {}
    # Batch fetch in chunks to avoid memory issues
    chunk_size = 500
    insert_count = 0

    for i in range(0, len(system_ids), chunk_size):
        chunk = system_ids[i : i + chunk_size]
        tasks = [fetch_system_details(client, sid) for sid in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for sid, result in zip(chunk, results, strict=False):
            if isinstance(result, BaseException):
                print(f"  Error fetching system {sid}: {result}")
                continue

            systems[sid] = result

            pos = result.get("position", {})
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            z = pos.get("z", 0)

            # Compute 2D projection
            map_x, map_y = compute_2d_projection(x, y, z)

            # Get security info
            security = result.get("security_status", 0.0)
            is_wormhole = result["name"].startswith("J") and len(result["name"]) == 7
            security_class = classify_security(security, is_wormhole)

            # Check for Pochven (Triglavian space)
            is_pochven = result.get("constellation_id") in [
                # Pochven constellation IDs
                20000837,
                20000838,
                20000839,  # Placeholder - will be updated
            ]

            await db.execute(
                """
                INSERT OR REPLACE INTO solar_systems
                (system_id, constellation_id, region_id, name,
                 x, y, z, map_x, map_y,
                 security_status, security_class,
                 star_id, star_type_id,
                 is_wormhole, is_pochven, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["system_id"],
                    result["constellation_id"],
                    constellation_map.get(sid, result["constellation_id"]),
                    result["name"],
                    x,
                    y,
                    z,
                    map_x,
                    map_y,
                    security,
                    security_class,
                    result.get("star_id"),
                    None,  # star_type_id - would need another fetch
                    is_wormhole,
                    is_pochven,
                    datetime.utcnow().isoformat(),
                ),
            )
            insert_count += 1

        print(f"  Inserted {insert_count} / {len(system_ids)} systems...")
        await db.commit()

    print(f"Inserted {insert_count} solar systems")
    return systems


async def ingest_stargates(
    db: aiosqlite.Connection,
    client: ESIClient,
    systems: dict[int, dict[str, Any]],
) -> None:
    """Fetch and insert all stargates and build connection graph."""
    print("\n=== Ingesting Stargates ===")

    # Collect all stargate IDs from systems
    stargate_ids = []
    for system_data in systems.values():
        stargate_ids.extend(system_data.get("stargates", []))

    print(f"Found {len(stargate_ids)} stargates")

    # Batch fetch stargates
    chunk_size = 500
    insert_count = 0
    connections = set()  # (from_id, to_id) pairs

    for i in range(0, len(stargate_ids), chunk_size):
        chunk = stargate_ids[i : i + chunk_size]
        tasks = [fetch_stargate_details(client, gid) for gid in chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for _, result in zip(chunk, results, strict=False):
            if isinstance(result, BaseException):
                # Some stargates may not exist (wormhole systems, etc.)
                continue

            pos = result.get("position", {})
            dest = result.get("destination", {})

            await db.execute(
                """
                INSERT OR REPLACE INTO stargates
                (stargate_id, system_id, destination_stargate_id, destination_system_id,
                 name, type_id, x, y, z)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["stargate_id"],
                    result["system_id"],
                    dest.get("stargate_id"),
                    dest.get("system_id"),
                    result.get("name"),
                    result.get("type_id"),
                    pos.get("x"),
                    pos.get("y"),
                    pos.get("z"),
                ),
            )
            insert_count += 1

            # Build connection
            from_sys = result["system_id"]
            to_sys = dest.get("system_id")
            if to_sys:
                # Add both directions
                connections.add((from_sys, to_sys))
                connections.add((to_sys, from_sys))

        print(f"  Inserted {insert_count} / {len(stargate_ids)} stargates...")
        await db.commit()

    print(f"Inserted {insert_count} stargates")

    # Insert connections
    print(f"\nBuilding connection graph with {len(connections)} edges...")

    # Precompute security weights
    cursor = await db.execute("SELECT system_id, security_status FROM solar_systems")
    security_map = {row[0]: row[1] for row in await cursor.fetchall()}

    for from_sys, to_sys in connections:
        # Calculate security weight (penalty for dangerous space)
        to_security = security_map.get(to_sys, 0.0)
        if to_security >= 0.45:
            sec_weight = 0.0  # Highsec - no penalty
        elif to_security > 0.0:
            sec_weight = 1.0  # Lowsec - small penalty
        else:
            sec_weight = 2.0  # Nullsec - larger penalty

        await db.execute(
            """
            INSERT OR REPLACE INTO system_connections
            (from_system_id, to_system_id, base_weight, security_weight, connection_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (from_sys, to_sys, 1.0, sec_weight, "stargate"),
        )

    await db.commit()
    print("Built connection graph")


async def update_region_ids(db: aiosqlite.Connection) -> None:
    """Update region_id in solar_systems from constellation data."""
    print("\nUpdating region IDs in solar systems...")

    await db.execute(
        """
        UPDATE solar_systems
        SET region_id = (
            SELECT c.region_id
            FROM constellations c
            WHERE c.constellation_id = solar_systems.constellation_id
        )
        WHERE region_id IS NULL OR region_id = 0
        """
    )
    await db.commit()


async def compute_statistics(db: aiosqlite.Connection) -> None:
    """Compute and display ingestion statistics."""
    print("\n=== Ingestion Statistics ===")

    queries = [
        ("Regions", "SELECT COUNT(*) FROM regions"),
        ("Constellations", "SELECT COUNT(*) FROM constellations"),
        ("Solar Systems", "SELECT COUNT(*) FROM solar_systems"),
        ("Stargates", "SELECT COUNT(*) FROM stargates"),
        ("Connections", "SELECT COUNT(*) FROM system_connections"),
        ("Highsec Systems", "SELECT COUNT(*) FROM solar_systems WHERE security_class = 'highsec'"),
        ("Lowsec Systems", "SELECT COUNT(*) FROM solar_systems WHERE security_class = 'lowsec'"),
        ("Nullsec Systems", "SELECT COUNT(*) FROM solar_systems WHERE security_class = 'nullsec'"),
        ("Wormhole Systems", "SELECT COUNT(*) FROM solar_systems WHERE is_wormhole = 1"),
    ]

    for label, query in queries:
        cursor = await db.execute(query)
        row = await cursor.fetchone()
        count = row[0] if row else 0
        print(f"  {label}: {count:,}")


async def main_async(reset: bool = False, skip_stargates: bool = False) -> None:
    """Main ingestion routine."""
    print("EVE Starmap - SDE Ingestion")
    print("=" * 50)

    db_path = get_db_path()
    print(f"Database: {db_path}")

    if reset:
        print("\nResetting database...")
        await reset_database(db_path)
    else:
        await create_tables(db_path)

    async with ESIClient() as client:
        async with aiosqlite.connect(db_path) as db:
            # Enable WAL mode for better performance
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")

            # Ingest in order
            regions = await ingest_regions(db, client)
            constellations = await ingest_constellations(db, client, regions)
            systems = await ingest_systems(db, client, constellations)

            if not skip_stargates:
                await ingest_stargates(db, client, systems)
            else:
                print("\nSkipping stargate ingestion")

            await update_region_ids(db)
            await compute_statistics(db)

    print("\n" + "=" * 50)
    print("Ingestion complete!")


def main() -> None:
    """Entry point for CLI."""
    parser = argparse.ArgumentParser(description="Ingest EVE Online SDE data into SQLite")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before ingestion",
    )
    parser.add_argument(
        "--skip-stargates",
        action="store_true",
        help="Skip stargate ingestion (faster for testing)",
    )

    args = parser.parse_args()
    asyncio.run(main_async(reset=args.reset, skip_stargates=args.skip_stargates))


if __name__ == "__main__":
    main()
