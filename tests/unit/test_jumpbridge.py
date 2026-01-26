"""Tests for jump bridge service."""

from unittest.mock import MagicMock, patch

import pytest

from backend.app.models.jumpbridge import (
    JumpBridge,
    JumpBridgeConfig,
    JumpBridgeNetwork,
)
from backend.app.services.jumpbridge import (
    bulk_add_bridges,
    bulk_remove_bridges,
    clear_bridge_cache,
    discover_bridges_from_structures,
    get_bridge_route_info,
    load_bridge_config,
    parse_bridge_text,
    save_bridge_config,
    validate_bridge,
    validate_network,
)


@pytest.fixture
def mock_universe():
    """Create a mock universe with known systems."""
    mock = MagicMock()

    # Create systems with proper attributes for validation tests
    def make_system(name, security, category, region_id, region_name):
        sys = MagicMock()
        sys.name = name
        sys.security = security
        sys.category = category
        sys.region_id = region_id
        sys.region_name = region_name
        return sys

    mock.systems = {
        # Highsec systems
        "Jita": make_system("Jita", 0.9, "highsec", 10000002, "The Forge"),
        "Amarr": make_system("Amarr", 1.0, "highsec", 10000043, "Domain"),
        "Dodixie": make_system("Dodixie", 0.9, "highsec", 10000032, "Sinq Laison"),
        "Perimeter": make_system("Perimeter", 0.9, "highsec", 10000002, "The Forge"),
        # Nullsec systems
        "HED-GP": make_system("HED-GP", -0.4, "nullsec", 10000014, "Catch"),
        "1DQ1-A": make_system("1DQ1-A", -0.5, "nullsec", 10000060, "Delve"),
        "8QT-H4": make_system("8QT-H4", -0.3, "nullsec", 10000060, "Delve"),
        "Niarja": make_system("Niarja", -1.0, "nullsec", 10000065, "Triglavian"),
        # Lowsec systems
        "Amamake": make_system("Amamake", 0.4, "lowsec", 10000042, "Metropolis"),
        "Tama": make_system("Tama", 0.3, "lowsec", 10000016, "Lonetrek"),
        # Wormhole system
        "J123456": make_system("J123456", -1.0, "wh", 11000001, "A-R00001"),
    }
    return mock


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    return tmp_path


