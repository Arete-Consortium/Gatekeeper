"""Unit tests for system notes service."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.services.system_notes import (
    NoteType,
    SystemNote,
    SystemNotesStore,
    get_notes_store,
    reset_notes_store,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the global notes store before each test."""
    reset_notes_store()
    yield
    reset_notes_store()


class TestNoteType:
    """Tests for NoteType enum."""

    def test_all_types_exist(self):
        """Test all expected note types exist."""
        assert NoteType.INFO.value == "info"
        assert NoteType.WARNING.value == "warning"
        assert NoteType.SAFE.value == "safe"
        assert NoteType.FLEET.value == "fleet"
        assert NoteType.BOOKMARK.value == "bookmark"
        assert NoteType.HOSTILE.value == "hostile"
        assert NoteType.FRIENDLY.value == "friendly"


class TestSystemNote:
    """Tests for SystemNote dataclass."""

    def test_basic_creation(self):
        """Test creating a basic note."""
        note = SystemNote(
            note_id="note_1",
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Test note",
        )
        assert note.note_id == "note_1"
        assert note.system_name == "Jita"
        assert note.content == "Test note"

    def test_is_expired_with_future_expiry(self):
        """Test is_expired returns False for future expiry."""
        note = SystemNote(
            note_id="note_1",
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Test",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert note.is_expired is False

    def test_is_expired_with_past_expiry(self):
        """Test is_expired returns True for past expiry."""
        note = SystemNote(
            note_id="note_1",
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Test",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert note.is_expired is True

    def test_is_expired_with_no_expiry(self):
        """Test is_expired returns False when no expiry set."""
        note = SystemNote(
            note_id="note_1",
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Test",
            expires_at=None,
        )
        assert note.is_expired is False

    def test_age_seconds(self):
        """Test age_seconds property."""
        past = datetime.now(UTC) - timedelta(seconds=30)
        note = SystemNote(
            note_id="note_1",
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Test",
            created_at=past,
        )
        assert 29 <= note.age_seconds <= 35


class TestSystemNotesStore:
    """Tests for SystemNotesStore class."""

    def test_add_note(self):
        """Test adding a note."""
        store = SystemNotesStore()
        note = store.add_note(
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Test note",
        )

        assert note.note_id is not None
        assert note.system_name == "Jita"
        assert note.content == "Test note"

    def test_add_note_with_author(self):
        """Test adding note with author."""
        store = SystemNotesStore()
        note = store.add_note(
            system_name="Jita",
            note_type=NoteType.WARNING,
            content="Danger!",
            author="TestPilot",
        )

        assert note.author == "TestPilot"

    def test_add_note_with_tags(self):
        """Test adding note with tags."""
        store = SystemNotesStore()
        note = store.add_note(
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Trade hub",
            tags=["trade", "highsec"],
        )

        assert "trade" in note.tags
        assert "highsec" in note.tags

    def test_add_note_string_type(self):
        """Test adding note with string type (auto-convert)."""
        store = SystemNotesStore()
        note = store.add_note(
            system_name="Jita",
            note_type="warning",
            content="Test",
        )

        assert note.note_type == NoteType.WARNING

    def test_get_note(self):
        """Test getting a note by ID."""
        store = SystemNotesStore()
        created = store.add_note(
            system_name="Jita",
            note_type=NoteType.INFO,
            content="Test",
        )

        retrieved = store.get_note(created.note_id)

        assert retrieved is not None
        assert retrieved.note_id == created.note_id

    def test_get_nonexistent_note(self):
        """Test getting nonexistent note returns None."""
        store = SystemNotesStore()
        result = store.get_note("nonexistent")
        assert result is None

    def test_get_system_notes(self):
        """Test getting notes for a system."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Note 1")
        store.add_note("Jita", NoteType.WARNING, "Note 2")
        store.add_note("Amarr", NoteType.INFO, "Other system")

        notes = store.get_system_notes("Jita")

        assert len(notes) == 2
        assert all(n.system_name == "Jita" for n in notes)

    def test_get_system_notes_by_type(self):
        """Test getting notes filtered by type."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Info note")
        store.add_note("Jita", NoteType.WARNING, "Warning note")
        store.add_note("Jita", NoteType.WARNING, "Another warning")

        notes = store.get_system_notes("Jita", note_type=NoteType.WARNING)

        assert len(notes) == 2
        assert all(n.note_type == NoteType.WARNING for n in notes)

    def test_get_system_notes_by_author(self):
        """Test getting notes filtered by author."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Note 1", author="Alice")
        store.add_note("Jita", NoteType.INFO, "Note 2", author="Bob")
        store.add_note("Jita", NoteType.INFO, "Note 3", author="Alice")

        notes = store.get_system_notes("Jita", author="Alice")

        assert len(notes) == 2
        assert all(n.author == "Alice" for n in notes)

    def test_get_system_notes_excludes_private(self):
        """Test that private notes are excluded by default."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Public note", is_shared=True)
        store.add_note("Jita", NoteType.INFO, "Private note", is_shared=False)

        notes = store.get_system_notes("Jita")

        assert len(notes) == 1
        assert notes[0].is_shared is True

    def test_get_system_summary(self):
        """Test getting notes summary for a system."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Info note")
        store.add_note("Jita", NoteType.WARNING, "Warning note")

        summary = store.get_system_summary("Jita")

        assert summary.system_name == "Jita"
        assert summary.total_notes == 2
        assert summary.has_warnings is True
        assert "info" in summary.note_types
        assert "warning" in summary.note_types

    def test_update_note(self):
        """Test updating a note."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Original content")

        updated = store.update_note(note.note_id, content="Updated content")

        assert updated is not None
        assert updated.content == "Updated content"
        assert updated.updated_at is not None

    def test_update_note_type(self):
        """Test updating note type."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Content")

        updated = store.update_note(note.note_id, note_type=NoteType.WARNING)

        assert updated.note_type == NoteType.WARNING

    def test_update_nonexistent_note(self):
        """Test updating nonexistent note returns None."""
        store = SystemNotesStore()
        result = store.update_note("nonexistent", content="Test")
        assert result is None

    def test_delete_note(self):
        """Test deleting a note."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Test")

        assert store.delete_note(note.note_id) is True
        assert store.get_note(note.note_id) is None

    def test_delete_nonexistent_note(self):
        """Test deleting nonexistent note returns False."""
        store = SystemNotesStore()
        assert store.delete_note("nonexistent") is False

    def test_get_all_warnings(self):
        """Test getting all warning/hostile notes."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.WARNING, "Warning in Jita")
        store.add_note("Amarr", NoteType.HOSTILE, "Hostile in Amarr")
        store.add_note("Dodixie", NoteType.INFO, "Info note")

        warnings = store.get_all_warnings()

        assert len(warnings) == 2
        assert "Jita" in warnings
        assert "Amarr" in warnings
        assert "Dodixie" not in warnings

    def test_get_notes_for_route(self):
        """Test getting notes for a route."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Jita note")
        store.add_note("Perimeter", NoteType.WARNING, "Perimeter note")

        route = ["Jita", "Perimeter", "Urlen", "Amarr"]
        notes = store.get_notes_for_route(route)

        assert len(notes) == 2
        assert "Jita" in notes
        assert "Perimeter" in notes
        assert "Urlen" not in notes

    def test_search_notes(self):
        """Test searching notes by content."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Trade hub")
        store.add_note("Amarr", NoteType.INFO, "Another trade hub")
        store.add_note("Dodixie", NoteType.INFO, "Market system")

        results = store.search_notes("trade")

        assert len(results) == 2

    def test_search_notes_by_tag(self):
        """Test searching notes matches tags."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Content", tags=["trade", "hub"])
        store.add_note("Amarr", NoteType.INFO, "Other content", tags=["market"])

        results = store.search_notes("trade")

        assert len(results) == 1
        assert results[0].system_name == "Jita"

    def test_search_notes_by_system_name(self):
        """Test searching notes matches system name."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Content")
        store.add_note("Amarr", NoteType.INFO, "Other content")

        results = store.search_notes("jita")

        assert len(results) == 1
        assert results[0].system_name == "Jita"

    def test_clear_system(self):
        """Test clearing all notes for a system."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Note 1")
        store.add_note("Jita", NoteType.INFO, "Note 2")
        store.add_note("Amarr", NoteType.INFO, "Other")

        store.clear_system("Jita")

        assert len(store.get_system_notes("Jita")) == 0
        assert len(store.get_system_notes("Amarr")) == 1

    def test_clear_all(self):
        """Test clearing all notes."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Note 1")
        store.add_note("Amarr", NoteType.INFO, "Note 2")

        store.clear_all()

        assert len(store.get_system_notes("Jita")) == 0
        assert len(store.get_system_notes("Amarr")) == 0

    def test_max_notes_per_system(self):
        """Test max notes per system limit."""
        store = SystemNotesStore(max_notes_per_system=3)

        for i in range(5):
            store.add_note("Jita", NoteType.INFO, f"Note {i}")

        notes = store.get_system_notes("Jita")
        assert len(notes) == 3

    def test_subscribe_callback(self):
        """Test subscription callbacks."""
        store = SystemNotesStore()
        callback_data = []

        def callback(system, note):
            callback_data.append((system, note))

        store.subscribe(callback)
        store.add_note("Jita", NoteType.INFO, "Test")

        assert len(callback_data) == 1
        assert callback_data[0][0] == "Jita"

    def test_prune_expired(self):
        """Test expired notes are pruned."""
        store = SystemNotesStore()
        note = store.add_note(
            "Jita",
            NoteType.INFO,
            "Expiring note",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        # Trigger prune
        store._prune_expired()

        assert store.get_note(note.note_id) is None


class TestGetNotesStore:
    """Tests for get_notes_store singleton."""

    def test_returns_same_instance(self):
        """Test singleton returns same instance."""
        store1 = get_notes_store()
        store2 = get_notes_store()
        assert store1 is store2

    def test_reset_creates_new_instance(self):
        """Test reset creates new instance."""
        store1 = get_notes_store()
        reset_notes_store()
        store2 = get_notes_store()
        assert store1 is not store2


class TestSystemNotesEdgeCases:
    """Additional edge case tests for system notes."""

    def test_subscriber_exception_does_not_crash(self):
        """Test that subscriber exceptions don't crash add_note."""
        store = SystemNotesStore()

        def bad_callback(system, note):
            raise ValueError("Callback error")

        store.subscribe(bad_callback)

        # Should not raise despite callback error
        note = store.add_note("Jita", NoteType.INFO, "Test")
        assert note is not None

    def test_unsubscribe_callback(self):
        """Test unsubscribing a callback."""
        store = SystemNotesStore()
        callback_data = []

        def callback(system, note):
            callback_data.append(note)

        store.subscribe(callback)
        store.add_note("Jita", NoteType.INFO, "Note 1")
        assert len(callback_data) == 1

        store.unsubscribe(callback)
        store.add_note("Jita", NoteType.INFO, "Note 2")
        assert len(callback_data) == 1  # No new callback

    def test_unsubscribe_nonexistent_callback(self):
        """Test unsubscribing a callback that wasn't subscribed."""
        store = SystemNotesStore()

        def callback(system, note):
            pass

        # Should not raise
        store.unsubscribe(callback)

    def test_get_system_notes_string_note_type(self):
        """Test get_system_notes with string note_type."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Info note")
        store.add_note("Jita", NoteType.WARNING, "Warning note")

        notes = store.get_system_notes("Jita", note_type="warning")

        assert len(notes) == 1
        assert notes[0].note_type == NoteType.WARNING

    def test_get_system_notes_include_private(self):
        """Test get_system_notes with include_private=True."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Public", is_shared=True)
        store.add_note("Jita", NoteType.INFO, "Private", is_shared=False)

        notes = store.get_system_notes("Jita", include_private=True)

        assert len(notes) == 2

    def test_update_note_with_string_type(self):
        """Test updating note with string note_type."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Content")

        updated = store.update_note(note.note_id, note_type="warning")

        assert updated.note_type == NoteType.WARNING

    def test_update_note_tags(self):
        """Test updating note tags."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Content", tags=["old"])

        updated = store.update_note(note.note_id, tags=["new", "tags"])

        assert updated.tags == ["new", "tags"]

    def test_update_note_is_shared(self):
        """Test updating note is_shared status."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Content", is_shared=True)

        updated = store.update_note(note.note_id, is_shared=False)

        assert updated.is_shared is False

    def test_update_note_expires_at(self):
        """Test updating note expires_at."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Content")

        new_expiry = datetime.now(UTC) + timedelta(hours=24)
        updated = store.update_note(note.note_id, expires_at=new_expiry)

        assert updated.expires_at == new_expiry

    def test_delete_note_cleans_empty_system(self):
        """Test that deleting last note removes system entry."""
        store = SystemNotesStore()
        note = store.add_note("Jita", NoteType.INFO, "Only note")

        store.delete_note(note.note_id)

        # System should have no notes
        assert store.get_system_notes("Jita") == []

    def test_search_notes_excludes_expired(self):
        """Test search excludes expired notes."""
        store = SystemNotesStore()
        store.add_note(
            "Jita",
            NoteType.INFO,
            "Expired note",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        store.add_note("Amarr", NoteType.INFO, "Valid note")

        results = store.search_notes("note")

        assert len(results) == 1
        assert results[0].system_name == "Amarr"

    def test_search_notes_excludes_private(self):
        """Test search excludes private notes."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Private note", is_shared=False)
        store.add_note("Amarr", NoteType.INFO, "Public note", is_shared=True)

        results = store.search_notes("note")

        assert len(results) == 1
        assert results[0].system_name == "Amarr"

    def test_search_notes_with_string_note_type(self):
        """Test search with string note_type filter."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Info note")
        store.add_note("Amarr", NoteType.WARNING, "Warning note")

        results = store.search_notes("note", note_type="warning")

        assert len(results) == 1
        assert results[0].note_type == NoteType.WARNING

    def test_search_notes_type_filter_excludes(self):
        """Test search with note_type excludes non-matching."""
        store = SystemNotesStore()
        store.add_note("Jita", NoteType.INFO, "Info content")
        store.add_note("Amarr", NoteType.WARNING, "Warning content")

        results = store.search_notes("content", note_type=NoteType.INFO)

        assert len(results) == 1
        assert results[0].system_name == "Jita"

    def test_clear_system_nonexistent(self):
        """Test clearing a system that doesn't exist."""
        store = SystemNotesStore()
        store.add_note("Amarr", NoteType.INFO, "Note")

        # Should not raise for nonexistent system
        store.clear_system("Jita")

        # Amarr should still have its note
        assert len(store.get_system_notes("Amarr")) == 1

    def test_get_note_returns_none_for_expired(self):
        """Test get_note returns None for expired notes."""
        store = SystemNotesStore()
        note = store.add_note(
            "Jita",
            NoteType.INFO,
            "Expired",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        # The note exists but is expired
        result = store.get_note(note.note_id)
        assert result is None
