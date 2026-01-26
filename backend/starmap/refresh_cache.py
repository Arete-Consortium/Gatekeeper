#!/usr/bin/env python3
"""Cache refresh script for EVE Starmap.

Refreshes live ESI data caches:
- System kills/jumps (5 min TTL)
- Incursions (10 min TTL)
- Sovereignty (1 hour TTL)

Usage:
    python -m scripts.refresh_cache [--once] [--type TYPE]

Options:
    --once       Run once and exit (default: continuous loop)
    --type TYPE  Only refresh specific type: kills, jumps, incursions, sov
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite

from backend.starmap.esi import (
    ESICache,
    ESIClient,
    get_incursions,
    get_sovereignty_map,
    get_system_jumps,
    get_system_kills,
)
from backend.starmap.sde.schema import get_db_path

# Refresh intervals (seconds)
INTERVALS = {
    "kills": 300,  # 5 minutes
    "jumps": 300,  # 5 minutes
    "incursions": 600,  # 10 minutes
    "sov": 3600,  # 1 hour
}


async def update_system_stats(db_path: str, kills: dict, jumps: dict) -> int:
    """Update system_stats table with kill/jump data.

    Args:
        db_path: Path to database
        kills: Dict of system_id -> {ship_kills, npc_kills, pod_kills}
        jumps: Dict of system_id -> ship_jumps

    Returns:
        Number of systems updated
    """
    now = datetime.utcnow().isoformat()
    updated = 0

    async with aiosqlite.connect(db_path) as db:
        # Combine all system IDs
        all_systems = set(kills.keys()) | set(jumps.keys())

        for system_id in all_systems:
            k = kills.get(system_id, {})
            j = jumps.get(system_id, 0)

            ship_kills = k.get("ship_kills", 0)
            npc_kills = k.get("npc_kills", 0)
            pod_kills = k.get("pod_kills", 0)

            # Calculate activity index (normalized 0-1)
            # Simple formula: log scale of total activity
            import math

            total_activity = ship_kills + pod_kills + j
            activity_index = min(1.0, math.log10(total_activity + 1) / 4)

            await db.execute(
                """
                INSERT INTO system_stats
                (system_id, ship_kills, npc_kills, pod_kills, ship_jumps,
                 kills_updated_at, jumps_updated_at, activity_index)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(system_id) DO UPDATE SET
                    ship_kills = excluded.ship_kills,
                    npc_kills = excluded.npc_kills,
                    pod_kills = excluded.pod_kills,
                    ship_jumps = excluded.ship_jumps,
                    kills_updated_at = excluded.kills_updated_at,
                    jumps_updated_at = excluded.jumps_updated_at,
                    activity_index = excluded.activity_index
                """,
                (system_id, ship_kills, npc_kills, pod_kills, j, now, now, activity_index),
            )
            updated += 1

        await db.commit()

    return updated


async def update_incursions(db_path: str, incursions: list) -> int:
    """Update incursions table.

    Args:
        db_path: Path to database
        incursions: List of incursion data from ESI

    Returns:
        Number of incursions updated
    """
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(db_path) as db:
        # Clear old incursions
        await db.execute("DELETE FROM incursions")

        for inc in incursions:
            await db.execute(
                """
                INSERT INTO incursions
                (constellation_id, staging_system_id, state, influence,
                 has_boss, faction_id, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inc.get("constellation_id"),
                    inc.get("staging_solar_system_id"),
                    inc.get("state"),
                    inc.get("influence", 0.0),
                    inc.get("has_boss", False),
                    inc.get("faction_id"),
                    now,
                ),
            )

        await db.commit()

    return len(incursions)


async def update_sovereignty(db_path: str, sov_map: dict) -> int:
    """Update sovereignty table.

    Args:
        db_path: Path to database
        sov_map: Dict of system_id -> sovereignty data

    Returns:
        Number of systems updated
    """
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(db_path) as db:
        for system_id, sov in sov_map.items():
            await db.execute(
                """
                INSERT INTO sovereignty
                (system_id, alliance_id, corporation_id, faction_id, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(system_id) DO UPDATE SET
                    alliance_id = excluded.alliance_id,
                    corporation_id = excluded.corporation_id,
                    faction_id = excluded.faction_id,
                    fetched_at = excluded.fetched_at
                """,
                (
                    system_id,
                    sov.get("alliance_id"),
                    sov.get("corporation_id"),
                    sov.get("faction_id"),
                    now,
                ),
            )

        await db.commit()

    return len(sov_map)