class TestParseBridgeText:
    """Tests for parse_bridge_text function."""

    def test_parse_arrow_format(self, mock_universe):
        """Should parse 'System1 <-> System2' format."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("Jita <-> Amarr")

        assert len(bridges) == 1
        assert len(errors) == 0
        assert bridges[0].from_system == "Jita"
        assert bridges[0].to_system == "Amarr"

    def test_parse_double_arrow_format(self, mock_universe):
        """Should parse 'System1 --> System2' format."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("Jita --> Amarr")

        assert len(bridges) == 1
        assert bridges[0].from_system == "Jita"
        assert bridges[0].to_system == "Amarr"

    def test_parse_angle_bracket_format(self, mock_universe):
        """Should parse 'System1 <> System2' format."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("Jita <> Amarr")

        assert len(bridges) == 1

    def test_parse_dash_format(self, mock_universe):
        """Should parse 'System1 - System2' format."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("Jita - Amarr")

        assert len(bridges) == 1

    def test_parse_multiple_bridges(self, mock_universe):
        """Should parse multiple bridges."""
        text = """
        Jita <-> Amarr
        Dodixie <-> HED-GP
        1DQ1-A <-> 8QT-H4
        """
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text(text)

        assert len(bridges) == 3
        assert len(errors) == 0

    def test_skip_comments(self, mock_universe):
        """Should skip lines starting with #."""
        text = """
        # This is a comment
        Jita <-> Amarr
        # Another comment
        """
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text(text)

        assert len(bridges) == 1

    def test_skip_empty_lines(self, mock_universe):
        """Should skip empty lines."""
        text = """
        Jita <-> Amarr

        Dodixie <-> HED-GP

        """
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text(text)

        assert len(bridges) == 2

    def test_unknown_system_error(self, mock_universe):
        """Should report error for unknown systems."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("Jita <-> UnknownSystem")

        assert len(bridges) == 0
        assert len(errors) == 1
        assert "Unknown system" in errors[0]
        assert "UnknownSystem" in errors[0]

    def test_unknown_first_system_error(self, mock_universe):
        """Should report error for unknown first system."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("FakeSystem <-> Jita")

        assert len(bridges) == 0
        assert len(errors) == 1
        assert "FakeSystem" in errors[0]

    def test_unparseable_line_error(self, mock_universe):
        """Should report error for unparseable lines."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("this is not a valid format")

        assert len(bridges) == 0
        assert len(errors) == 1
        assert "Could not parse" in errors[0]

    def test_deduplicate_bridges(self, mock_universe):
        """Should skip duplicate bridges."""
        text = """
        Jita <-> Amarr
        Jita <-> Amarr
        Amarr <-> Jita
        """
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text(text)

        # All three are duplicates (same connection), only first should be kept
        assert len(bridges) == 1

    def test_whitespace_handling(self, mock_universe):
        """Should handle extra whitespace."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, errors = parse_bridge_text("  Jita   <->   Amarr  ")

        assert len(bridges) == 1
        assert bridges[0].from_system == "Jita"
        assert bridges[0].to_system == "Amarr"

    def test_returns_jump_bridge_objects(self, mock_universe):
        """Should return JumpBridge objects."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, _ = parse_bridge_text("Jita <-> Amarr")

        assert isinstance(bridges[0], JumpBridge)

    def test_bridge_has_none_structure_id(self, mock_universe):
        """Parsed bridges should have None structure_id."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, _ = parse_bridge_text("Jita <-> Amarr")

        assert bridges[0].structure_id is None

    def test_bridge_has_none_owner(self, mock_universe):
        """Parsed bridges should have None owner."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            bridges, _ = parse_bridge_text("Jita <-> Amarr")

        assert bridges[0].owner is None


class TestJumpBridgeConfig:
    """Tests for JumpBridgeConfig model."""

    def test_empty_config(self):
        """Should create empty config."""
        config = JumpBridgeConfig(networks=[])
        assert config.networks == []

    def test_get_active_bridges_all_enabled(self):
        """Should return all bridges when all networks enabled."""
        bridge1 = JumpBridge(from_system="A", to_system="B")
        bridge2 = JumpBridge(from_system="C", to_system="D")

        network1 = JumpBridgeNetwork(name="Net1", bridges=[bridge1], enabled=True)
        network2 = JumpBridgeNetwork(name="Net2", bridges=[bridge2], enabled=True)

        config = JumpBridgeConfig(networks=[network1, network2])
        active = config.get_active_bridges()

        assert len(active) == 2

    def test_get_active_bridges_some_disabled(self):
        """Should only return bridges from enabled networks."""
        bridge1 = JumpBridge(from_system="A", to_system="B")
        bridge2 = JumpBridge(from_system="C", to_system="D")

        network1 = JumpBridgeNetwork(name="Net1", bridges=[bridge1], enabled=True)
        network2 = JumpBridgeNetwork(name="Net2", bridges=[bridge2], enabled=False)

        config = JumpBridgeConfig(networks=[network1, network2])
        active = config.get_active_bridges()

        assert len(active) == 1
        assert active[0].from_system == "A"

    def test_get_active_bridges_all_disabled(self):
        """Should return empty list when all networks disabled."""
        bridge1 = JumpBridge(from_system="A", to_system="B")
        network1 = JumpBridgeNetwork(name="Net1", bridges=[bridge1], enabled=False)

        config = JumpBridgeConfig(networks=[network1])
        active = config.get_active_bridges()

        assert len(active) == 0


class TestJumpBridgeNetwork:
    """Tests for JumpBridgeNetwork model."""

    def test_default_enabled(self):
        """Network should be enabled by default."""
        network = JumpBridgeNetwork(name="Test", bridges=[])
        assert network.enabled is True

    def test_empty_bridges_list(self):
        """Network should have empty bridges by default."""
        network = JumpBridgeNetwork(name="Test")
        assert network.bridges == []


class TestJumpBridge:
    """Tests for JumpBridge model."""

    def test_required_fields(self):
        """Should require from_system and to_system."""
        bridge = JumpBridge(from_system="A", to_system="B")
        assert bridge.from_system == "A"
        assert bridge.to_system == "B"

    def test_optional_fields_default_none(self):
        """Optional fields should default to None."""
        bridge = JumpBridge(from_system="A", to_system="B")
        assert bridge.structure_id is None
        assert bridge.owner is None

    def test_with_all_fields(self):
        """Should accept all fields."""
        bridge = JumpBridge(
            from_system="A", to_system="B", structure_id=123456789, owner="Test Alliance"
        )
        assert bridge.structure_id == 123456789
        assert bridge.owner == "Test Alliance"


class TestLoadSaveBridgeConfig:
    """Tests for load_bridge_config and save_bridge_config."""

    def test_load_creates_empty_config_if_no_file(self, tmp_path):
        """Should create empty config if file doesn't exist."""
        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path",
            return_value=tmp_path / "bridges.json",
        ):
            config = load_bridge_config()

        assert config.networks == []

    def test_save_and_load_roundtrip(self, tmp_path):
        """Should be able to save and load config."""
        config_path = tmp_path / "bridges.json"
        clear_bridge_cache()

        bridge = JumpBridge(from_system="Jita", to_system="Amarr")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            loaded = load_bridge_config()

        assert len(loaded.networks) == 1
        assert loaded.networks[0].name == "TestNet"
        assert len(loaded.networks[0].bridges) == 1

    def test_load_caches_config(self, tmp_path):
        """Should cache loaded config."""
        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')
        clear_bridge_cache()

        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            config1 = load_bridge_config()
            config2 = load_bridge_config()

        assert config1 is config2

    def test_clear_cache_forces_reload(self, tmp_path):
        """Clearing cache should force reload on next load."""
        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            clear_bridge_cache()
            config1 = load_bridge_config()
            clear_bridge_cache()
            config2 = load_bridge_config()

        # After clearing, should be different objects (reloaded)
        assert config1 is not config2


