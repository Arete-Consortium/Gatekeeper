"""Token Storage Service for ESI OAuth2 tokens.

Provides persistent storage for EVE SSO tokens with support for:
- In-memory storage (development)
- File-based storage (single instance)
- Redis storage (production/multi-instance)
- Token encryption at rest
- Proactive token refresh tracking
"""

import json
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.config import settings
from .jwt_service import decrypt_token, encrypt_token, should_refresh_esi_token


class TokenStore(ABC):
    """Abstract base class for token storage."""

    # Whether to encrypt tokens at rest
    encrypt_tokens: bool = True

    def _encrypt(self, token: str) -> str:
        """Encrypt a token if encryption is enabled."""
        if self.encrypt_tokens:
            return encrypt_token(token)
        return token

    def _decrypt(self, token: str) -> str:
        """Decrypt a token if encryption is enabled."""
        if self.encrypt_tokens:
            return decrypt_token(token)
        return token

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

    async def get_tokens_needing_refresh(self) -> list[dict[str, Any]]:
        """Get all tokens that need proactive refresh.

        Returns tokens expiring within ESI_REFRESH_THRESHOLD_SECONDS.
        """
        characters = await self.list_characters()
        return [char for char in characters if should_refresh_esi_token(char["expires_at"])]

    async def is_token_valid(self, character_id: int) -> bool:
        """Check if a token exists and is not expired.

        Args:
            character_id: Character ID to check

        Returns:
            True if token exists and is valid
        """
        token = await self.get_token(character_id)
        if not token:
            return False
        return datetime.now(UTC) < token["expires_at"]


class MemoryTokenStore(TokenStore):
    """In-memory token storage for development.

    Note: Encryption is disabled for memory store since tokens
    are already protected in process memory.
    """

    def __init__(self, encrypt: bool = False) -> None:
        self._tokens: dict[int, dict[str, Any]] = {}
        self.encrypt_tokens = encrypt

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
            "access_token": self._encrypt(access_token) if self.encrypt_tokens else access_token,
            "refresh_token": self._encrypt(refresh_token) if self.encrypt_tokens else refresh_token,
            "expires_at": expires_at,
            "character_name": character_name,
            "scopes": scopes,
        }

    async def get_token(self, character_id: int) -> dict[str, Any] | None:
        stored = self._tokens.get(character_id)
        if not stored:
            return None

        # Return decrypted copy
        result = stored.copy()
        if self.encrypt_tokens:
            result["access_token"] = self._decrypt(stored["access_token"])
            result["refresh_token"] = self._decrypt(stored["refresh_token"])
        return result

    async def remove_token(self, character_id: int) -> bool:
        if character_id in self._tokens:
            del self._tokens[character_id]
            return True
        return False

    async def list_characters(self) -> list[dict[str, Any]]:
        # Return decrypted copies
        result = []
        for stored in self._tokens.values():
            char = stored.copy()
            if self.encrypt_tokens:
                char["access_token"] = self._decrypt(stored["access_token"])
                char["refresh_token"] = self._decrypt(stored["refresh_token"])
            result.append(char)
        return result

    async def clear_all(self) -> int:
        count = len(self._tokens)
        self._tokens.clear()
        return count


class FileTokenStore(TokenStore):
    """File-based token storage for single-instance deployments.

    Tokens are encrypted before writing to disk for security.
    """

    def __init__(self, path: Path | None = None, encrypt: bool = True) -> None:
        self._path = path or Path.home() / ".config" / "eve-gatekeeper" / "tokens.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._tokens: dict[int, dict[str, Any]] = {}
        self.encrypt_tokens = encrypt
        self._load()

    def _load(self) -> None:
        """Load tokens from file (stored encrypted)."""
        if self._path.exists():
            try:
                with self._path.open() as f:
                    data = json.load(f)
                    # Convert string keys back to int and parse dates
                    for char_id, token in data.items():
                        token["character_id"] = int(char_id)
                        token["expires_at"] = datetime.fromisoformat(token["expires_at"])
                        # Tokens are stored encrypted, keep them that way in memory
                        self._tokens[int(char_id)] = token
            except (json.JSONDecodeError, KeyError):
                self._tokens = {}

    def _save(self) -> None:
        """Save tokens to file (encrypted)."""
        import os

        data = {}
        for char_id, token in self._tokens.items():
            data[str(char_id)] = {
                **token,
                "expires_at": token["expires_at"].isoformat(),
            }

        # Write atomically to prevent corruption
        temp_path = self._path.with_suffix(".tmp")
        with temp_path.open("w") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, self._path)

        # Set restrictive permissions (owner read/write only)
        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass  # May fail on Windows

    async def store_token(
        self,
        character_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        character_name: str,
        scopes: list[str],
    ) -> None:
        # Encrypt tokens before storing
        self._tokens[character_id] = {
            "character_id": character_id,
            "access_token": self._encrypt(access_token),
            "refresh_token": self._encrypt(refresh_token),
            "expires_at": expires_at,
            "character_name": character_name,
            "scopes": scopes,
        }
        self._save()

    async def get_token(self, character_id: int) -> dict[str, Any] | None:
        stored = self._tokens.get(character_id)
        if not stored:
            return None

        # Return decrypted copy
        return {
            **stored,
            "access_token": self._decrypt(stored["access_token"]),
            "refresh_token": self._decrypt(stored["refresh_token"]),
        }

    async def remove_token(self, character_id: int) -> bool:
        if character_id in self._tokens:
            del self._tokens[character_id]
            self._save()
            return True
        return False

    async def list_characters(self) -> list[dict[str, Any]]:
        # Return decrypted copies
        result = []
        for stored in self._tokens.values():
            result.append(
                {
                    **stored,
                    "access_token": self._decrypt(stored["access_token"]),
                    "refresh_token": self._decrypt(stored["refresh_token"]),
                }
            )
        return result

    async def clear_all(self) -> int:
        count = len(self._tokens)
        self._tokens.clear()
        self._save()
        return count


class RedisTokenStore(TokenStore):
    """Redis-based token storage for production/multi-instance.

    Tokens are encrypted before storing in Redis for defense-in-depth.
    """

    def __init__(self, redis_url: str, encrypt: bool = True) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url)
        self._prefix = "eve_gatekeeper:token:"
        self.encrypt_tokens = encrypt

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
            "access_token": self._encrypt(access_token),
            "refresh_token": self._encrypt(refresh_token),
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

        # Decrypt tokens when retrieving
        return {
            "character_id": int(data[b"character_id"]),
            "access_token": self._decrypt(data[b"access_token"].decode()),
            "refresh_token": self._decrypt(data[b"refresh_token"].decode()),
            "expires_at": datetime.fromisoformat(data[b"expires_at"].decode()),
            "character_name": data[b"character_name"].decode(),
            "scopes": json.loads(data[b"scopes"].decode()),
        }

    async def remove_token(self, character_id: int) -> bool:
        key = f"{self._prefix}{character_id}"
        deleted = await self._redis.delete(key)
        await self._redis.srem(f"{self._prefix}characters", character_id)
        return bool(deleted > 0)

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
