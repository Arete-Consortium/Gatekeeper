"""Tests for multi-character support."""


import pytest
from app.models.character_preferences import (
    AlertPreferences,
    CharacterPreferences,
    CharacterPreferencesUpdate,
    RoutingPreferences,
    UIPreferences,
)
from app.services.character_preferences import (
    ActiveCharacterManager,
    MemoryPreferencesStore,
)

# =============================================================================
# Preferences Model Tests
# =============================================================================


class TestCharacterPreferencesModel:
    """Tests for character preferences model."""

    def test_create_default_preferences(self):
        """Test creating preferences with defaults."""
        prefs = CharacterPreferences(
            character_id=12345,
            character_name="Test Pilot",
        )

        assert prefs.character_id == 12345
        assert prefs.character_name == "Test Pilot"
        assert prefs.routing.default_profile == "safer"
        assert prefs.routing.avoid_systems == []
        assert prefs.alerts.enabled is True
        assert prefs.ui.theme == "dark"

    def test_create_preferences_with_custom_values(self):
        """Test creating preferences with custom values."""
        prefs = CharacterPreferences(
            character_id=12345,
            character_name="Test Pilot",
            routing=RoutingPreferences(
                default_profile="paranoid",
                avoid_systems=["Tama", "Rancer"],
                use_bridges=True,
            ),
            alerts=AlertPreferences(
                enabled=True,
                min_value_isk=1000000,
                watch_systems=["Jita"],
            ),
            ui=UIPreferences(
                theme="light",
                compact_mode=True,
            ),
            home_system="Jita",
        )

        assert prefs.routing.default_profile == "paranoid"
        assert "Tama" in prefs.routing.avoid_systems
        assert prefs.routing.use_bridges is True
        assert prefs.alerts.min_value_isk == 1000000
        assert prefs.ui.theme == "light"
        assert prefs.home_system == "Jita"

    def test_preferences_serialization(self):
        """Test preferences can be serialized to JSON."""
        prefs = CharacterPreferences(
            character_id=12345,
            character_name="Test Pilot",
        )

        data = prefs.model_dump(mode="json")
        assert data["character_id"] == 12345
        assert "routing" in data
        assert "alerts" in data
        assert "ui" in data

    def test_preferences_update_model(self):
        """Test partial update model."""
        update = CharacterPreferencesUpdate(
            routing=RoutingPreferences(default_profile="shortest"),
        )

        assert update.routing is not None
        assert update.routing.default_profile == "shortest"
        assert update.alerts is None
        assert update.ui is None


# =============================================================================
# Memory Store Tests
# =============================================================================


class TestMemoryPreferencesStore:
    """Tests for in-memory preferences storage."""

    @pytest.fixture
    def store(self):
        """Create a fresh memory store."""
        return MemoryPreferencesStore()

    @pytest.mark.asyncio
    async def test_save_and_get_preferences(self, store):
        """Test saving and retrieving preferences."""
        prefs = CharacterPreferences(
            character_id=12345,
            character_name="Test Pilot",
        )

        await store.save_preferences(prefs)
        retrieved = await store.get_preferences(12345)

        assert retrieved is not None
        assert retrieved.character_id == 12345
        assert retrieved.character_name == "Test Pilot"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, store):
        """Test getting non-existent preferences returns None."""
        result = await store.get_preferences(99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create(self, store):
        """Test get_or_create creates defaults if not exists."""
        prefs = await store.get_or_create(12345, "Test Pilot")

        assert prefs.character_id == 12345
        assert prefs.character_name == "Test Pilot"
        assert prefs.routing.default_profile == "safer"

        # Second call should return same
        prefs2 = await store.get_or_create(12345, "Test Pilot")
        assert prefs2.character_id == prefs.character_id

    @pytest.mark.asyncio
    async def test_update_preferences(self, store):
        """Test updating preferences."""
        # Create initial
        prefs = await store.get_or_create(12345, "Test Pilot")
        assert prefs.routing.default_profile == "safer"

        # Update
        update = CharacterPreferencesUpdate(
            routing=RoutingPreferences(default_profile="paranoid"),
        )
        updated = await store.update_preferences(12345, update)

        assert updated is not None
        assert updated.routing.default_profile == "paranoid"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, store):
        """Test updating non-existent preferences returns None."""
        update = CharacterPreferencesUpdate(
            routing=RoutingPreferences(default_profile="paranoid"),
        )
        result = await store.update_preferences(99999, update)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_preferences(self, store):
        """Test deleting preferences."""
        await store.get_or_create(12345, "Test Pilot")

        deleted = await store.delete_preferences(12345)
        assert deleted is True

        result = await store.get_preferences(12345)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, store):
        """Test deleting non-existent returns False."""
        deleted = await store.delete_preferences(99999)
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_all(self, store):
        """Test listing all preferences."""
        await store.get_or_create(12345, "Pilot One")
        await store.get_or_create(67890, "Pilot Two")

        all_prefs = await store.list_all()
        assert len(all_prefs) == 2

        ids = {p.character_id for p in all_prefs}
        assert 12345 in ids
        assert 67890 in ids


# =============================================================================
# Active Character Manager Tests
# =============================================================================