class TestImportBridges:
    """Tests for import_bridges function."""

    def test_import_creates_network(self, mock_universe, tmp_path):
        """Should create a new network on import."""
        from backend.app.services.jumpbridge import import_bridges

        config_path = tmp_path / "bridges.json"
        clear_bridge_cache()

        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            result = import_bridges("TestNet", "Jita <-> Amarr")

        assert result.network_name == "TestNet"
        assert result.bridges_imported == 1
        assert len(result.errors) == 0

    def test_import_multiple_bridges(self, mock_universe, tmp_path):
        """Should import multiple bridges."""
        from backend.app.services.jumpbridge import import_bridges

        config_path = tmp_path / "bridges.json"
        clear_bridge_cache()

        text = """
        Jita <-> Amarr
        Dodixie <-> HED-GP
        """

        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            result = import_bridges("TestNet", text)

        assert result.bridges_imported == 2

    def test_import_replace_mode(self, mock_universe, tmp_path):
        """Replace mode should replace existing network."""
        from backend.app.services.jumpbridge import import_bridges

        config_path = tmp_path / "bridges.json"
        clear_bridge_cache()

        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            # First import
            import_bridges("TestNet", "Jita <-> Amarr")
            clear_bridge_cache()
            # Second import with replace
            result = import_bridges("TestNet", "Dodixie <-> HED-GP", replace=True)

        assert result.bridges_imported == 1

    def test_import_merge_mode(self, mock_universe, tmp_path):
        """Merge mode should add new bridges to existing network."""
        from backend.app.services.jumpbridge import import_bridges

        config_path = tmp_path / "bridges.json"
        clear_bridge_cache()

        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            # First import
            import_bridges("TestNet", "Jita <-> Amarr")
            clear_bridge_cache()
            # Second import with merge (replace=False)
            import_bridges("TestNet", "Dodixie <-> HED-GP", replace=False)

            # Check both bridges exist
            clear_bridge_cache()
            config = load_bridge_config()

        network = next(n for n in config.networks if n.name == "TestNet")
        assert len(network.bridges) == 2

    def test_import_returns_errors(self, mock_universe, tmp_path):
        """Should return errors for invalid systems."""
        from backend.app.services.jumpbridge import import_bridges

        config_path = tmp_path / "bridges.json"
        clear_bridge_cache()

        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            result = import_bridges("TestNet", "FakeSystem <-> Amarr")

        assert result.bridges_imported == 0
        assert len(result.errors) > 0


class TestToggleNetwork:
    """Tests for toggle_network function."""

    def test_toggle_disable_network(self, tmp_path):
        """Should disable a network."""
        from backend.app.services.jumpbridge import toggle_network

        config_path = tmp_path / "bridges.json"

        bridge = JumpBridge(from_system="A", to_system="B")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = toggle_network("TestNet", enabled=False)

            # Check it's disabled
            clear_bridge_cache()
            loaded = load_bridge_config()

        assert result is True
        assert loaded.networks[0].enabled is False

    def test_toggle_enable_network(self, tmp_path):
        """Should enable a network."""
        from backend.app.services.jumpbridge import toggle_network

        config_path = tmp_path / "bridges.json"

        bridge = JumpBridge(from_system="A", to_system="B")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=False)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = toggle_network("TestNet", enabled=True)

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert result is True
        assert loaded.networks[0].enabled is True

    def test_toggle_nonexistent_network(self, tmp_path):
        """Should return False for nonexistent network."""
        from backend.app.services.jumpbridge import toggle_network

        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            result = toggle_network("NonExistent", enabled=False)

        assert result is False


