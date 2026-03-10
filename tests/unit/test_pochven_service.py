"""Unit tests for Pochven filament routing service."""

from backend.app.models.pochven import PochvenConnection
from backend.app.services.pochven import (
    POCHVEN_SYSTEMS,
    _state,
    get_active_pochven,
    get_pochven_systems,
    is_pochven_enabled,
    toggle_pochven,
)


class TestPochvenToggle:
    """Tests for Pochven enable/disable."""

    def setup_method(self):
        _state["enabled"] = True

    def test_default_enabled(self):
        assert is_pochven_enabled() is True

    def test_toggle_off(self):
        result = toggle_pochven(False)
        assert result is False
        assert is_pochven_enabled() is False

    def test_toggle_on(self):
        toggle_pochven(False)
        result = toggle_pochven(True)
        assert result is True
        assert is_pochven_enabled() is True


class TestGetPochvenSystems:
    """Tests for Pochven system listing."""

    def test_returns_list(self):
        systems = get_pochven_systems()
        assert isinstance(systems, list)
        assert len(systems) > 0

    def test_all_systems_valid(self):
        """All returned systems should be from POCHVEN_SYSTEMS."""
        systems = get_pochven_systems()
        for s in systems:
            assert s in POCHVEN_SYSTEMS


class TestGetActivePochven:
    """Tests for active Pochven connection loading."""

    def test_returns_connections(self):
        connections = get_active_pochven()
        assert isinstance(connections, list)
        assert len(connections) > 0
        assert all(isinstance(c, PochvenConnection) for c in connections)

    def test_connections_have_valid_types(self):
        connections = get_active_pochven()
        valid_types = {"internal", "cross_krai"}
        for c in connections:
            assert c.connection_type in valid_types

    def test_internal_connections_exist(self):
        connections = get_active_pochven()
        internal = [c for c in connections if c.connection_type == "internal"]
        assert len(internal) > 0

    def test_cross_krai_connections_exist(self):
        connections = get_active_pochven()
        cross = [c for c in connections if c.connection_type == "cross_krai"]
        assert len(cross) > 0

    def test_all_connections_bidirectional(self):
        connections = get_active_pochven()
        for c in connections:
            assert c.bidirectional is True

    def test_filters_unknown_systems(self):
        """Connections with systems not in universe should be excluded."""
        connections = get_active_pochven()
        from backend.app.services.data_loader import load_universe

        universe = load_universe()
        for c in connections:
            assert c.from_system in universe.systems
            assert c.to_system in universe.systems
