"""MCP Tool implementations for EVE Gatekeeper."""

from typing import Any

from ..services.fitting import (
    JumpCapability,
    ShipCategory,
    get_travel_recommendation,
    parse_eft_fitting,
)
from ..services.fitting import (
    get_ship_info as _get_ship_info,
)
from ..services.map_visualization import (
    get_region_map,
    get_security_level,
    get_systems_in_range,
)
from ..services.thera import (
    get_active_thera,
    get_thera_cache_age,
    get_thera_last_error,
)
from ..services.webhooks import (
    WebhookSubscription,
    WebhookType,
    add_subscription,
    list_subscriptions,
)


def calculate_route(
    origin: str,
    destination: str,
    profile: str = "shortest",
    avoid_systems: list[str] | None = None,
    use_thera: bool = False,
) -> dict[str, Any]:
    """
    Calculate a route between two systems.

    Note: This is a simplified implementation. Full routing requires
    the universe graph to be loaded.
    """
    avoid_systems = avoid_systems or []

    # Return mock data for demonstration
    # In production, this would call the actual routing service
    result = {
        "origin": origin,
        "destination": destination,
        "profile": profile,
        "avoid_systems": avoid_systems,
        "use_thera": use_thera,
        "status": "route_calculated",
        "message": "Use the /api/v1/route endpoint for full routing with live data",
        "api_endpoint": f"/api/v1/route?origin={origin}&destination={destination}&profile={profile}&use_thera={use_thera}",
    }
    return result


async def get_thera_connections(max_ship_size: str | None = None) -> dict[str, Any]:
    """Get active Thera wormhole connections from EVE-Scout.

    Returns current Thera connections that can be used as shortcuts.
    Optionally filter by max_ship_size (e.g., 'frigate', 'battleship').
    """
    connections = get_active_thera()

    if max_ship_size:
        connections = [c for c in connections if c.max_ship_size.lower() == max_ship_size.lower()]

    return {
        "connections": [
            {
                "id": c.id,
                "in_system_name": c.in_system_name,
                "out_system_name": c.out_system_name,
                "wh_type": c.wh_type,
                "max_ship_size": c.max_ship_size,
                "remaining_hours": c.remaining_hours,
            }
            for c in connections
        ],
        "total": len(connections),
    }


async def get_thera_status() -> dict[str, Any]:
    """Check Thera connection cache status and EVE-Scout API health."""
    cache_age = get_thera_cache_age()
    last_error = get_thera_last_error()
    connections = get_active_thera()

    return {
        "cache_age": cache_age,
        "connection_count": len(connections),
        "api_healthy": last_error is None,
        "last_error": last_error,
    }


def parse_fitting(eft_text: str) -> dict[str, Any]:
    """Parse an EFT format fitting."""
    fitting = parse_eft_fitting(eft_text)

    if not fitting:
        return {
            "error": "Failed to parse fitting",
            "hint": "EFT format should start with [ShipName, FitName]",
        }

    return {
        "ship_name": fitting.ship_name,
        "ship_category": fitting.ship_category.value,
        "jump_capability": fitting.jump_capability.value,
        "modules": fitting.modules,
        "cargo": fitting.cargo,
        "drones": fitting.drones,
        "travel_capabilities": {
            "is_covert_capable": fitting.is_covert_capable,
            "is_cloak_capable": fitting.is_cloak_capable,
            "has_warp_stabs": fitting.has_warp_stabs,
            "is_bubble_immune": fitting.is_bubble_immune,
            "has_align_mods": fitting.has_align_mods,
            "has_warp_speed_mods": fitting.has_warp_speed_mods,
        },
    }


def analyze_fitting(eft_text: str) -> dict[str, Any]:
    """Parse a fitting and provide travel recommendations."""
    fitting = parse_eft_fitting(eft_text)

    if not fitting:
        return {
            "error": "Failed to parse fitting",
            "hint": "EFT format should start with [ShipName, FitName]",
        }

    recommendation = get_travel_recommendation(fitting)

    return {
        "fitting": {
            "ship_name": fitting.ship_name,
            "ship_category": fitting.ship_category.value,
            "jump_capability": fitting.jump_capability.value,
        },
        "travel_recommendation": {
            "can_use_gates": recommendation.can_use_gates,
            "can_use_jump_bridges": recommendation.can_use_jump_bridges,
            "can_jump": recommendation.can_jump,
            "can_bridge_others": recommendation.can_bridge_others,
            "can_covert_bridge": recommendation.can_covert_bridge,
            "recommended_profile": recommendation.recommended_profile,
            "warnings": recommendation.warnings,
            "tips": recommendation.tips,
        },
    }