class TestDeleteNetwork:
    """Tests for delete_network function."""

    def test_delete_existing_network(self, tmp_path):
        """Should delete an existing network."""
        from backend.app.services.jumpbridge import delete_network

        config_path = tmp_path / "bridges.json"

        bridge = JumpBridge(from_system="A", to_system="B")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = delete_network("TestNet")

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert result is True
        assert len(loaded.networks) == 0

    def test_delete_nonexistent_network(self, tmp_path):
        """Should return False for nonexistent network."""
        from backend.app.services.jumpbridge import delete_network

        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            result = delete_network("NonExistent")

        assert result is False

    def test_delete_preserves_other_networks(self, tmp_path):
        """Should preserve other networks when deleting one."""
        from backend.app.services.jumpbridge import delete_network

        config_path = tmp_path / "bridges.json"

        network1 = JumpBridgeNetwork(name="Net1", bridges=[], enabled=True)
        network2 = JumpBridgeNetwork(name="Net2", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network1, network2])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            delete_network("Net1")

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert len(loaded.networks) == 1
        assert loaded.networks[0].name == "Net2"


class TestGetActiveBridges:
    """Tests for get_active_bridges function."""

    def test_get_active_bridges(self, tmp_path):
        """Should return bridges from enabled networks."""
        from backend.app.services.jumpbridge import get_active_bridges

        config_path = tmp_path / "bridges.json"

        bridge1 = JumpBridge(from_system="A", to_system="B")
        bridge2 = JumpBridge(from_system="C", to_system="D")
        network1 = JumpBridgeNetwork(name="Net1", bridges=[bridge1], enabled=True)
        network2 = JumpBridgeNetwork(name="Net2", bridges=[bridge2], enabled=False)
        config = JumpBridgeConfig(networks=[network1, network2])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            active = get_active_bridges()

        assert len(active) == 1
        assert active[0].from_system == "A"

    def test_get_active_bridges_empty(self, tmp_path):
        """Should return empty list when no networks."""
        from backend.app.services.jumpbridge import get_active_bridges

        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            active = get_active_bridges()

        assert active == []


