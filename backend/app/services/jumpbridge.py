"""Jump bridge management service."""

import json
import re
from pathlib import Path

from ..core.config import settings
from ..models.jumpbridge import (
    BridgeValidationIssue,
    BridgeValidationResult,
    BulkBridgeResponse,
    JumpBridge,
    JumpBridgeConfig,
    JumpBridgeImportResponse,
    JumpBridgeNetwork,
    JumpBridgeStats,
)
from .data_loader import load_universe

# Cache for jump bridge config
_bridge_config: JumpBridgeConfig | None = None


def get_bridge_config_path() -> Path:
    """Get path to jump bridge config file."""
    return settings.DATA_DIR / "jumpbridges.json"


def load_bridge_config() -> JumpBridgeConfig:
    """Load jump bridge configuration from file."""
    global _bridge_config
    if _bridge_config is not None:
        return _bridge_config

    config_path = get_bridge_config_path()
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        _bridge_config = JumpBridgeConfig(**raw)
    else:
        _bridge_config = JumpBridgeConfig(networks=[])

    return _bridge_config


def save_bridge_config(config: JumpBridgeConfig) -> None:
    """Save jump bridge configuration to file."""
    global _bridge_config
    config_path = get_bridge_config_path()
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)
    _bridge_config = config


def clear_bridge_cache() -> None:
    """Clear the cached bridge config."""
    global _bridge_config
    _bridge_config = None


