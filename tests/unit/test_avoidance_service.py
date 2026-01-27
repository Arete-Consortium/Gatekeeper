"""Unit tests for avoidance list service."""

import json

import pytest


@pytest.fixture(autouse=True)
def isolate_avoidance(tmp_path, monkeypatch):
    """Isolate avoidance config to tmp_path for each test."""
    from backend.app.services.avoidance import clear_avoidance_cache

    config_path = tmp_path / "avoidance_lists.json"
    monkeypatch.setattr(
        "backend.app.services.avoidance.get_avoidance_config_path",
        lambda: config_path,
    )
    clear_avoidance_cache()
    yield
    clear_avoidance_cache()


class TestCreateAvoidanceList:
    """Tests for creating avoidance lists."""

    def test_create_list(self):
        from backend.app.services.avoidance import create_avoidance_list

        result = create_avoidance_list("gatecamps", ["Tama", "Rancer"])
        assert result.name == "gatecamps"
        assert set(result.systems) == {"Tama", "Rancer"}
        assert result.created_at is not None
        assert result.updated_at is not None

    def test_create_duplicate_name_raises(self):
        from backend.app.services.avoidance import create_avoidance_list

        create_avoidance_list("gatecamps", ["Tama"])
        with pytest.raises(ValueError, match="already exists"):
            create_avoidance_list("gatecamps", ["Rancer"])

    def test_create_deduplicates_systems(self):
        from backend.app.services.avoidance import create_avoidance_list

        result = create_avoidance_list("dupes", ["Tama", "Tama", "Rancer"])
        assert result.systems == ["Rancer", "Tama"]  # sorted, deduped

    def test_create_with_description(self):
        from backend.app.services.avoidance import create_avoidance_list

        result = create_avoidance_list("test", ["Tama"], description="Dangerous pipe")
        assert result.description == "Dangerous pipe"


class TestGetAvoidanceList:
    """Tests for retrieving avoidance lists."""

    def test_get_existing(self):
        from backend.app.services.avoidance import create_avoidance_list, get_avoidance_list

        create_avoidance_list("gatecamps", ["Tama", "Rancer"])
        result = get_avoidance_list("gatecamps")
        assert result.name == "gatecamps"
        assert set(result.systems) == {"Tama", "Rancer"}

    def test_get_nonexistent_raises(self):
        from backend.app.services.avoidance import get_avoidance_list

        with pytest.raises(ValueError, match="not found"):
            get_avoidance_list("nonexistent")


class TestUpdateAvoidanceList:
    """Tests for updating avoidance lists."""

    def test_update_replace_systems(self):
        from backend.app.services.avoidance import create_avoidance_list, update_avoidance_list

        create_avoidance_list("test", ["Tama", "Rancer"])
        result = update_avoidance_list("test", systems=["Amamake"])
        assert result.systems == ["Amamake"]

    def test_update_add_systems(self):
        from backend.app.services.avoidance import create_avoidance_list, update_avoidance_list

        create_avoidance_list("test", ["Tama"])
        result = update_avoidance_list("test", add_systems=["Rancer"])
        assert set(result.systems) == {"Tama", "Rancer"}

    def test_update_remove_systems(self):
        from backend.app.services.avoidance import create_avoidance_list, update_avoidance_list

        create_avoidance_list("test", ["Tama", "Rancer"])
        result = update_avoidance_list("test", remove_systems=["Tama"])
        assert result.systems == ["Rancer"]

    def test_update_description(self):
        from backend.app.services.avoidance import create_avoidance_list, update_avoidance_list

        create_avoidance_list("test", ["Tama"])
        result = update_avoidance_list("test", description="Updated desc")
        assert result.description == "Updated desc"

    def test_update_nonexistent_raises(self):
        from backend.app.services.avoidance import update_avoidance_list

        with pytest.raises(ValueError, match="not found"):
            update_avoidance_list("nonexistent", systems=["Tama"])

    def test_update_changes_updated_at(self):
        from backend.app.services.avoidance import create_avoidance_list, update_avoidance_list

        created = create_avoidance_list("test", ["Tama"])
        import time

        time.sleep(0.01)
        updated = update_avoidance_list("test", description="new")
        assert updated.updated_at >= created.updated_at


class TestDeleteAvoidanceList:
    """Tests for deleting avoidance lists."""

    def test_delete_existing(self):
        from backend.app.services.avoidance import (
            create_avoidance_list,
            delete_avoidance_list,
            list_avoidance_lists,
        )

        create_avoidance_list("test", ["Tama"])
        delete_avoidance_list("test")
        assert len(list_avoidance_lists()) == 0

    def test_delete_nonexistent_raises(self):
        from backend.app.services.avoidance import delete_avoidance_list

        with pytest.raises(ValueError, match="not found"):
            delete_avoidance_list("nonexistent")


class TestResolveAvoidance:
    """Tests for resolving named lists to system sets."""

    def test_resolve_single_list(self):
        from backend.app.services.avoidance import create_avoidance_list, resolve_avoidance

        create_avoidance_list("gatecamps", ["Tama", "Rancer"])
        result = resolve_avoidance(["gatecamps"])
        assert result == {"Tama", "Rancer"}

    def test_resolve_multiple_lists_merges(self):
        from backend.app.services.avoidance import create_avoidance_list, resolve_avoidance

        create_avoidance_list("list1", ["Tama", "Rancer"])
        create_avoidance_list("list2", ["Amamake", "Rancer"])
        result = resolve_avoidance(["list1", "list2"])
        assert result == {"Tama", "Rancer", "Amamake"}

    def test_resolve_unknown_list_raises(self):
        from backend.app.services.avoidance import resolve_avoidance

        with pytest.raises(ValueError, match="not found"):
            resolve_avoidance(["nonexistent"])

    def test_resolve_empty_list(self):
        from backend.app.services.avoidance import resolve_avoidance

        result = resolve_avoidance([])
        assert result == set()


class TestPersistence:
    """Tests for file persistence."""

    def test_save_and_reload(self, tmp_path):
        from backend.app.services.avoidance import (
            clear_avoidance_cache,
            create_avoidance_list,
            get_avoidance_list,
        )

        create_avoidance_list("persist", ["Tama", "Rancer"])
        clear_avoidance_cache()
        result = get_avoidance_list("persist")
        assert result.name == "persist"
        assert set(result.systems) == {"Rancer", "Tama"}

    def test_file_created_on_save(self, tmp_path):
        from backend.app.services.avoidance import (
            create_avoidance_list,
            get_avoidance_config_path,
        )

        create_avoidance_list("test", ["Tama"])
        config_path = get_avoidance_config_path()
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert len(data["lists"]) == 1
        assert data["lists"][0]["name"] == "test"


class TestSystemValidation:
    """Tests for system validation (warn but still save)."""

    def test_unknown_systems_still_saved(self):
        """Unknown systems should be saved (warn, not error)."""
        from backend.app.services.avoidance import create_avoidance_list

        result = create_avoidance_list("test", ["FakeSystem", "Jita"])
        assert "FakeSystem" in result.systems
        assert "Jita" in result.systems