class TestAddBridge:
    """Tests for add_bridge function."""

    def test_add_bridge_success(self, mock_universe, tmp_path):
        """Should add a bridge to existing network."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, message = add_bridge("TestNet", "Jita", "Amarr")

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert success is True
        assert "successfully" in message.lower()
        assert len(loaded.networks[0].bridges) == 1
        assert loaded.networks[0].bridges[0].from_system == "Jita"
        assert loaded.networks[0].bridges[0].to_system == "Amarr"

    def test_add_bridge_with_optional_fields(self, mock_universe, tmp_path):
        """Should add bridge with structure_id and owner."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, _ = add_bridge(
                "TestNet", "Jita", "Amarr", structure_id=123456, owner="Test Alliance"
            )

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert success is True
        assert loaded.networks[0].bridges[0].structure_id == 123456
        assert loaded.networks[0].bridges[0].owner == "Test Alliance"

    def test_add_bridge_unknown_from_system(self, mock_universe, tmp_path):
        """Should fail for unknown origin system."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, message = add_bridge("TestNet", "FakeSystem", "Amarr")

        assert success is False
        assert "Unknown system" in message
        assert "FakeSystem" in message

    def test_add_bridge_unknown_to_system(self, mock_universe, tmp_path):
        """Should fail for unknown destination system."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, message = add_bridge("TestNet", "Jita", "FakeSystem")

        assert success is False
        assert "Unknown system" in message
        assert "FakeSystem" in message

    def test_add_bridge_same_system(self, mock_universe, tmp_path):
        """Should fail when origin and destination are the same."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, message = add_bridge("TestNet", "Jita", "Jita")

        assert success is False
        assert "different" in message.lower()

    def test_add_bridge_network_not_found(self, mock_universe, tmp_path):
        """Should fail for nonexistent network."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            success, message = add_bridge("NonExistent", "Jita", "Amarr")

        assert success is False
        assert "not found" in message.lower()
        assert "NonExistent" in message

    def test_add_bridge_duplicate(self, mock_universe, tmp_path):
        """Should fail when bridge already exists."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="Jita", to_system="Amarr")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, message = add_bridge("TestNet", "Jita", "Amarr")

        assert success is False
        assert "already exists" in message.lower()

    def test_add_bridge_duplicate_reverse_order(self, mock_universe, tmp_path):
        """Should detect duplicate when systems are in reverse order."""
        from backend.app.services.jumpbridge import add_bridge

        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="Jita", to_system="Amarr")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            # Try to add reverse direction
            success, message = add_bridge("TestNet", "Amarr", "Jita")

        assert success is False
        assert "already exists" in message.lower()


class TestRemoveBridge:
    """Tests for remove_bridge function."""

    def test_remove_bridge_success(self, tmp_path):
        """Should remove an existing bridge."""
        from backend.app.services.jumpbridge import remove_bridge

        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="Jita", to_system="Amarr")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, message = remove_bridge("TestNet", "Jita", "Amarr")

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert success is True
        assert "successfully" in message.lower()
        assert len(loaded.networks[0].bridges) == 0

    def test_remove_bridge_reverse_order(self, tmp_path):
        """Should remove bridge when systems are in reverse order."""
        from backend.app.services.jumpbridge import remove_bridge

        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="Jita", to_system="Amarr")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            # Remove with reverse system order
            success, message = remove_bridge("TestNet", "Amarr", "Jita")

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert success is True
        assert len(loaded.networks[0].bridges) == 0

    def test_remove_bridge_network_not_found(self, tmp_path):
        """Should fail for nonexistent network."""
        from backend.app.services.jumpbridge import remove_bridge

        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            success, message = remove_bridge("NonExistent", "Jita", "Amarr")

        assert success is False
        assert "not found" in message.lower()
        assert "NonExistent" in message

    def test_remove_bridge_not_found(self, tmp_path):
        """Should fail when bridge doesn't exist."""
        from backend.app.services.jumpbridge import remove_bridge

        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            success, message = remove_bridge("TestNet", "Jita", "Amarr")

        assert success is False
        assert "not found" in message.lower()

    def test_remove_bridge_preserves_others(self, tmp_path):
        """Should preserve other bridges in network."""
        from backend.app.services.jumpbridge import remove_bridge

        config_path = tmp_path / "bridges.json"
        bridge1 = JumpBridge(from_system="Jita", to_system="Amarr")
        bridge2 = JumpBridge(from_system="Dodixie", to_system="Perimeter")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge1, bridge2], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            remove_bridge("TestNet", "Jita", "Amarr")

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert len(loaded.networks[0].bridges) == 1
        assert loaded.networks[0].bridges[0].from_system == "Dodixie"


