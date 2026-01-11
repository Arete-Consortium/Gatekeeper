"""Token Storage Service for ESI OAuth2 tokens.

Provides persistent storage for EVE SSO tokens with support for:
- In-memory storage (development)
- File-based storage (single instance)
- Redis storage (production/multi-instance)
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.config import settings


class TokenStore(ABC):
    """Abstract base class for token storage."""

    @abstractmethod
    async def store_token(
        self,
        character_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        character_name: str,
        scopes: list[str],
    ) -> None:
        """Store a token for a character."""
        pass

    @abstractmethod
    async def get_token(self, character_id: int) -> dict[str, Any] | None:
        """Get stored token for a character."""
        pass

    @abstractmethod
    async def remove_token(self, character_id: int) -> bool:
        """Remove token for a character. Returns True if removed."""
        pass

    @abstractmethod
    async def list_characters(self) -> list[dict[str, Any]]:
        """List all characters with stored tokens."""
        pass

    @abstractmethod
    async def clear_all(self) -> int:
        """Clear all tokens. Returns count of removed tokens."""
        pass


class MemoryTokenStore(TokenStore):
    """In-memory token storage for development."""

    def __init__(self) -> None:
        self._tokens: dict[int, dict[str, Any]] = {}

    async def store_token(
        self,
        character_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        character_name: str,
        scopes: list[str],
    ) -> None:
        self._tokens[character_id] = {
            "character_id": character_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "character_name": character_name,
            "scopes": scopes,
        }

    async def get_token(self, character_id: int) -> dict[str, Any] | None:
        return self._tokens.get(character_id)

    async def remove_token(self, character_id: int) -> bool:
        if character_id in self._tokens:
            del self._tokens[character_id]
            return True
        return False

    async def list_characters(self) -> list[dict[str, Any]]:
        return list(self._tokens.values())

    async def clear_all(self) -> int:
        count = len(self._tokens)
        self._tokens.clear()
        return count


class FileTokenStore(TokenStore):
    """File-based token storage for single-instance deployments."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".config" / "eve-gatekeeper" / "tokens.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._tokens: dict[int, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load tokens from file."""
        if self._path.exists():
            try:
                with self._path.open() as f:
                    data = json.load(f)
                    # Convert string keys back to int and parse dates
                    for char_id, token in data.items():
                        token["character_id"] = int(char_id)
                        token["expires_at"] = datetime.fromisoformat(token["expires_at"])
                        self._tokens[int(char_id)] = token
            except (json.JSONDecodeError, KeyError):
                self._tokens = {}

    def _save(self) -> None:
        """Save tokens to file."""
        data = {}
        for char_id, token in self._tokens.items():
            data[str(char_id)] = {
                **token,
                "expires_at": token["expires_at"].isoformat(),
            }
        with self._path.open("w") as f:
            json.dump(data, f, indent=2)

    async def store_token(
        self,
        character_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        character_name: str,
        scopes: list[str],
    ) -> None:
        self._tokens[character_id] = {
            "character_id": character_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "character_name": character_name,
            "scopes": scopes,
        }
        self._save()

    async def get_token(self, character_id: int) -> dict[str, Any] | None:
        return self._tokens.get(character_id)

    async def remove_token(self, character_id: int) -> bool:
        if character_id in self._tokens:
            del self._tokens[character_id]
            self._save()
            return True
        return False

    async def list_characters(self) -> list[dict[str, Any]]:
        return list(self._tokens.values())

    async def clear_all(self) -> int:
        count = len(self._tokens)
        self._tokens.clear()
        self._save()
        return count


class RedisTokenStore(TokenStore):
    """Redis-based token storage for production/multi-instance."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url)
        self._prefix = "eve_gatekeeper:token:"

    async def store_token(
        self,
        character_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        character_name: str,
        scopes: list[str],
    ) -> None:
        key = f"{self._prefix}{character_id}"
        data = {
            "character_id": character_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat(),
            "character_name": character_name,
            "scopes": json.dumps(scopes),
        }
        await self._redis.hset(key, mapping=data)
        # Add to character list
        await self._redis.sadd(f"{self._prefix}characters", character_id)

    async def get_token(self, character_id: int) -> dict[str, Any] | None:
        key = f"{self._prefix}{character_id}"
        data = await self._redis.hgetall(key)
        if not data:
            return None

        return {
            "character_id": int(data[b"character_id"]),
            "access_token": data[b"access_token"].decode(),
            "refresh_token": data[b"refresh_token"].decode(),
            "expires_at": datetime.fromisoformat(data[b"expires_at"].decode()),
            "character_name": data[b"character_name"].decode(),
            "scopes": json.loads(data[b"scopes"].decode()),
        }

    async def remove_token(self, character_id: int) -> bool:
        key = f"{self._prefix}{character_id}"
        deleted = await self._redis.delete(key)
        await self._redis.srem(f"{self._prefix}characters", character_id)
        return deleted > 0

    async def list_characters(self) -> list[dict[str, Any]]:
        char_ids = await self._redis.smembers(f"{self._prefix}characters")
        characters = []
        for char_id in char_ids:
            token = await self.get_token(int(char_id))
            if token:
                characters.append(token)
        return characters

    async def clear_all(self) -> int:
        char_ids = await self._redis.smembers(f"{self._prefix}characters")
        count = 0
        for char_id in char_ids:
            if await self.remove_token(int(char_id)):
                count += 1
        return count


# =============================================================================
# Dependency Injection
# =============================================================================

_token_store: TokenStore | None = None


def get_token_store() -> TokenStore:
    """Get the token store instance (FastAPI dependency)."""
    global _token_store

    if _token_store is None:
        if settings.REDIS_URL:
            _token_store = RedisTokenStore(settings.REDIS_URL)
        elif settings.DEBUG:
            _token_store = MemoryTokenStore()
        else:
            _token_store = FileTokenStore()

    return _token_store


def set_token_store(store: TokenStore) -> None:
    """Set the token store instance (for testing)."""
    global _token_store
    _token_store = store
