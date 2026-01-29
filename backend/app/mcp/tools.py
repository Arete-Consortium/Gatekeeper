"""MCP Tool implementations for EVE Gatekeeper."""

import re
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
from ..services.risk_engine import compute_risk, risk_to_color
from ..services.routing import compute_route
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


# =============================================================================
# Input Validation Helpers
# =============================================================================

class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint


def _validate_string(value: Any, name: str, required: bool = True) -> str | None:
    """Validate a string input.

    Args:
        value: The value to validate
        name: Parameter name for error messages
        required: Whether the parameter is required

    Returns:
        Validated string or None if not required and empty

    Raises:
        ValidationError: If validation fails
    """
    if value is None:
        if required:
            raise ValidationError(
                f"Missing required parameter: {name}",
                hint=f"Please provide a value for '{name}'",
            )
        return None

    if not isinstance(value, str):
        raise ValidationError(
            f"Invalid type for '{name}': expected string, got {type(value).__name__}",
            hint=f"'{name}' must be a text value",
        )

    stripped = value.strip()
    if not stripped:
        if required:
            raise ValidationError(
                f"Empty value for required parameter: {name}",
                hint=f"'{name}' cannot be empty or whitespace-only",
            )
        return None

    return stripped


def _validate_system_name(value: Any, name: str = "system_name") -> str:
    """Validate a system name input."""
    result = _validate_string(value, name, required=True)
    if result is None:
        raise ValidationError(f"System name is required", hint="Provide a valid system name")
    # System names shouldn't be excessively long
    if len(result) > 100:
        raise ValidationError(
            f"System name too long: {len(result)} characters",
            hint="System names are typically short (e.g., 'Jita', 'HED-GP')",
        )
    return result


def _validate_region_name(value: Any, name: str = "region_name") -> str:
    """Validate a region name input."""
    result = _validate_string(value, name, required=True)
    if result is None:
        raise ValidationError(f"Region name is required", hint="Provide a valid region name")
    if len(result) > 100:
        raise ValidationError(
            f"Region name too long: {len(result)} characters",
            hint="Region names are typically short (e.g., 'The Forge', 'Domain')",
        )
    return result


def _validate_ship_name(value: Any, name: str = "ship_name") -> str:
    """Validate a ship name input."""
    result = _validate_string(value, name, required=True)
    if result is None:
        raise ValidationError(f"Ship name is required", hint="Provide a valid ship name")
    if len(result) > 100:
        raise ValidationError(
            f"Ship name too long: {len(result)} characters",
            hint="Ship names are typically short (e.g., 'Caracal', 'Archon')",
        )
    return result


def _validate_eft_text(value: Any, name: str = "eft_text") -> str:
    """Validate EFT fitting text input."""
    result = _validate_string(value, name, required=True)
    if result is None:
        raise ValidationError(
            f"EFT text is required",
            hint="EFT format should start with [ShipName, FitName]",
        )
    # Basic sanity check - EFT should start with [
    if not result.startswith("["):
        raise ValidationError(
            "Invalid EFT format: must start with '['",
            hint="EFT format should start with [ShipName, FitName]",
        )
    return result


def _validate_integer(
    value: Any,
    name: str,
    min_val: int | None = None,
    max_val: int | None = None,
    default: int | None = None,
) -> int:
    """Validate an integer input with optional bounds.

    Args:
        value: The value to validate
        name: Parameter name for error messages
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        default: Default value if None provided

    Returns:
        Validated integer, clamped to bounds if provided

    Raises:
        ValidationError: If validation fails and no default provided
    """
    if value is None:
        if default is not None:
            return default
        raise ValidationError(
            f"Missing required parameter: {name}",
            hint=f"Please provide an integer value for '{name}'",
        )

    # Handle numeric types
    if isinstance(value, bool):
        raise ValidationError(
            f"Invalid type for '{name}': expected integer, got boolean",
            hint=f"'{name}' must be a number, not true/false",
        )

    if isinstance(value, float):
        value = int(value)
    elif not isinstance(value, int):
        raise ValidationError(
            f"Invalid type for '{name}': expected integer, got {type(value).__name__}",
            hint=f"'{name}' must be a whole number",
        )

    # Clamp to bounds
    if min_val is not None and value < min_val:
        value = min_val
    if max_val is not None and value > max_val:
        value = max_val

    return value