class TestActiveCharacterManager:
    """Tests for active character session management."""

    @pytest.fixture
    def manager(self):
        """Create a fresh manager."""
        return ActiveCharacterManager()

    def test_set_and_get_active(self, manager):
        """Test setting and getting active character."""
        manager.set_active("session-1", 12345)

        active = manager.get_active("session-1")
        assert active == 12345

    def test_get_nonexistent_session_returns_none(self, manager):
        """Test getting non-existent session returns None."""
        result = manager.get_active("nonexistent")
        assert result is None

    def test_multiple_sessions(self, manager):
        """Test multiple sessions can have different active characters."""
        manager.set_active("session-1", 12345)
        manager.set_active("session-2", 67890)

        assert manager.get_active("session-1") == 12345
        assert manager.get_active("session-2") == 67890

    def test_switch_active_character(self, manager):
        """Test switching active character in a session."""
        manager.set_active("session-1", 12345)
        manager.set_active("session-1", 67890)

        assert manager.get_active("session-1") == 67890

    def test_clear_active(self, manager):
        """Test clearing active character."""
        manager.set_active("session-1", 12345)
        manager.clear_active("session-1")

        assert manager.get_active("session-1") is None

    def test_get_stats(self, manager):
        """Test getting session statistics."""
        manager.set_active("session-1", 12345)
        manager.set_active("session-2", 67890)
        manager.set_active("session-3", 12345)  # Same char as session-1

        stats = manager.get_stats()
        assert stats["active_sessions"] == 3
        assert stats["unique_characters"] == 2


# =============================================================================
# Routing Preferences Tests
# =============================================================================


class TestRoutingPreferences:
    """Tests for routing preferences."""

    def test_default_values(self):
        """Test default routing preferences."""
        prefs = RoutingPreferences()

        assert prefs.default_profile == "safer"
        assert prefs.avoid_systems == []
        assert prefs.avoid_lists == []
        assert prefs.use_bridges is False
        assert prefs.use_thera is False
        assert prefs.use_pochven is False
        assert prefs.use_wormholes is False

    def test_custom_values(self):
        """Test custom routing preferences."""
        prefs = RoutingPreferences(
            default_profile="paranoid",
            avoid_systems=["Tama", "Rancer", "Amamake"],
            avoid_lists=["gatecamps"],
            use_bridges=True,
            use_thera=True,
        )

        assert prefs.default_profile == "paranoid"
        assert len(prefs.avoid_systems) == 3
        assert "Tama" in prefs.avoid_systems
        assert prefs.use_bridges is True


# =============================================================================
# Alert Preferences Tests
# =============================================================================


class TestAlertPreferences:
    """Tests for alert preferences."""

    def test_default_values(self):
        """Test default alert preferences."""
        prefs = AlertPreferences()

        assert prefs.enabled is True
        assert prefs.min_value_isk == 0
        assert prefs.include_pods is True
        assert prefs.watch_systems == []
        assert prefs.discord_webhook is None

    def test_webhook_configuration(self):
        """Test webhook configuration."""
        prefs = AlertPreferences(
            discord_webhook="https://discord.com/api/webhooks/...",
            slack_webhook="https://hooks.slack.com/...",
        )

        assert prefs.discord_webhook is not None
        assert prefs.slack_webhook is not None


# =============================================================================
# UI Preferences Tests
# =============================================================================


class TestUIPreferences:
    """Tests for UI preferences."""

    def test_default_values(self):
        """Test default UI preferences."""
        prefs = UIPreferences()

        assert prefs.theme == "dark"
        assert prefs.default_map_zoom == 1.0
        assert prefs.show_risk_overlay is True
        assert prefs.show_kills_overlay is True
        assert prefs.compact_mode is False

    def test_light_theme(self):
        """Test light theme configuration."""
        prefs = UIPreferences(theme="light")
        assert prefs.theme == "light"


# =============================================================================
# Integration Tests
# =============================================================================


class TestMultiCharacterIntegration:
    """Integration tests for multi-character support."""

    @pytest.fixture
    def store(self):
        """Create a fresh memory store."""
        return MemoryPreferencesStore()

    @pytest.fixture
    def manager(self):
        """Create a fresh active manager."""
        return ActiveCharacterManager()

    @pytest.mark.asyncio
    async def test_full_character_workflow(self, store, manager):
        """Test a complete multi-character workflow."""
        # User logs in with first character
        prefs1 = await store.get_or_create(12345, "Main Character")
        manager.set_active("session-abc", 12345)

        # Customize preferences
        prefs1.routing.default_profile = "paranoid"
        prefs1.routing.avoid_systems.append("Tama")
        prefs1.home_system = "Jita"
        await store.save_preferences(prefs1)

        # User logs in with second character
        prefs2 = await store.get_or_create(67890, "Alt Character")

        # Set different preferences for alt
        prefs2.routing.default_profile = "shortest"
        prefs2.home_system = "Amarr"
        await store.save_preferences(prefs2)

        # Switch to alt
        manager.set_active("session-abc", 67890)

        # Verify switch
        assert manager.get_active("session-abc") == 67890

        # Get preferences for active character
        active_id = manager.get_active("session-abc")
        active_prefs = await store.get_preferences(active_id)

        assert active_prefs.character_name == "Alt Character"
        assert active_prefs.home_system == "Amarr"
        assert active_prefs.routing.default_profile == "shortest"

    @pytest.mark.asyncio
    async def test_character_specific_avoid_lists(self, store):
        """Test that avoid lists are character-specific."""
        # Main has avoid list
        prefs1 = await store.get_or_create(12345, "Hauler")
        prefs1.routing.avoid_systems = ["Tama", "Rancer", "Amamake"]
        await store.save_preferences(prefs1)

        # PvP alt has no avoid list
        await store.get_or_create(67890, "PvP Alt")
        # Default empty avoid list

        # Verify they're separate
        p1 = await store.get_preferences(12345)
        p2 = await store.get_preferences(67890)

        assert len(p1.routing.avoid_systems) == 3
        assert len(p2.routing.avoid_systems) == 0