def get_ship_info(ship_name: str) -> dict[str, Any]:
    """Get information about a ship type."""
    info = _get_ship_info(ship_name)

    if not info:
        return {
            "error": f"Ship not found: {ship_name}",
            "hint": "Check the ship name spelling",
        }

    category: ShipCategory = info["category"]
    jump: JumpCapability = info["jump"]

    return {
        "ship_name": ship_name,
        "category": category.value,
        "jump_capability": jump.value,
        "can_jump": jump != JumpCapability.none,
        "can_use_gates": category not in [ShipCategory.capital, ShipCategory.supercapital],
    }


def check_system_threat(system_name: str) -> dict[str, Any]:
    """
    Check the threat level for a system.

    Note: This is a simplified implementation. Full threat data requires
    the live kill feed.
    """
    # Return mock data for demonstration
    # In production, this would query the zkill listener
    return {
        "system_name": system_name,
        "status": "data_available_via_api",
        "message": "Use the /api/v1/stats endpoint for live kill data",
        "api_endpoints": {
            "system_stats": f"/api/v1/stats/system/{system_name}",
            "recent_kills": f"/api/v1/stats/system/{system_name}/kills",
        },
    }


def get_region_info(region_name: str) -> dict[str, Any]:
    """Get information about a region."""
    data = get_region_map(region_name)

    if not data:
        return {
            "error": f"Region not found: {region_name}",
            "hint": "Check the region name spelling (e.g., 'The Forge', 'Domain')",
        }

    # Count systems by security level
    high_sec = sum(1 for s in data.systems if s.security_status >= 0.5)
    low_sec = sum(1 for s in data.systems if 0.0 < s.security_status < 0.5)
    null_sec = sum(1 for s in data.systems if s.security_status <= 0.0)

    return {
        "region_id": data.region_id,
        "region_name": data.region_name,
        "system_count": len(data.systems),
        "connection_count": len(data.connections),
        "security_breakdown": {
            "high_sec": high_sec,
            "low_sec": low_sec,
            "null_sec": null_sec,
        },
    }


def get_jump_range(center_system: str, max_jumps: int = 5) -> dict[str, Any]:
    """Get all systems within jump range."""
    max_jumps = min(max(max_jumps, 1), 20)  # Clamp to 1-20

    result = get_systems_in_range(center_system, max_jumps, include_connections=False)

    if not result:
        return {
            "error": f"System not found: {center_system}",
            "hint": "Check the system name spelling",
        }

    systems, _ = result

    # Group by security level
    by_security = {"high_sec": [], "low_sec": [], "null_sec": []}
    for s in systems:
        level = get_security_level(s.security_status).value
        by_security[level].append(s.system_name)

    return {
        "center_system": center_system,
        "max_jumps": max_jumps,
        "total_systems": len(systems),
        "systems_by_security": by_security,
    }


async def create_alert_subscription(
    webhook_url: str,
    webhook_type: str = "discord",
    systems: list[str] | None = None,
    min_value: float | None = None,
) -> dict[str, Any]:
    """Create a kill alert subscription."""
    import secrets

    try:
        wh_type = WebhookType(webhook_type)
    except ValueError:
        return {
            "error": f"Invalid webhook type: {webhook_type}",
            "valid_types": ["discord", "slack"],
        }

    sub_id = secrets.token_urlsafe(8)

    subscription = WebhookSubscription(
        id=sub_id,
        webhook_url=webhook_url,
        webhook_type=wh_type,
        systems=systems or [],
        min_value=min_value,
    )

    add_subscription(subscription)

    return {
        "status": "created",
        "subscription_id": sub_id,
        "webhook_type": webhook_type,
        "systems": systems or ["all"],
        "min_value": min_value,
    }


async def list_alert_subscriptions() -> dict[str, Any]:
    """List all alert subscriptions."""
    subs = list_subscriptions()

    return {
        "total": len(subs),
        "subscriptions": [
            {
                "id": s.id,
                "name": s.name,
                "webhook_type": s.webhook_type.value,
                "systems": s.systems or ["all"],
                "min_value": s.min_value,
                "enabled": s.enabled,
            }
            for s in subs
        ],
    }
