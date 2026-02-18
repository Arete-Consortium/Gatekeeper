"""Caching service with Redis and in-memory fallback."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from cachetools import TTLCache

from ..core.config import settings

logger = logging.getLogger(__name__)


class CacheService(ABC):
    """Abstract cache service interface."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Get a value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set a value in cache with TTL in seconds."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        pass

    # Convenience methods for JSON serialization
    async def get_json(self, key: str) -> Any | None:
        """Get and deserialize JSON value from cache."""
        value = await self.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON for key: {key}")
            return None

    async def set_json(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Serialize and set JSON value in cache."""
        try:
            serialized = json.dumps(value, default=str)
            return await self.set(key, serialized, ttl)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize value for key {key}: {e}")
            return False


class MemoryCacheService(CacheService):
    """In-memory cache using cachetools TTLCache."""

    def __init__(self, maxsize: int = 10000):
        # Group caches by TTL for better memory management
        self._caches: dict[int, TTLCache] = {}
        self._maxsize = maxsize
        self._hits = 0
        self._misses = 0

    def _get_cache(self, ttl: int) -> TTLCache:
        """Get or create a cache for the given TTL."""
        if ttl not in self._caches:
            self._caches[ttl] = TTLCache(maxsize=self._maxsize, ttl=ttl)
        return self._caches[ttl]

    async def get(self, key: str) -> str | None:
        """Get value from any cache that has this key."""
        for cache in self._caches.values():
            if key in cache:
                self._hits += 1
                logger.debug("Cache hit", extra={"key": key, "cache_type": "memory"})
                return str(cache[key])
        self._misses += 1
        logger.debug("Cache miss", extra={"key": key, "cache_type": "memory"})
        return None

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in the appropriate TTL cache."""
        cache = self._get_cache(ttl)
        try:
            cache[key] = value
            return True
        except Exception as e:
            logger.warning(f"Memory cache set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from all caches."""
        deleted = False
        for cache in self._caches.values():
            if key in cache:
                del cache[key]
                deleted = True
        return deleted

    async def exists(self, key: str) -> bool:
        """Check if key exists in any cache."""
        return any(key in cache for cache in self._caches.values())

    async def clear(self) -> bool:
        """Clear all caches."""
        total_entries = sum(len(cache) for cache in self._caches.values())
        for cache in self._caches.values():
            cache.clear()
        logger.info("Memory cache cleared", extra={"entries_cleared": total_entries})
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total_entries = sum(len(cache) for cache in self._caches.values())
        return {
            "type": "memory",
            "entries": total_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": self._hits / (self._hits + self._misses)
            if (self._hits + self._misses) > 0
            else 0,
        }


class RedisCacheService(CacheService):
    """Redis-based cache service."""

    def __init__(self, redis_url: str):
        import redis.asyncio as aioredis

        self._redis: Any = aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> str | None:
        """Get value from Redis."""
        try:
            value = await self._redis.get(key)
            if value is not None:
                self._hits += 1
                logger.debug("Cache hit", extra={"key": key, "cache_type": "redis"})
                return str(value)
            else:
                self._misses += 1
                logger.debug("Cache miss", extra={"key": key, "cache_type": "redis"})
            return None
        except Exception as e:
            logger.warning("Redis get failed", extra={"key": key, "error": str(e)})
            self._misses += 1
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in Redis with TTL."""
        try:
            await self._redis.setex(key, ttl, value)
            logger.debug("Cache set", extra={"key": key, "ttl": ttl, "cache_type": "redis"})
            return True
        except Exception as e:
            logger.warning("Redis set failed", extra={"key": key, "ttl": ttl, "error": str(e)})
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            result = await self._redis.delete(key)
            deleted = int(result) > 0
            if deleted:
                logger.debug("Cache key deleted", extra={"key": key, "cache_type": "redis"})
            return deleted
        except Exception as e:
            logger.warning("Redis delete failed", extra={"key": key, "error": str(e)})
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            return int(await self._redis.exists(key)) > 0
        except Exception as e:
            logger.warning("Redis exists check failed", extra={"key": key, "error": str(e)})
            return False

    async def clear(self) -> bool:
        """Clear all keys (use with caution in production)."""
        try:
            await self._redis.flushdb()
            logger.info("Redis cache cleared")
            return True
        except Exception as e:
            logger.warning("Redis clear failed", extra={"error": str(e)})
            return False

    async def ping(self) -> bool:
        """Check if Redis is connected."""
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.close()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "type": "redis",
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": self._hits / (self._hits + self._misses)
            if (self._hits + self._misses) > 0
            else 0,
        }


# Global cache instance
_cache: CacheService | None = None


async def get_cache() -> CacheService:
    """Get or create the cache service instance."""
    global _cache
    if _cache is not None:
        return _cache

    if settings.REDIS_URL:
        try:
            cache = RedisCacheService(settings.REDIS_URL)
            # Test connection
            if await cache.ping():
                logger.info("Using Redis cache")
                _cache = cache
                return _cache
            else:
                logger.warning("Redis ping failed, falling back to memory cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, using memory cache")

    # Fallback to memory cache
    logger.info("Using in-memory cache")
    _cache = MemoryCacheService()
    return _cache


def get_cache_sync() -> CacheService:
    """Get cache instance synchronously (creates memory cache if not initialized)."""
    global _cache
    if _cache is None:
        _cache = MemoryCacheService()
    return _cache


# Cache key builders
def build_route_key(origin: str, dest: str, profile: str) -> str:
    """Build cache key for route calculations."""
    return f"route:{origin}:{dest}:{profile}"


def build_risk_key(system_name: str) -> str:
    """Build cache key for risk scores."""
    return f"risk:{system_name}"


def build_esi_key(endpoint: str) -> str:
    """Build cache key for ESI responses."""
    return f"esi:{endpoint}"
