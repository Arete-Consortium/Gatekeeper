"""System notes service for user annotations on systems.

Allows users to add notes, warnings, and tags to systems.
Notes can be personal or shared with the community.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock


class NoteType(StrEnum):
    """Type of system note."""

    INFO = "info"  # General information
    WARNING = "warning"  # Danger warning
    SAFE = "safe"  # Safe haven indicator
    FLEET = "fleet"  # Fleet staging/contact
    BOOKMARK = "bookmark"  # Notable location
    HOSTILE = "hostile"  # Known hostile activity
    FRIENDLY = "friendly"  # Friendly space


@dataclass
class SystemNote:
    """A note attached to a system."""

    note_id: str
    system_name: str
    note_type: NoteType
    content: str
    author: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    is_shared: bool = True  # Whether visible to others
    expires_at: datetime | None = None  # Optional expiry

    @property
    def is_expired(self) -> bool:
        """Check if note has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Get age of note in seconds."""
        return (datetime.now(UTC) - self.created_at).total_seconds()


@dataclass
class SystemNotesSummary:
    """Summary of notes for a system."""

    system_name: str
    total_notes: int
    note_types: dict[str, int]  # Count by type
    has_warnings: bool
    latest_note: SystemNote | None
    notes: list[SystemNote]


class SystemNotesStore:
    """In-memory storage for system notes."""

    def __init__(self, max_notes_per_system: int = 50):
        self._notes: dict[str, dict[str, SystemNote]] = {}  # system -> {note_id: note}
        self._lock = RLock()
        self._next_id = 1
        self.max_notes_per_system = max_notes_per_system
        self._subscribers: list[Callable[[str, SystemNote], None]] = []

    def _generate_id(self) -> str:
        """Generate a unique note ID."""
        with self._lock:
            note_id = f"note_{self._next_id}"
            self._next_id += 1
            return note_id

    def _prune_expired(self) -> None:
        """Remove expired notes."""
        now = datetime.now(UTC)
        with self._lock:
            for system_name in list(self._notes.keys()):
                expired_ids = [
                    note_id
                    for note_id, note in self._notes[system_name].items()
                    if note.expires_at and note.expires_at < now
                ]
                for note_id in expired_ids:
                    del self._notes[system_name][note_id]

                if not self._notes[system_name]:
                    del self._notes[system_name]

    def add_note(
        self,
        system_name: str,
        note_type: NoteType | str,
        content: str,
        author: str | None = None,
        tags: list[str] | None = None,
        is_shared: bool = True,
        expires_at: datetime | None = None,
    ) -> SystemNote:
        """
        Add a note to a system.

        Args:
            system_name: Name of the system
            note_type: Type of note
            content: Note content
            author: Optional author name
            tags: Optional list of tags
            is_shared: Whether note is visible to others
            expires_at: Optional expiry time

        Returns:
            Created SystemNote
        """
        self._prune_expired()

        if isinstance(note_type, str):
            note_type = NoteType(note_type)

        note = SystemNote(
            note_id=self._generate_id(),
            system_name=system_name,
            note_type=note_type,
            content=content,
            author=author,
            tags=tags or [],
            is_shared=is_shared,
            expires_at=expires_at,
        )

        with self._lock:
            if system_name not in self._notes:
                self._notes[system_name] = {}

            # Limit notes per system
            if len(self._notes[system_name]) >= self.max_notes_per_system:
                # Remove oldest note
                oldest_id = min(
                    self._notes[system_name].keys(),
                    key=lambda x: self._notes[system_name][x].created_at,
                )
                del self._notes[system_name][oldest_id]

            self._notes[system_name][note.note_id] = note

        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(system_name, note)
            except Exception:
                pass

        return note

    def get_note(self, note_id: str) -> SystemNote | None:
        """Get a specific note by ID."""
        self._prune_expired()

        with self._lock:
            for system_notes in self._notes.values():
                if note_id in system_notes:
                    note = system_notes[note_id]
                    return note if not note.is_expired else None
            return None

    def get_system_notes(
        self,
        system_name: str,
        note_type: NoteType | str | None = None,
        include_private: bool = False,
        author: str | None = None,
    ) -> list[SystemNote]:
        """
        Get notes for a system.

        Args:
            system_name: Name of the system
            note_type: Optional filter by type
            include_private: Include non-shared notes
            author: Optional filter by author

        Returns:
            List of notes, sorted by created_at descending
        """
        self._prune_expired()

        with self._lock:
            if system_name not in self._notes:
                return []

            notes = list(self._notes[system_name].values())

        # Filter
        if note_type:
            if isinstance(note_type, str):
                note_type = NoteType(note_type)
            notes = [n for n in notes if n.note_type == note_type]

        if not include_private:
            notes = [n for n in notes if n.is_shared]

        if author:
            notes = [n for n in notes if n.author == author]

        # Remove expired
        notes = [n for n in notes if not n.is_expired]

        # Sort by created_at descending
        notes.sort(key=lambda x: x.created_at, reverse=True)

        return notes

    def get_system_summary(self, system_name: str) -> SystemNotesSummary:
        """Get summary of notes for a system."""
        notes = self.get_system_notes(system_name)

        # Count by type
        type_counts: dict[str, int] = {}
        for note in notes:
            type_counts[note.note_type.value] = type_counts.get(note.note_type.value, 0) + 1

        has_warnings = any(n.note_type in (NoteType.WARNING, NoteType.HOSTILE) for n in notes)

        return SystemNotesSummary(
            system_name=system_name,
            total_notes=len(notes),
            note_types=type_counts,
            has_warnings=has_warnings,
            latest_note=notes[0] if notes else None,
            notes=notes,
        )

    def update_note(
        self,
        note_id: str,
        content: str | None = None,
        note_type: NoteType | str | None = None,
        tags: list[str] | None = None,
        is_shared: bool | None = None,
        expires_at: datetime | None = None,
    ) -> SystemNote | None:
        """
        Update an existing note.

        Args:
            note_id: ID of note to update
            content: New content (optional)
            note_type: New type (optional)
            tags: New tags (optional)
            is_shared: New shared status (optional)
            expires_at: New expiry (optional)

        Returns:
            Updated note, or None if not found
        """
        with self._lock:
            for system_notes in self._notes.values():
                if note_id in system_notes:
                    note = system_notes[note_id]

                    if content is not None:
                        note.content = content
                    if note_type is not None:
                        if isinstance(note_type, str):
                            note_type = NoteType(note_type)
                        note.note_type = note_type
                    if tags is not None:
                        note.tags = tags
                    if is_shared is not None:
                        note.is_shared = is_shared
                    if expires_at is not None:
                        note.expires_at = expires_at

                    note.updated_at = datetime.now(UTC)
                    return note

        return None

    def delete_note(self, note_id: str) -> bool:
        """
        Delete a note by ID.

        Args:
            note_id: ID of note to delete

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            for system_name, system_notes in self._notes.items():
                if note_id in system_notes:
                    del system_notes[note_id]
                    if not system_notes:
                        del self._notes[system_name]
                    return True
        return False

    def get_all_warnings(self) -> dict[str, list[SystemNote]]:
        """Get all warning/hostile notes grouped by system."""
        self._prune_expired()

        result: dict[str, list[SystemNote]] = {}

        with self._lock:
            for system_name, system_notes in self._notes.items():
                warnings = [
                    n
                    for n in system_notes.values()
                    if n.note_type in (NoteType.WARNING, NoteType.HOSTILE)
                    and n.is_shared
                    and not n.is_expired
                ]
                if warnings:
                    result[system_name] = sorted(warnings, key=lambda x: x.created_at, reverse=True)

        return result

    def get_notes_for_route(self, system_names: list[str]) -> dict[str, SystemNotesSummary]:
        """
        Get note summaries for all systems in a route.

        Args:
            system_names: List of system names

        Returns:
            Dict mapping system name to SystemNotesSummary
        """
        result = {}
        for system_name in system_names:
            summary = self.get_system_summary(system_name)
            if summary.total_notes > 0:
                result[system_name] = summary
        return result

    def search_notes(
        self,
        query: str,
        note_type: NoteType | str | None = None,
        limit: int = 50,
    ) -> list[SystemNote]:
        """
        Search notes by content.

        Args:
            query: Search query (case-insensitive)
            note_type: Optional filter by type
            limit: Max results

        Returns:
            List of matching notes
        """
        self._prune_expired()
        query_lower = query.lower()

        results: list[SystemNote] = []

        with self._lock:
            for system_notes in self._notes.values():
                for note in system_notes.values():
                    if note.is_expired or not note.is_shared:
                        continue

                    if note_type:
                        if isinstance(note_type, str):
                            note_type = NoteType(note_type)
                        if note.note_type != note_type:
                            continue

                    # Search in content, tags, and system name
                    if (
                        query_lower in note.content.lower()
                        or query_lower in note.system_name.lower()
                        or any(query_lower in tag.lower() for tag in note.tags)
                    ):
                        results.append(note)

        # Sort by created_at descending and limit
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]

    def subscribe(self, callback: Callable[[str, SystemNote], None]) -> None:
        """Subscribe to note changes."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, SystemNote], None]) -> None:
        """Unsubscribe from note changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def clear_system(self, system_name: str) -> None:
        """Clear all notes for a system."""
        with self._lock:
            if system_name in self._notes:
                del self._notes[system_name]

    def clear_all(self) -> None:
        """Clear all notes."""
        with self._lock:
            self._notes.clear()


# Global store instance
_notes_store: SystemNotesStore | None = None


def get_notes_store() -> SystemNotesStore:
    """Get the global notes store instance."""
    global _notes_store
    if _notes_store is None:
        _notes_store = SystemNotesStore()
    return _notes_store


def reset_notes_store() -> None:
    """Reset the global notes store (for testing)."""
    global _notes_store
    _notes_store = None