async def refresh_kills_jumps(client: ESIClient, cache: ESICache, db_path: str) -> None:
    """Refresh system kills and jumps data."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Refreshing kills/jumps...")

    try:
        kills = await get_system_kills(client, cache)
        jumps = await get_system_jumps(client, cache)

        updated = await update_system_stats(db_path, kills, jumps)
        print(f"  Updated {updated} systems with kill/jump data")
    except Exception as e:
        print(f"  Error refreshing kills/jumps: {e}")


async def refresh_incursions(client: ESIClient, cache: ESICache, db_path: str) -> None:
    """Refresh incursion data."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Refreshing incursions...")

    try:
        incursions = await get_incursions(client, cache)
        updated = await update_incursions(db_path, incursions)
        print(f"  Updated {updated} active incursions")
    except Exception as e:
        print(f"  Error refreshing incursions: {e}")


async def refresh_sovereignty(client: ESIClient, cache: ESICache, db_path: str) -> None:
    """Refresh sovereignty data."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Refreshing sovereignty...")

    try:
        sov_map = await get_sovereignty_map(client, cache)
        updated = await update_sovereignty(db_path, sov_map)
        print(f"  Updated sovereignty for {updated} systems")
    except Exception as e:
        print(f"  Error refreshing sovereignty: {e}")


async def cleanup_cache(cache: ESICache) -> None:
    """Clean up expired cache entries."""
    removed = await cache.cleanup_expired()
    if removed > 0:
        print(f"  Cleaned up {removed} expired cache entries")


async def run_continuous(refresh_type: str | None = None) -> None:
    """Run continuous refresh loop."""
    print("EVE Starmap - Cache Refresh Service")
    print("=" * 50)

    db_path = str(get_db_path())
    print(f"Database: {db_path}")

    cache = ESICache(db_path)

    # Track last refresh times
    last_refresh = {
        "kills": 0.0,
        "incursions": 0.0,
        "sov": 0.0,
    }

    async with ESIClient() as client:
        while True:
            now = asyncio.get_event_loop().time()

            # Check each data type
            if refresh_type in (None, "kills", "jumps"):
                if now - last_refresh["kills"] >= INTERVALS["kills"]:
                    await refresh_kills_jumps(client, cache, db_path)
                    last_refresh["kills"] = now

            if refresh_type in (None, "incursions"):
                if now - last_refresh["incursions"] >= INTERVALS["incursions"]:
                    await refresh_incursions(client, cache, db_path)
                    last_refresh["incursions"] = now

            if refresh_type in (None, "sov"):
                if now - last_refresh["sov"] >= INTERVALS["sov"]:
                    await refresh_sovereignty(client, cache, db_path)
                    last_refresh["sov"] = now

            # Periodic cache cleanup
            await cleanup_cache(cache)

            # Sleep before next check
            await asyncio.sleep(60)  # Check every minute


async def run_once(refresh_type: str | None = None) -> None:
    """Run refresh once and exit."""
    print("EVE Starmap - One-time Cache Refresh")
    print("=" * 50)

    db_path = str(get_db_path())
    print(f"Database: {db_path}")

    cache = ESICache(db_path)

    async with ESIClient() as client:
        if refresh_type in (None, "kills", "jumps"):
            await refresh_kills_jumps(client, cache, db_path)

        if refresh_type in (None, "incursions"):
            await refresh_incursions(client, cache, db_path)

        if refresh_type in (None, "sov"):
            await refresh_sovereignty(client, cache, db_path)

        await cleanup_cache(cache)

    print("\nRefresh complete!")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Refresh EVE Starmap ESI data caches")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default: continuous)",
    )
    parser.add_argument(
        "--type",
        choices=["kills", "jumps", "incursions", "sov"],
        help="Only refresh specific data type",
    )

    args = parser.parse_args()

    if args.once:
        asyncio.run(run_once(args.type))
    else:
        try:
            asyncio.run(run_continuous(args.type))
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == "__main__":
    main()
