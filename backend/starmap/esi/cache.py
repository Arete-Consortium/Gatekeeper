"""ESI response caching with SQLite backend."""

import json
from datetime import datetime, timedelta
from typing import Any

import aiosqlite

from backend.starmap.sde.schema import get_db_path

# Default TTL values for different endpoint types (in seconds)
TTL_CONFIG = {
    # Live data - short TTL
    "system_kills": 300,  # 5 minutes
    "system_jumps": 300,  # 5 minutes
    "incursions": 600,  # 10 minutes
    "sovereignty_map": 3600,  # 1 hour
    "sovereignty_campaigns": 300,  # 5 minutes
    # Static data - long TTL
    "universe_types": 86400 * 7,  # 1 week
    "universe_categories": 86400 * 7,
    "universe_groups": 86400 * 7,
    # Default
    "default": 300,  # 5 minutes
}


class ESICache:
    """Async cache for ESI responses using SQLite.

    Provides per-endpoint TTL caching with ETag support.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(get_db_path())

    async def get(self, cache_key: str) -> tuple[Any, bool] | None:
        """Get cached data if not expired.

        Args:
            cache_key: Unique key for the cached data

        Returns:
            Tuple of (data, is_expired) or None if not cached
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT data, expires_at, etag
                FROM esi_cache
                WHERE cache_key = ?
                """,
                (cache_key,),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            data = json.loads(row[0])
            expires_at = datetime.fromisoformat(row[1])
            is_expired = datetime.utcnow() > expires_at

            return data, is_expired

    async def set(
        self,
        cache_key: str,
        endpoint: str,
        data: Any,
        ttl: int | None = None,
        etag: str | None = None,
    ) -> None:
        """Cache data with TTL.

        Args:
            cache_key: Unique key for the cached data
            endpoint: API endpoint name (for TTL lookup)
            data: Data to cache
            ttl: Override TTL in seconds
            etag: ETag from response
        """
        if ttl is None:
            ttl = TTL_CONFIG.get(endpoint, TTL_CONFIG["default"])

        expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO esi_cache
                (cache_key, endpoint, data, etag, expires_at, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key,
                    endpoint,
                    json.dumps(data),
                    etag,
                    expires_at.isoformat(),
                    datetime.utcnow().isoformat(),
                ),
            )
            await db.commit()

    async def get_etag(self, cache_key: str) -> str | None:
        """Get the cached ETag for conditional requests.

        Args:
            cache_key: Unique key for the cached data

        Returns:
            ETag string or None
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT etag FROM esi_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def invalidate(self, cache_key: str) -> None:
        """Invalidate a specific cache entry.

        Args:
            cache_key: Key to invalidate
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM esi_cache WHERE cache_key = ?",
                (cache_key,),
            )
            await db.commit()

    async def invalidate_endpoint(self, endpoint: str) -> None:
        """Invalidate all cache entries for an endpoint.

        Args:
            endpoint: Endpoint name to invalidate
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM esi_cache WHERE endpoint = ?",
                (endpoint,),
            )
            await db.commit()

    async def cleanup_expired(self) -> int:
        """Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM esi_cache
                WHERE expires_at < ?
                """,
                (datetime.utcnow().isoformat(),),
            )
            await db.commit()
            return cursor.rowcount

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache stats
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM esi_cache")
            row = await cursor.fetchone()
            total = int(row[0]) if row else 0

            cursor = await db.execute(
                """
                SELECT COUNT(*)
                FROM esi_cache
                WHERE expires_at < ?
                """,
                (datetime.utcnow().isoformat(),),
            )
            row = await cursor.fetchone()
            expired = int(row[0]) if row else 0

            cursor = await db.execute(
                """
                SELECT endpoint, COUNT(*)
                FROM esi_cache
                GROUP BY endpoint
                """
            )
            by_endpoint = {row[0]: row[1] for row in await cursor.fetchall()}

            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "by_endpoint": by_endpoint,
            }
