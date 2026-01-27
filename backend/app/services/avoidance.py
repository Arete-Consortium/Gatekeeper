"""Avoidance list management service."""

import json
from datetime import UTC, datetime
from pathlib import Path

from ..core.config import settings
from ..models.avoidance import AvoidanceConfig, AvoidanceList
from .data_loader import load_universe

# Cache for avoidance config
_avoidance_config: AvoidanceConfig | None = None


def get_avoidance_config_path() -> Path:
    """Get path to avoidance lists config file."""
    return settings.DATA_DIR / "avoidance_lists.json"


def load_avoidance_config() -> AvoidanceConfig:
    """Load avoidance configuration from file."""
    global _avoidance_config
    if _avoidance_config is not None:
        return _avoidance_config

    config_path = get_avoidance_config_path()
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        _avoidance_config = AvoidanceConfig(**raw)
    else:
        _avoidance_config = AvoidanceConfig(lists=[])

    return _avoidance_config


def save_avoidance_config(config: AvoidanceConfig) -> None:
    """Save avoidance configuration to file."""
    global _avoidance_config
    config_path = get_avoidance_config_path()
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2, default=str)
    _avoidance_config = config


def clear_avoidance_cache() -> None:
    """Clear the cached avoidance config."""
    global _avoidance_config
    _avoidance_config = None


def _validate_systems(systems: list[str]) -> list[str]:
    """Validate system names against universe. Returns list of unknown systems."""
    universe = load_universe()
    return [s for s in systems if s not in universe.systems]


def create_avoidance_list(
    name: str,
    systems: list[str],
    description: str = "",
) -> AvoidanceList:
    """Create a new named avoidance list.

    Raises ValueError if a list with the same name already exists.
    Warns (via returned unknown list) but still saves if systems are unknown.
    """
    config = load_avoidance_config()

    # Check for duplicate name
    for existing in config.lists:
        if existing.name == name:
            raise ValueError(f"Avoidance list already exists: {name}")

    now = datetime.now(UTC)
    avoidance_list = AvoidanceList(
        name=name,
        systems=sorted(set(systems)),
        description=description,
        created_at=now,
        updated_at=now,
    )
    config.lists.append(avoidance_list)
    save_avoidance_config(config)
    return avoidance_list


def get_avoidance_list(name: str) -> AvoidanceList:
    """Get a specific avoidance list by name.

    Raises ValueError if not found.
    """
    config = load_avoidance_config()
    for avoidance_list in config.lists:
        if avoidance_list.name == name:
            return avoidance_list
    raise ValueError(f"Avoidance list not found: {name}")


def update_avoidance_list(
    name: str,
    systems: list[str] | None = None,
    description: str | None = None,
    add_systems: list[str] | None = None,
    remove_systems: list[str] | None = None,
) -> AvoidanceList:
    """Update an existing avoidance list.

    Raises ValueError if not found.
    """
    config = load_avoidance_config()

    target = None
    for avoidance_list in config.lists:
        if avoidance_list.name == name:
            target = avoidance_list
            break

    if target is None:
        raise ValueError(f"Avoidance list not found: {name}")

    if systems is not None:
        target.systems = sorted(set(systems))
    if add_systems:
        current = set(target.systems)
        current.update(add_systems)
        target.systems = sorted(current)
    if remove_systems:
        current = set(target.systems)
        current -= set(remove_systems)
        target.systems = sorted(current)
    if description is not None:
        target.description = description

    target.updated_at = datetime.now(UTC)
    save_avoidance_config(config)
    return target


def delete_avoidance_list(name: str) -> None:
    """Delete an avoidance list by name.

    Raises ValueError if not found.
    """
    config = load_avoidance_config()
    for i, avoidance_list in enumerate(config.lists):
        if avoidance_list.name == name:
            config.lists.pop(i)
            save_avoidance_config(config)
            return
    raise ValueError(f"Avoidance list not found: {name}")


def list_avoidance_lists() -> list[AvoidanceList]:
    """Return all avoidance lists."""
    config = load_avoidance_config()
    return config.lists


def resolve_avoidance(names: list[str]) -> set[str]:
    """Resolve named avoidance lists into a union of all systems.

    Raises ValueError if any list name is not found.
    """
    config = load_avoidance_config()
    lists_by_name = {al.name: al for al in config.lists}

    result: set[str] = set()
    for name in names:
        if name not in lists_by_name:
            raise ValueError(f"Avoidance list not found: {name}")
        result.update(lists_by_name[name].systems)
    return result