def _validate_float(
    value: Any,
    name: str,
    min_val: float | None = None,
    max_val: float | None = None,
    default: float | None = None,
) -> float | None:
    """Validate a float input with optional bounds."""
    if value is None:
        return default

    if isinstance(value, bool):
        raise ValidationError(
            f"Invalid type for '{name}': expected number, got boolean",
            hint=f"'{name}' must be a number",
        )

    if isinstance(value, (int, float)):
        result = float(value)
    else:
        raise ValidationError(
            f"Invalid type for '{name}': expected number, got {type(value).__name__}",
            hint=f"'{name}' must be a number",
        )

    if min_val is not None and result < min_val:
        raise ValidationError(
            f"Value for '{name}' too small: {result} < {min_val}",
            hint=f"'{name}' must be at least {min_val}",
        )
    if max_val is not None and result > max_val:
        raise ValidationError(
            f"Value for '{name}' too large: {result} > {max_val}",
            hint=f"'{name}' must be at most {max_val}",
        )

    return result


def _validate_string_list(value: Any, name: str, max_items: int = 100) -> list[str]:
    """Validate a list of strings.

    Returns empty list if value is None.
    """
    if value is None:
        return []

    if not isinstance(value, list):
        raise ValidationError(
            f"Invalid type for '{name}': expected list, got {type(value).__name__}",
            hint=f"'{name}' must be a list of strings",
        )

    if len(value) > max_items:
        raise ValidationError(
            f"Too many items in '{name}': {len(value)} > {max_items}",
            hint=f"'{name}' can have at most {max_items} items",
        )

    result = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise ValidationError(
                f"Invalid item type in '{name}' at index {i}: expected string",
                hint=f"All items in '{name}' must be strings",
            )
        stripped = item.strip()
        if stripped:
            result.append(stripped)

    return result


def _validate_webhook_url(value: Any, name: str = "webhook_url") -> str:
    """Validate a webhook URL.

    Checks for basic URL format and common webhook patterns.
    """
    result = _validate_string(value, name, required=True)
    if result is None:
        raise ValidationError(
            "Webhook URL is required",
            hint="Provide a Discord or Slack webhook URL",
        )

    # Basic URL validation
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"[a-zA-Z0-9]"  # Must start with alphanumeric
        r"[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]*$"  # Valid URL characters
    )

    if not url_pattern.match(result):
        raise ValidationError(
            f"Invalid URL format: {result[:50]}{'...' if len(result) > 50 else ''}",
            hint="URL must start with http:// or https://",
        )

    # Warn about very long URLs
    if len(result) > 500:
        raise ValidationError(
            "URL too long",
            hint="Webhook URLs are typically shorter than 500 characters",
        )

    return result


def _validation_error_to_dict(error: ValidationError) -> dict[str, Any]:
    """Convert a ValidationError to a response dict."""
    result: dict[str, Any] = {"error": error.message}
    if error.hint:
        result["hint"] = error.hint
    return result


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
    # Input validation
    try:
        validated_origin = _validate_system_name(origin, "origin")
        validated_destination = _validate_system_name(destination, "destination")
        validated_avoid = _validate_string_list(avoid_systems, "avoid_systems", max_items=50)
    except ValidationError as e:
        return _validation_error_to_dict(e)

    # Validate profile
    valid_profiles = ["shortest", "safer", "paranoid"]
    if profile not in valid_profiles:
        return {
            "error": f"Invalid profile: {profile}",
            "hint": f"Valid profiles are: {', '.join(valid_profiles)}",
            "valid_profiles": valid_profiles,
        }

    # Validate use_thera is boolean
    if not isinstance(use_thera, bool):
        use_thera = bool(use_thera)

    try:
        route = compute_route(
            from_system=validated_origin,
            to_system=validated_destination,
            profile=profile,
            avoid=set(validated_avoid) if validated_avoid else None,
            use_thera=use_thera,
        )
        return route.model_dump()
    except ValueError as e:
        return {"error": str(e)}


