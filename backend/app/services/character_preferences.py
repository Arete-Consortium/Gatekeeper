"""Character preferences service for multi-character support.

Manages storage and retrieval of per-character preferences with support for:
- In-memory storage (development)
- File-based storage (single instance)
- Redis storage (production/multi-instance)
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.config import settings
from ..models.character_preferences import (
    CharacterPreferences,
    CharacterPreferencesUpdate,
)

logger = logging.getLogger(__name__)


class CharacterPreferencesStore(ABC):
    """Abstract base class for character preferences storage."""

    @abstractmethod
    async def get_preferences(self, character_id: int) -> CharacterPreferences | None:
        """Get preferences for a character."""
        pass

    @abstractmethod
    async def save_preferences(self, prefs: CharacterPreferences) -> None:
        """Save preferences for a character."""
        pass

    @abstractmethod
    async def delete_preferences(self, character_id: int) -> bool:
        """Delete preferences for a character."""
        pass

    @abstractmethod
    async def list_all(self) -> list[CharacterPreferences]:
        """List all character preferences."""
        pass

    async def get_or_create(self, character_id: int, character_name: str) -> CharacterPreferences:
        """Get preferences or create default if not exists."""
        prefs = await self.get_preferences(character_id)
        if prefs is None:
            prefs = CharacterPreferences(
                character_id=character_id,
                character_name=character_name,
            )
            await self.save_preferences(prefs)
            logger.info(
                "Created default preferences",
                extra={"character_id": character_id, "character_name": character_name},
            )
        return prefs

    async def update_preferences(
        self,
        character_id: int,
        update: CharacterPreferencesUpdate,
    ) -> CharacterPreferences | None:
        """Update preferences for a character.

        Args:
            character_id: Character ID to update
            update: Partial update to apply

        Returns:
            Updated preferences or None if not found
        """
        prefs = await self.get_preferences(character_id)
        if prefs is None:
            return None

        # Apply updates
        if update.routing is not None:
            prefs.routing = update.routing
        if update.alerts is not None:
            prefs.alerts = update.alerts
        if update.ui is not None:
            prefs.ui = update.ui
        if update.home_system is not None:
            prefs.home_system = update.home_system
        if update.notes is not None:
            prefs.notes = update.notes

        prefs.updated_at = datetime.now(UTC)
        await self.save_preferences(prefs)
        return prefs


class MemoryPreferencesStore(CharacterPreferencesStore):
    """In-memory preferences storage for development."""

    def __init__(self) -> None:
        self._preferences: dict[int, CharacterPreferences] = {}

    async def get_preferences(self, character_id: int) -> CharacterPreferences | None:
        return self._preferences.get(character_id)

    async def save_preferences(self, prefs: CharacterPreferences) -> None:
        self._preferences[prefs.character_id] = prefs
        logger.debug(
            "Preferences saved",
            extra={
                "character_id": prefs.character_id,
                "store_type": "memory",
            },
        )

    async def delete_preferences(self, character_id: int) -> bool:
        if character_id in self._preferences:
            del self._preferences[character_id]
            return True
        return False

    async def list_all(self) -> list[CharacterPreferences]:
        return list(self._preferences.values())


class FilePreferencesStore(CharacterPreferencesStore):
    """File-based preferences storage for single-instance deployments."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".config" / "eve-gatekeeper" / "preferences.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._preferences: dict[int, CharacterPreferences] = {}
        self._load()

    def _load(self) -> None:
        """Load preferences from file."""
        if self._path.exists():
            try:
                with self._path.open() as f:
                    data = json.load(f)
                    for char_id, prefs_data in data.items():
                        self._preferences[int(char_id)] = CharacterPreferences(**prefs_data)
                logger.info(
                    "Preferences loaded from file",
                    extra={"path": str(self._path), "count": len(self._preferences)},
                )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(
                    "Failed to load preferences from file",
                    extra={"path": str(self._path), "error": str(e)},
                )
                self._preferences = {}

    def _save(self) -> None:
        """Save preferences to file."""
        import os

        data = {}
        for char_id, prefs in self._preferences.items():
            data[str(char_id)] = prefs.model_dump(mode="json")

        # Write atomically
        temp_path = self._path.with_suffix(".tmp")
        with temp_path.open("w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(temp_path, self._path)

        try:
            os.chmod(self._path, 0o600)
        except OSError:
            pass

    async def get_preferences(self, character_id: int) -> CharacterPreferences | None:
        return self._preferences.get(character_id)

    async def save_preferences(self, prefs: CharacterPreferences) -> None:
        self._preferences[prefs.character_id] = prefs
        self._save()
        logger.debug(
            "Preferences saved",
            extra={
                "character_id": prefs.character_id,
                "store_type": "file",
            },
        )

    async def delete_preferences(self, character_id: int) -> bool:
        if character_id in self._preferences:
            del self._preferences[character_id]
            self._save()
            return True
        return False

    async def list_all(self) -> list[CharacterPreferences]:
        return list(self._preferences.values())


class RedisPreferencesStore(CharacterPreferencesStore):
    """Redis-based preferences storage for production/multi-instance."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(redis_url)
        self._prefix = "eve_gatekeeper:prefs:"

    async def get_preferences(self, character_id: int) -> CharacterPreferences | None:
        key = f"{self._prefix}{character_id}"
        data = await self._redis.get(key)
        if not data:
            return None
        try:
            return CharacterPreferences(**json.loads(data))
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(
                "Failed to parse preferences from Redis",
                extra={"character_id": character_id, "error": str(e)},
            )
            return None

    async def save_preferences(self, prefs: CharacterPreferences) -> None:
        key = f"{self._prefix}{prefs.character_id}"
        data = prefs.model_dump_json()
        await self._redis.set(key, data)
        # Add to character list
        await self._redis.sadd(f"{self._prefix}all", prefs.character_id)
        logger.debug(
            "Preferences saved",
            extra={
                "character_id": prefs.character_id,
                "store_type": "redis",
            },
        )

    async def delete_preferences(self, character_id: int) -> bool:
        key = f"{self._prefix}{character_id}"
        deleted = await self._redis.delete(key)
        await self._redis.srem(f"{self._prefix}all", character_id)
        return bool(deleted > 0)

    async def list_all(self) -> list[CharacterPreferences]:
        char_ids = await self._redis.smembers(f"{self._prefix}all")
        result = []
        for char_id in char_ids:
            prefs = await self.get_preferences(int(char_id))
            if prefs:
                result.append(prefs)
        return result


# =============================================================================
# Active Character Session Management
# =============================================================================


class ActiveCharacterManager:
    """Manages active character selection per session/client.

    In a stateless API, the active character is typically passed via
    headers or stored client-side. This manager provides server-side
    session storage for clients that prefer it.
    """

    def __init__(self) -> None:
        # session_id -> character_id
        self._active: dict[str, int] = {}

    def set_active(self, session_id: str, character_id: int) -> None:
        """Set the active character for a session."""
        self._active[session_id] = character_id
        logger.debug(
            "Active character set",
            extra={"session_id": session_id, "character_id": character_id},
        )

    def get_active(self, session_id: str) -> int | None:
        """Get the active character for a session."""
        return self._active.get(session_id)

    def clear_active(self, session_id: str) -> None:
        """Clear the active character for a session."""
        self._active.pop(session_id, None)

    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        return {
            "active_sessions": len(self._active),
            "unique_characters": len(set(self._active.values())),
        }


# =============================================================================
# Dependency Injection
# =============================================================================

_preferences_store: CharacterPreferencesStore | None = None
_active_manager: ActiveCharacterManager | None = None


def get_preferences_store() -> CharacterPreferencesStore:
    """Get the preferences store instance."""
    global _preferences_store

    if _preferences_store is None:
        if settings.REDIS_URL:
            _preferences_store = RedisPreferencesStore(settings.REDIS_URL)
        elif settings.DEBUG:
            _preferences_store = MemoryPreferencesStore()
        else:
            _preferences_store = FilePreferencesStore()

    return _preferences_store


def get_active_manager() -> ActiveCharacterManager:
    """Get the active character manager instance."""
    global _active_manager

    if _active_manager is None:
        _active_manager = ActiveCharacterManager()

    return _active_manager


def set_preferences_store(store: CharacterPreferencesStore) -> None:
    """Set the preferences store instance (for testing)."""
    global _preferences_store
    _preferences_store = store