def parse_bridge_text(text: str) -> tuple[list[JumpBridge], list[str]]:
    """
    Parse jump bridge text format into bridge objects.

    Supported formats:
    - "System1 --> System2" (one-way, though bridges are bidirectional)
    - "System1 <-> System2" (explicit bidirectional)
    - "System1 <> System2" (alternate bidirectional)
    - "System1 - System2" (simple format)

    Args:
        text: Raw text with one bridge per line

    Returns:
        Tuple of (parsed bridges, error messages)
    """
    universe = load_universe()
    bridges: list[JumpBridge] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()

    # Patterns for different formats
    patterns = [
        r"^\s*(.+?)\s*<->\s*(.+?)\s*$",  # System1 <-> System2
        r"^\s*(.+?)\s*<>\s*(.+?)\s*$",  # System1 <> System2
        r"^\s*(.+?)\s*-->\s*(.+?)\s*$",  # System1 --> System2
        r"^\s*(.+?)\s*-\s*(.+?)\s*$",  # System1 - System2
    ]

    for line_num, line in enumerate(text.strip().split("\n"), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        matched = False
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                sys1 = match.group(1).strip()
                sys2 = match.group(2).strip()

                # Validate systems exist
                if sys1 not in universe.systems:
                    errors.append(f"Line {line_num}: Unknown system '{sys1}'")
                    matched = True
                    break
                if sys2 not in universe.systems:
                    errors.append(f"Line {line_num}: Unknown system '{sys2}'")
                    matched = True
                    break

                # Create canonical key to avoid duplicates
                sorted_systems = sorted([sys1, sys2])
                key: tuple[str, str] = (sorted_systems[0], sorted_systems[1])
                if key in seen:
                    matched = True
                    break

                seen.add(key)
                bridges.append(
                    JumpBridge(
                        from_system=sys1,
                        to_system=sys2,
                        structure_id=None,
                        owner=None,
                    )
                )
                matched = True
                break

        if not matched:
            errors.append(f"Line {line_num}: Could not parse '{line}'")

    return bridges, errors


def import_bridges(
    network_name: str,
    bridge_text: str,
    replace: bool = True,
) -> JumpBridgeImportResponse:
    """
    Import jump bridges from text format.

    Args:
        network_name: Name for this bridge network
        bridge_text: Raw text with bridges
        replace: If True, replace existing network; if False, merge

    Returns:
        Import result with counts and errors
    """
    config = load_bridge_config()

    # Parse the bridges
    bridges, errors = parse_bridge_text(bridge_text)

    # Find or create network
    existing_network = None
    for network in config.networks:
        if network.name == network_name:
            existing_network = network
            break

    if existing_network:
        if replace:
            existing_network.bridges = bridges
        else:
            # Merge: add new bridges, skip duplicates
            existing_keys = {
                tuple(sorted([b.from_system, b.to_system])) for b in existing_network.bridges
            }
            for bridge in bridges:
                key = tuple(sorted([bridge.from_system, bridge.to_system]))
                if key not in existing_keys:
                    existing_network.bridges.append(bridge)
                    existing_keys.add(key)
    else:
        config.networks.append(
            JumpBridgeNetwork(
                name=network_name,
                bridges=bridges,
                enabled=True,
            )
        )

    # Save config
    save_bridge_config(config)

    return JumpBridgeImportResponse(
        network_name=network_name,
        bridges_imported=len(bridges),
        bridges_skipped=0,
        errors=errors,
    )


def get_active_bridges() -> list[JumpBridge]:
    """Get all bridges from enabled networks."""
    config = load_bridge_config()
    return config.get_active_bridges()


def toggle_network(network_name: str, enabled: bool) -> bool:
    """
    Enable or disable a jump bridge network.

    Args:
        network_name: Name of the network
        enabled: Whether to enable or disable

    Returns:
        True if network was found and updated
    """
    config = load_bridge_config()
    for network in config.networks:
        if network.name == network_name:
            network.enabled = enabled
            save_bridge_config(config)
            return True
    return False


def delete_network(network_name: str) -> bool:
    """
    Delete a jump bridge network.

    Args:
        network_name: Name of the network to delete

    Returns:
        True if network was found and deleted
    """
    config = load_bridge_config()
    for i, network in enumerate(config.networks):
        if network.name == network_name:
            config.networks.pop(i)
            save_bridge_config(config)
            return True
    return False


def add_bridge(
    network_name: str,
    from_system: str,
    to_system: str,
    structure_id: int | None = None,
    owner: str | None = None,
) -> tuple[bool, str]:
    """
    Add a single jump bridge to a network.

    Args:
        network_name: Name of the network to add bridge to
        from_system: Origin system name
        to_system: Destination system name
        structure_id: Optional ESI structure ID
        owner: Optional owner alliance/corp

    Returns:
        Tuple of (success, message)
    """
    universe = load_universe()

    # Validate systems
    if from_system not in universe.systems:
        return False, f"Unknown system: {from_system}"
    if to_system not in universe.systems:
        return False, f"Unknown system: {to_system}"
    if from_system == to_system:
        return False, "Origin and destination must be different systems"

    config = load_bridge_config()

    # Find network
    network = None
    for n in config.networks:
        if n.name == network_name:
            network = n
            break

    if network is None:
        return False, f"Network not found: {network_name}"

    # Check for duplicate
    key = tuple(sorted([from_system, to_system]))
    for bridge in network.bridges:
        existing_key = tuple(sorted([bridge.from_system, bridge.to_system]))
        if existing_key == key:
            return False, f"Bridge already exists: {from_system} <-> {to_system}"

    # Add bridge
    network.bridges.append(
        JumpBridge(
            from_system=from_system,
            to_system=to_system,
            structure_id=structure_id,
            owner=owner,
        )
    )
    save_bridge_config(config)
    return True, "Bridge added successfully"


def remove_bridge(
    network_name: str,
    from_system: str,
    to_system: str,
) -> tuple[bool, str]:
    """
    Remove a single jump bridge from a network.

    Args:
        network_name: Name of the network
        from_system: Origin system name
        to_system: Destination system name

    Returns:
        Tuple of (success, message)
    """
    config = load_bridge_config()

    # Find network
    network = None
    for n in config.networks:
        if n.name == network_name:
            network = n
            break

    if network is None:
        return False, f"Network not found: {network_name}"

    # Find and remove bridge
    key = tuple(sorted([from_system, to_system]))
    for i, bridge in enumerate(network.bridges):
        existing_key = tuple(sorted([bridge.from_system, bridge.to_system]))
        if existing_key == key:
            network.bridges.pop(i)
            save_bridge_config(config)
            return True, "Bridge removed successfully"

    return False, f"Bridge not found: {from_system} <-> {to_system}"


def get_bridge_stats() -> JumpBridgeStats:
    """
    Get statistics about jump bridge networks.

    Returns:
        JumpBridgeStats with network and bridge counts
    """
    config = load_bridge_config()

    total_bridges = 0
    active_bridges = 0
    active_networks = 0
    bridges_by_network: dict[str, int] = {}
    connected_systems: set[str] = set()

    for network in config.networks:
        bridge_count = len(network.bridges)
        total_bridges += bridge_count
        bridges_by_network[network.name] = bridge_count

        if network.enabled:
            active_networks += 1
            active_bridges += bridge_count
            for bridge in network.bridges:
                connected_systems.add(bridge.from_system)
                connected_systems.add(bridge.to_system)

    return JumpBridgeStats(
        total_networks=len(config.networks),
        active_networks=active_networks,
        total_bridges=total_bridges,
        active_bridges=active_bridges,
        systems_connected=len(connected_systems),
        bridges_by_network=bridges_by_network,
    )


def validate_bridge(
    from_system: str,
    to_system: str,
) -> list[BridgeValidationIssue]:
    """
    Validate a single bridge against universe rules.

    Rules:
    - Both systems must exist
    - Systems must be different
    - Ansiblex bridges cannot be in highsec (security >= 0.5)
    - Warning if bridge connects different regions

    Args:
        from_system: Origin system name
        to_system: Destination system name

    Returns:
        List of validation issues (empty if valid)
    """
    universe = load_universe()
    issues: list[BridgeValidationIssue] = []

    # Check systems exist
    if from_system not in universe.systems:
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue=f"Unknown system: {from_system}",
                severity="error",
            )
        )
        return issues

    if to_system not in universe.systems:
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue=f"Unknown system: {to_system}",
                severity="error",
            )
        )
        return issues

    # Check same system
    if from_system == to_system:
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue="Origin and destination are the same system",
                severity="error",
            )
        )
        return issues

    sys1 = universe.systems[from_system]
    sys2 = universe.systems[to_system]

    # Check highsec - Ansiblex cannot be anchored in highsec
    if sys1.category == "highsec":
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue=f"{from_system} is highsec (security {sys1.security:.1f}) - Ansiblex cannot be anchored",
                severity="error",
            )
        )

    if sys2.category == "highsec":
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue=f"{to_system} is highsec (security {sys2.security:.1f}) - Ansiblex cannot be anchored",
                severity="error",
            )
        )

    # Check wormhole space - cannot have Ansiblex
    if sys1.category == "wh":
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue=f"{from_system} is wormhole space - Ansiblex cannot be anchored",
                severity="error",
            )
        )

    if sys2.category == "wh":
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue=f"{to_system} is wormhole space - Ansiblex cannot be anchored",
                severity="error",
            )
        )

    # Warning if different regions (unusual but possible)
    if sys1.region_id != sys2.region_id:
        issues.append(
            BridgeValidationIssue(
                from_system=from_system,
                to_system=to_system,
                issue=f"Cross-region bridge: {sys1.region_name} to {sys2.region_name}",
                severity="warning",
            )
        )

    return issues