class TestGetBridgeStats:
    """Tests for get_bridge_stats function."""

    def test_stats_empty_config(self, tmp_path):
        """Should return zeros for empty config."""
        from backend.app.services.jumpbridge import get_bridge_stats

        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            stats = get_bridge_stats()

        assert stats.total_networks == 0
        assert stats.active_networks == 0
        assert stats.total_bridges == 0
        assert stats.active_bridges == 0
        assert stats.systems_connected == 0
        assert stats.bridges_by_network == {}

    def test_stats_single_enabled_network(self, tmp_path):
        """Should count enabled network correctly."""
        from backend.app.services.jumpbridge import get_bridge_stats

        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="Jita", to_system="Amarr")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            stats = get_bridge_stats()

        assert stats.total_networks == 1
        assert stats.active_networks == 1
        assert stats.total_bridges == 1
        assert stats.active_bridges == 1
        assert stats.systems_connected == 2
        assert stats.bridges_by_network == {"TestNet": 1}

    def test_stats_disabled_network(self, tmp_path):
        """Should count disabled network but not active bridges."""
        from backend.app.services.jumpbridge import get_bridge_stats

        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="Jita", to_system="Amarr")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=False)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            stats = get_bridge_stats()

        assert stats.total_networks == 1
        assert stats.active_networks == 0
        assert stats.total_bridges == 1
        assert stats.active_bridges == 0
        assert stats.systems_connected == 0  # Only counts active bridges

    def test_stats_multiple_networks(self, tmp_path):
        """Should aggregate stats across networks."""
        from backend.app.services.jumpbridge import get_bridge_stats

        config_path = tmp_path / "bridges.json"
        bridge1 = JumpBridge(from_system="Jita", to_system="Amarr")
        bridge2 = JumpBridge(from_system="Dodixie", to_system="Perimeter")
        bridge3 = JumpBridge(from_system="A", to_system="B")
        network1 = JumpBridgeNetwork(name="Net1", bridges=[bridge1, bridge2], enabled=True)
        network2 = JumpBridgeNetwork(name="Net2", bridges=[bridge3], enabled=True)
        config = JumpBridgeConfig(networks=[network1, network2])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            stats = get_bridge_stats()

        assert stats.total_networks == 2
        assert stats.active_networks == 2
        assert stats.total_bridges == 3
        assert stats.active_bridges == 3
        assert stats.systems_connected == 6  # Jita, Amarr, Dodixie, Perimeter, A, B
        assert stats.bridges_by_network == {"Net1": 2, "Net2": 1}

    def test_stats_shared_systems_counted_once(self, tmp_path):
        """Systems connected multiple times should be counted once."""
        from backend.app.services.jumpbridge import get_bridge_stats

        config_path = tmp_path / "bridges.json"
        bridge1 = JumpBridge(from_system="Jita", to_system="Amarr")
        bridge2 = JumpBridge(from_system="Jita", to_system="Dodixie")  # Jita shared
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge1, bridge2], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            stats = get_bridge_stats()

        assert stats.systems_connected == 3  # Jita, Amarr, Dodixie (Jita counted once)

    def test_stats_mixed_enabled_disabled(self, tmp_path):
        """Should correctly handle mix of enabled/disabled networks."""
        from backend.app.services.jumpbridge import get_bridge_stats

        config_path = tmp_path / "bridges.json"
        bridge1 = JumpBridge(from_system="Jita", to_system="Amarr")
        bridge2 = JumpBridge(from_system="Dodixie", to_system="Perimeter")
        network1 = JumpBridgeNetwork(name="EnabledNet", bridges=[bridge1], enabled=True)
        network2 = JumpBridgeNetwork(name="DisabledNet", bridges=[bridge2], enabled=False)
        config = JumpBridgeConfig(networks=[network1, network2])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            stats = get_bridge_stats()

        assert stats.total_networks == 2
        assert stats.active_networks == 1
        assert stats.total_bridges == 2
        assert stats.active_bridges == 1
        assert stats.systems_connected == 2  # Only from enabled network
        assert stats.bridges_by_network == {"EnabledNet": 1, "DisabledNet": 1}


class TestValidateBridge:
    """Tests for validate_bridge function."""

    def test_valid_nullsec_bridge(self, mock_universe):
        """Should return no errors for valid nullsec bridge."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("1DQ1-A", "8QT-H4")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_valid_lowsec_bridge(self, mock_universe):
        """Should return no errors for valid lowsec bridge."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("Amamake", "Tama")

        errors = [i for i in issues if i.severity == "error"]
        # Cross-region is a warning, not error
        assert len(errors) == 0

    def test_highsec_from_system_error(self, mock_universe):
        """Should return error for highsec origin system."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("Jita", "1DQ1-A")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 1
        assert "highsec" in errors[0].issue.lower()
        assert "Jita" in errors[0].issue

    def test_highsec_to_system_error(self, mock_universe):
        """Should return error for highsec destination system."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("1DQ1-A", "Amarr")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 1
        assert "highsec" in errors[0].issue.lower()
        assert "Amarr" in errors[0].issue

    def test_both_highsec_error(self, mock_universe):
        """Should return errors for both highsec systems."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("Jita", "Amarr")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 2

    def test_wormhole_system_error(self, mock_universe):
        """Should return error for wormhole system."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("J123456", "1DQ1-A")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 1
        assert "wormhole" in errors[0].issue.lower()

    def test_unknown_from_system_error(self, mock_universe):
        """Should return error for unknown origin system."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("FakeSystem", "1DQ1-A")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 1
        assert "Unknown system" in errors[0].issue

    def test_unknown_to_system_error(self, mock_universe):
        """Should return error for unknown destination system."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("1DQ1-A", "FakeSystem")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 1
        assert "Unknown system" in errors[0].issue

    def test_same_system_error(self, mock_universe):
        """Should return error when origin and destination are the same."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("1DQ1-A", "1DQ1-A")

        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 1
        assert "same system" in errors[0].issue.lower()

    def test_cross_region_warning(self, mock_universe):
        """Should return warning for cross-region bridge."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("1DQ1-A", "HED-GP")  # Delve to Catch

        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) == 1
        assert "Cross-region" in warnings[0].issue

    def test_same_region_no_warning(self, mock_universe):
        """Should not warn for same-region bridge."""
        with patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe):
            issues = validate_bridge("1DQ1-A", "8QT-H4")  # Both in Delve

        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) == 0