async def get_thera_connections(max_ship_size: str | None = None) -> dict[str, Any]:
    """Get active Thera wormhole connections from EVE-Scout.

    Returns current Thera connections that can be used as shortcuts.
    Optionally filter by max_ship_size (e.g., 'frigate', 'battleship').
    """
    # Validate max_ship_size if provided
    if max_ship_size is not None:
        try:
            max_ship_size = _validate_string(max_ship_size, "max_ship_size", required=False)
        except ValidationError as e:
            return _validation_error_to_dict(e)

    try:
        connections = get_active_thera()
    except Exception as e:
        return {
            "error": f"Failed to fetch Thera connections: {str(e)}",
            "hint": "EVE-Scout API may be temporarily unavailable",
            "connections": [],
            "total": 0,
        }

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
    try:
        cache_age = get_thera_cache_age()
        last_error = get_thera_last_error()
        connections = get_active_thera()

        return {
            "cache_age": cache_age,
            "connection_count": len(connections),
            "api_healthy": last_error is None,
            "last_error": last_error,
        }
    except Exception as e:
        return {
            "cache_age": None,
            "connection_count": 0,
            "api_healthy": False,
            "last_error": f"Failed to get Thera status: {str(e)}",
        }


def parse_fitting(eft_text: str) -> dict[str, Any]:
    """Parse an EFT format fitting."""
    # Input validation
    try:
        validated_text = _validate_eft_text(eft_text, "eft_text")
    except ValidationError as e:
        return _validation_error_to_dict(e)

    try:
        fitting = parse_eft_fitting(validated_text)
    except Exception as e:
        return {
            "error": f"Failed to parse fitting: {str(e)}",
            "hint": "EFT format should start with [ShipName, FitName]",
        }

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
    # Input validation
    try:
        validated_text = _validate_eft_text(eft_text, "eft_text")
    except ValidationError as e:
        return _validation_error_to_dict(e)

    try:
        fitting = parse_eft_fitting(validated_text)
    except Exception as e:
        return {
            "error": f"Failed to parse fitting: {str(e)}",
            "hint": "EFT format should start with [ShipName, FitName]",
        }

    if not fitting:
        return {
            "error": "Failed to parse fitting",
            "hint": "EFT format should start with [ShipName, FitName]",
        }

    try:
        recommendation = get_travel_recommendation(fitting)
    except Exception as e:
        return {
            "error": f"Failed to analyze fitting: {str(e)}",
            "fitting": {
                "ship_name": fitting.ship_name,
                "ship_category": fitting.ship_category.value,
            },
        }

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
    # Input validation
    try:
        validated_name = _validate_ship_name(ship_name, "ship_name")
    except ValidationError as e:
        return _validation_error_to_dict(e)

    try:
        info = _get_ship_info(validated_name)
    except Exception as e:
        return {
            "error": f"Failed to get ship info: {str(e)}",
            "hint": "Check the ship name spelling",
        }

    if not info:
        return {
            "error": f"Ship not found: {validated_name}",
            "hint": "Check the ship name spelling",
        }

    category: ShipCategory = info["category"]
    jump: JumpCapability = info["jump"]

    return {
        "ship_name": validated_name,
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
    # Input validation
    try:
        validated_name = _validate_system_name(system_name, "system_name")
    except ValidationError as e:
        return _validation_error_to_dict(e)

    try:
        report = compute_risk(validated_name)
        color = risk_to_color(report.score)
        return {
            "system_name": validated_name,
            "system_id": report.system_id,
            "security": report.security,
            "risk_score": report.score,
            "risk_color": color,
            "danger_level": report.danger_level.value if report.danger_level else "unknown",
            "category": report.category,
            "breakdown": report.breakdown.model_dump(),
        }
    except ValueError as e:
        return {
            "error": str(e),
            "hint": "Check the system name spelling",
        }
    except Exception as e:
        return {
            "error": f"Failed to compute system threat: {str(e)}",
            "hint": "An unexpected error occurred",
        }


def get_region_info(region_name: str) -> dict[str, Any]:
    """Get information about a region."""
    # Input validation
    try:
        validated_name = _validate_region_name(region_name, "region_name")
    except ValidationError as e:
        return _validation_error_to_dict(e)

    try:
        data = get_region_map(validated_name)
    except Exception as e:
        return {
            "error": f"Failed to get region info: {str(e)}",
            "hint": "Check the region name spelling (e.g., 'The Forge', 'Domain')",
        }

    if not data:
        return {
            "error": f"Region not found: {validated_name}",
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
    # Input validation
    try:
        validated_system = _validate_system_name(center_system, "center_system")
    except ValidationError as e:
        return _validation_error_to_dict(e)

    # Validate and clamp max_jumps
    try:
        validated_jumps = _validate_integer(max_jumps, "max_jumps", min_val=1, max_val=20, default=5)
    except ValidationError as e:
        return _validation_error_to_dict(e)

    try:
        result = get_systems_in_range(validated_system, validated_jumps, include_connections=False)
    except Exception as e:
        return {
            "error": f"Failed to get systems in range: {str(e)}",
            "hint": "Check the system name spelling",
        }

    if not result:
        return {
            "error": f"System not found: {validated_system}",
            "hint": "Check the system name spelling",
        }

    systems, _ = result

    # Group by security level
    by_security: dict[str, list[str]] = {"high_sec": [], "low_sec": [], "null_sec": []}
    for s in systems:
        level = get_security_level(s.security_status).value
        by_security[level].append(s.system_name)

    return {
        "center_system": validated_system,
        "max_jumps": validated_jumps,
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

    # Input validation
    try:
        validated_url = _validate_webhook_url(webhook_url, "webhook_url")
    except ValidationError as e:
        return _validation_error_to_dict(e)

    try:
        validated_systems = _validate_string_list(systems, "systems", max_items=100)
    except ValidationError as e:
        return _validation_error_to_dict(e)

    # Validate min_value if provided
    if min_value is not None:
        try:
            validated_min_value = _validate_float(min_value, "min_value", min_val=0.0)
        except ValidationError as e:
            return _validation_error_to_dict(e)
    else:
        validated_min_value = None

    # Validate webhook_type
    try:
        wh_type = WebhookType(webhook_type)
    except ValueError:
        valid_types = [t.value for t in WebhookType]
        return {
            "error": f"Invalid webhook type: {webhook_type}",
            "hint": f"Valid types are: {', '.join(valid_types)}",
            "valid_types": valid_types,
        }

    sub_id = secrets.token_urlsafe(8)

    try:
        subscription = WebhookSubscription(
            id=sub_id,
            webhook_url=validated_url,
            webhook_type=wh_type,
            systems=validated_systems or [],
            min_value=validated_min_value,
        )

        add_subscription(subscription)
    except Exception as e:
        return {
            "error": f"Failed to create subscription: {str(e)}",
            "hint": "An unexpected error occurred",
        }

    return {
        "status": "created",
        "subscription_id": sub_id,
        "webhook_type": webhook_type,
        "systems": validated_systems or ["all"],
        "min_value": validated_min_value,
    }


async def list_alert_subscriptions() -> dict[str, Any]:
    """List all alert subscriptions."""
    try:
        subs = list_subscriptions()
    except Exception as e:
        return {
            "error": f"Failed to list subscriptions: {str(e)}",
            "hint": "An unexpected error occurred",
            "total": 0,
            "subscriptions": [],
        }

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