def validate_network(network_name: str) -> BridgeValidationResult:
    """
    Validate all bridges in a network.

    Args:
        network_name: Name of the network to validate

    Returns:
        BridgeValidationResult with all issues found
    """
    config = load_bridge_config()

    # Find network
    network = None
    for n in config.networks:
        if n.name == network_name:
            network = n
            break

    if network is None:
        return BridgeValidationResult(
            network_name=network_name,
            total_bridges=0,
            valid_bridges=0,
            issues=[
                BridgeValidationIssue(
                    from_system="",
                    to_system="",
                    issue=f"Network not found: {network_name}",
                    severity="error",
                )
            ],
        )

    all_issues: list[BridgeValidationIssue] = []
    valid_count = 0

    for bridge in network.bridges:
        issues = validate_bridge(bridge.from_system, bridge.to_system)
        if not any(i.severity == "error" for i in issues):
            valid_count += 1
        all_issues.extend(issues)

    return BridgeValidationResult(
        network_name=network_name,
        total_bridges=len(network.bridges),
        valid_bridges=valid_count,
        issues=all_issues,
    )


def bulk_add_bridges(
    network_name: str,
    bridges: list[tuple[str, str, int | None, str | None]],
) -> BulkBridgeResponse:
    """
    Add multiple bridges to a network.

    Args:
        network_name: Name of the network
        bridges: List of (from_system, to_system, structure_id, owner) tuples

    Returns:
        BulkBridgeResponse with counts and errors
    """
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for from_sys, to_sys, struct_id, owner in bridges:
        success, message = add_bridge(network_name, from_sys, to_sys, struct_id, owner)
        if success:
            succeeded += 1
        else:
            failed += 1
            errors.append(f"{from_sys} <-> {to_sys}: {message}")

    return BulkBridgeResponse(succeeded=succeeded, failed=failed, errors=errors)


def bulk_remove_bridges(
    network_name: str,
    bridges: list[tuple[str, str]],
) -> BulkBridgeResponse:
    """
    Remove multiple bridges from a network.

    Args:
        network_name: Name of the network
        bridges: List of (from_system, to_system) tuples

    Returns:
        BulkBridgeResponse with counts and errors
    """
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for from_sys, to_sys in bridges:
        success, message = remove_bridge(network_name, from_sys, to_sys)
        if success:
            succeeded += 1
        else:
            failed += 1
            errors.append(f"{from_sys} <-> {to_sys}: {message}")

    return BulkBridgeResponse(succeeded=succeeded, failed=failed, errors=errors)