class TestValidateNetwork:
    """Tests for validate_network function."""

    def test_validate_valid_network(self, mock_universe, tmp_path):
        """Should return all bridges valid for valid network."""
        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="1DQ1-A", to_system="8QT-H4")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = validate_network("TestNet")

        assert result.total_bridges == 1
        assert result.valid_bridges == 1
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) == 0

    def test_validate_network_with_invalid_bridges(self, mock_universe, tmp_path):
        """Should return issues for invalid bridges."""
        config_path = tmp_path / "bridges.json"
        bridge1 = JumpBridge(from_system="1DQ1-A", to_system="8QT-H4")  # Valid
        bridge2 = JumpBridge(from_system="Jita", to_system="Amarr")  # Invalid - highsec
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge1, bridge2], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = validate_network("TestNet")

        assert result.total_bridges == 2
        assert result.valid_bridges == 1
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) == 2  # Both Jita and Amarr are highsec

    def test_validate_network_not_found(self, tmp_path):
        """Should return error for nonexistent network."""
        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            result = validate_network("NonExistent")

        assert result.total_bridges == 0
        assert result.valid_bridges == 0
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) == 1
        assert "not found" in errors[0].issue.lower()


class TestBulkAddBridges:
    """Tests for bulk_add_bridges function."""

    def test_bulk_add_all_success(self, mock_universe, tmp_path):
        """Should add all valid bridges."""
        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = bulk_add_bridges(
                "TestNet",
                [
                    ("1DQ1-A", "8QT-H4", None, None),
                    ("Amamake", "Tama", 123, "Test Corp"),
                ],
            )

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert result.succeeded == 2
        assert result.failed == 0
        assert len(result.errors) == 0
        assert len(loaded.networks[0].bridges) == 2

    def test_bulk_add_partial_failure(self, mock_universe, tmp_path):
        """Should report failures for invalid bridges."""
        config_path = tmp_path / "bridges.json"
        network = JumpBridgeNetwork(name="TestNet", bridges=[], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = bulk_add_bridges(
                "TestNet",
                [
                    ("1DQ1-A", "8QT-H4", None, None),  # Valid
                    ("FakeSystem", "1DQ1-A", None, None),  # Invalid
                ],
            )

        assert result.succeeded == 1
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "FakeSystem" in result.errors[0]

    def test_bulk_add_network_not_found(self, mock_universe, tmp_path):
        """Should fail all bridges if network doesn't exist."""
        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            result = bulk_add_bridges(
                "NonExistent",
                [("1DQ1-A", "8QT-H4", None, None)],
            )

        assert result.succeeded == 0
        assert result.failed == 1


class TestBulkRemoveBridges:
    """Tests for bulk_remove_bridges function."""

    def test_bulk_remove_all_success(self, tmp_path):
        """Should remove all specified bridges."""
        config_path = tmp_path / "bridges.json"
        bridge1 = JumpBridge(from_system="A", to_system="B")
        bridge2 = JumpBridge(from_system="C", to_system="D")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge1, bridge2], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = bulk_remove_bridges(
                "TestNet",
                [("A", "B"), ("C", "D")],
            )

            clear_bridge_cache()
            loaded = load_bridge_config()

        assert result.succeeded == 2
        assert result.failed == 0
        assert len(loaded.networks[0].bridges) == 0

    def test_bulk_remove_partial_failure(self, tmp_path):
        """Should report failures for nonexistent bridges."""
        config_path = tmp_path / "bridges.json"
        bridge = JumpBridge(from_system="A", to_system="B")
        network = JumpBridgeNetwork(name="TestNet", bridges=[bridge], enabled=True)
        config = JumpBridgeConfig(networks=[network])

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            save_bridge_config(config)
            clear_bridge_cache()
            result = bulk_remove_bridges(
                "TestNet",
                [("A", "B"), ("X", "Y")],  # First exists, second doesn't
            )

        assert result.succeeded == 1
        assert result.failed == 1
        assert "X" in result.errors[0] and "Y" in result.errors[0]

    def test_bulk_remove_network_not_found(self, tmp_path):
        """Should fail all if network doesn't exist."""
        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with patch(
            "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
        ):
            result = bulk_remove_bridges("NonExistent", [("A", "B")])

        assert result.succeeded == 0
        assert result.failed == 1


class TestDiscoverBridgesFromStructures:
    """Tests for discover_bridges_from_structures function."""

    def test_parse_dash_format(self):
        """Should parse 'SystemA - SystemB' format."""
        structures = [
            {
                "structure_id": 1234567890,
                "name": "1DQ1-A - 8QT-H4",
                "solar_system_id": 30004759,
                "owner_id": 99000001,
            }
        ]
        system_map = {30004759: "1DQ1-A"}

        results = discover_bridges_from_structures(structures, system_map)

        assert len(results) == 1
        bridge, error = results[0]
        assert error is None
        assert bridge.from_system == "1DQ1-A"
        assert bridge.to_system == "8QT-H4"
        assert bridge.structure_id == 1234567890

    def test_parse_arrow_format(self):
        """Should parse 'SystemA » SystemB' format."""
        structures = [
            {
                "structure_id": 1234567890,
                "name": "HED-GP » V-3YG7",
                "solar_system_id": 30001161,
                "owner_id": 99000001,
            }
        ]
        system_map = {30001161: "HED-GP"}

        results = discover_bridges_from_structures(structures, system_map)

        assert len(results) == 1
        bridge, error = results[0]
        assert error is None
        assert bridge.from_system == "HED-GP"
        assert bridge.to_system == "V-3YG7"

    def test_deduplicate_pairs(self):
        """Should deduplicate bridge pairs (both ends of same bridge)."""
        structures = [
            {
                "structure_id": 1111,
                "name": "A - B",
                "solar_system_id": 1,
                "owner_id": 99000001,
            },
            {
                "structure_id": 2222,
                "name": "B - A",
                "solar_system_id": 2,
                "owner_id": 99000001,
            },
        ]
        system_map = {1: "A", 2: "B"}

        results = discover_bridges_from_structures(structures, system_map)

        # Should only return one bridge (deduplicated)
        valid = [r for r in results if r[1] is None]
        assert len(valid) == 1

    def test_unparseable_name(self):
        """Should return error for unparseable names."""
        structures = [
            {
                "structure_id": 1234,
                "name": "Random Structure Name",
                "solar_system_id": 1,
                "owner_id": 99000001,
            }
        ]
        system_map = {1: "TestSystem"}

        results = discover_bridges_from_structures(structures, system_map)

        assert len(results) == 1
        bridge, error = results[0]
        assert error is not None
        assert "Could not parse" in error

    def test_missing_system_map(self):
        """Should handle missing system in map."""
        structures = [
            {
                "structure_id": 1234,
                "name": "A - B",
                "solar_system_id": 99999,  # Not in map
                "owner_id": 99000001,
            }
        ]
        system_map = {}

        results = discover_bridges_from_structures(structures, system_map)

        # Should still parse from name
        assert len(results) == 1
        bridge, error = results[0]
        assert error is None
        assert bridge.from_system == "A"
        assert bridge.to_system == "B"


class TestGetBridgeRouteInfo:
    """Tests for get_bridge_route_info function."""

    def test_route_comparison(self, mock_universe, tmp_path):
        """Should return route comparison data."""
        config_path = tmp_path / "bridges.json"
        # Create a network with bridges
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()

        # Mock route responses
        mock_without = MagicMock()
        mock_without.total_jumps = 15
        mock_without.max_risk = 50.0
        mock_without.avg_risk = 25.0

        mock_with = MagicMock()
        mock_with.total_jumps = 10
        mock_with.max_risk = 40.0
        mock_with.avg_risk = 20.0
        mock_with.bridges_used = 2

        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
            patch(
                "backend.app.services.routing.compute_route",
                side_effect=[mock_without, mock_with],
            ),
        ):
            result = get_bridge_route_info("1DQ1-A", "HED-GP")

        assert result["from_system"] == "1DQ1-A"
        assert result["to_system"] == "HED-GP"
        assert result["without_bridges"]["jumps"] == 15
        assert result["with_bridges"]["jumps"] == 10
        assert result["with_bridges"]["bridges_used"] == 2
        assert result["jumps_saved"] == 5

    def test_unknown_system(self, mock_universe, tmp_path):
        """Should return error for unknown system."""
        config_path = tmp_path / "bridges.json"
        config_path.write_text('{"networks": []}')

        clear_bridge_cache()
        with (
            patch("backend.app.services.jumpbridge.load_universe", return_value=mock_universe),
            patch(
                "backend.app.services.jumpbridge.get_bridge_config_path", return_value=config_path
            ),
        ):
            result = get_bridge_route_info("FakeSystem", "1DQ1-A")

        assert "error" in result
        assert "Unknown system" in result["error"]
