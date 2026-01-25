"""AI-powered route analysis service."""

from ..models.ai import (
    AlternativeRoute,
    DangerThresholdsResponse,
    PathDanger,
    RouteAnalysisRequest,
    RouteAnalysisResponse,
    SystemWarning,
)
from ..models.risk import DangerLevel, ZKillStats
from .data_loader import load_risk_config, load_universe
from .routing import compute_route
from .zkill_stats import get_cached_stats_sync


def classify_danger(stats: ZKillStats, thresholds: dict[str, int]) -> DangerLevel:
    """
    Classify danger level based on kill statistics.

    Args:
        stats: zKill statistics for the system
        thresholds: Dict with 'medium', 'high', 'extreme' threshold values

    Returns:
        DangerLevel classification
    """
    total_activity = stats.recent_kills + stats.recent_pods

    if total_activity >= thresholds.get("extreme", 20):
        return DangerLevel.extreme
    elif total_activity >= thresholds.get("high", 10):
        return DangerLevel.high
    elif total_activity >= thresholds.get("medium", 5):
        return DangerLevel.medium
    else:
        return DangerLevel.low


def generate_system_warning(
    system_name: str,
    system_id: int,
    danger_level: DangerLevel,
    stats: ZKillStats,
) -> SystemWarning:
    """
    Generate a human-readable warning for a dangerous system.

    Args:
        system_name: Name of the system
        system_id: EVE system ID
        danger_level: Classified danger level
        stats: zKill statistics

    Returns:
        SystemWarning with warning text
    """
    total = stats.recent_kills + stats.recent_pods

    if danger_level == DangerLevel.extreme:
        warning_text = (
            f"EXTREME DANGER: {system_name} is a warzone with {total} recent kills. "
            "Avoid at all costs or travel in fleet."
        )
    elif danger_level == DangerLevel.high:
        warning_text = (
            f"HIGH DANGER: {system_name} has significant activity ({total} recent kills). "
            "Use caution and consider alternative routes."
        )
    elif danger_level == DangerLevel.medium:
        warning_text = (
            f"CAUTION: {system_name} shows moderate activity ({total} recent kills). "
            "Stay alert and avoid lingering."
        )
    else:
        warning_text = f"{system_name} appears relatively quiet ({total} recent kills)."

    return SystemWarning(
        system_name=system_name,
        system_id=system_id,
        danger_level=danger_level,
        recent_kills=stats.recent_kills,
        recent_pods=stats.recent_pods,
        warning_text=warning_text,
    )


def generate_assessment(
    from_system: str,
    to_system: str,
    total_jumps: int,
    dangerous_systems: list[tuple[str, DangerLevel]],
) -> tuple[DangerLevel, str]:
    """
    Generate an overall route assessment.

    Args:
        from_system: Origin system
        to_system: Destination system
        total_jumps: Total jumps in route
        dangerous_systems: List of (system_name, danger_level) tuples for dangerous systems

    Returns:
        Tuple of (overall_danger_level, assessment_text)
    """
    # Determine overall danger level
    extreme_count = sum(1 for _, level in dangerous_systems if level == DangerLevel.extreme)
    high_count = sum(1 for _, level in dangerous_systems if level == DangerLevel.high)
    medium_count = sum(1 for _, level in dangerous_systems if level == DangerLevel.medium)

    if extreme_count > 0:
        overall = DangerLevel.extreme
    elif high_count > 0:
        overall = DangerLevel.high
    elif medium_count > 0:
        overall = DangerLevel.medium
    else:
        overall = DangerLevel.low

    # Generate assessment text
    total_dangerous = extreme_count + high_count + medium_count

    if overall == DangerLevel.extreme:
        extreme_names = [name for name, level in dangerous_systems if level == DangerLevel.extreme]
        systems_str = ", ".join(extreme_names[:3])
        if len(extreme_names) > 3:
            systems_str += f" (+{len(extreme_names) - 3} more)"
        assessment = (
            f"CRITICAL: This route passes through {total_dangerous} dangerous system(s) "
            f"including extreme-risk {systems_str}. "
            "Strongly recommend alternative routing or fleet escort."
        )
    elif overall == DangerLevel.high:
        assessment = (
            f"HIGH RISK: Route contains {total_dangerous} dangerous system(s). "
            "Consider 'safer' or 'paranoid' profile for reduced risk."
        )
    elif overall == DangerLevel.medium:
        assessment = (
            f"MODERATE RISK: Route contains {total_dangerous} system(s) with recent activity. "
            "Stay vigilant during transit."
        )
    else:
        assessment = f"LOW RISK: Route appears relatively safe with {total_jumps} jumps."

    return overall, assessment


def _get_system_stats(system_id: int) -> ZKillStats:
    """Get cached stats for a system, returning empty stats if not found."""
    cached = get_cached_stats_sync(system_id)
    return cached if cached else ZKillStats()


def analyze_route(request: RouteAnalysisRequest) -> RouteAnalysisResponse:
    """
    Perform AI-powered route analysis.

    Args:
        request: Route analysis request

    Returns:
        RouteAnalysisResponse with assessment, warnings, and alternatives
    """
    cfg = load_risk_config()
    universe = load_universe()
    thresholds = cfg.danger_thresholds

    # Validate systems
    if request.from_system not in universe.systems:
        raise ValueError(f"Unknown system: {request.from_system}")
    if request.to_system not in universe.systems:
        raise ValueError(f"Unknown system: {request.to_system}")

    # Validate profile
    if request.profile not in cfg.routing_profiles:
        available = ", ".join(cfg.routing_profiles.keys())
        raise ValueError(f"Unknown profile: '{request.profile}'. Available: {available}")

    # Compute the requested route
    avoid_set = set(request.avoid)
    route = compute_route(
        request.from_system,
        request.to_system,
        request.profile,
        avoid=avoid_set,
        use_bridges=request.use_bridges,
    )

    # Analyze each system on the path
    warnings: list[SystemWarning] = []
    path_danger: list[PathDanger] = []
    dangerous_systems: list[tuple[str, DangerLevel]] = []

    for hop in route.path:
        system = universe.systems[hop.system_name]
        stats = _get_system_stats(system.id)
        danger_level = classify_danger(stats, thresholds)

        path_danger.append(
            PathDanger(
                system_name=hop.system_name,
                danger_level=danger_level,
                recent_kills=stats.recent_kills + stats.recent_pods,
            )
        )

        # Track dangerous systems
        if danger_level in (DangerLevel.medium, DangerLevel.high, DangerLevel.extreme):
            dangerous_systems.append((hop.system_name, danger_level))

            # Generate warnings for high/extreme only
            if danger_level in (DangerLevel.high, DangerLevel.extreme):
                warnings.append(
                    generate_system_warning(
                        system_name=hop.system_name,
                        system_id=system.id,
                        danger_level=danger_level,
                        stats=stats,
                    )
                )

    # Generate overall assessment
    overall_danger, assessment = generate_assessment(
        request.from_system,
        request.to_system,
        route.total_jumps,
        dangerous_systems,
    )

    # Find alternatives if dangerous and requested
    alternatives: list[AlternativeRoute] = []
    if request.include_alternatives and overall_danger in (DangerLevel.high, DangerLevel.extreme):
        alternatives = _find_alternatives(
            request.from_system,
            request.to_system,
            request.profile,
            route,
            avoid_set,
            request.use_bridges,
            thresholds,
        )

    return RouteAnalysisResponse(
        from_system=request.from_system,
        to_system=request.to_system,
        profile=request.profile,
        total_jumps=route.total_jumps,
        overall_danger=overall_danger,
        assessment=assessment,
        warnings=warnings,
        alternatives=alternatives,
        path_danger=path_danger,
    )


def _find_alternatives(
    from_system: str,
    to_system: str,
    current_profile: str,
    current_route,
    avoid_set: set[str],
    use_bridges: bool,
    thresholds: dict[str, int],
) -> list[AlternativeRoute]:
    """
    Find alternative safer routes.

    Returns alternatives with 'safer' or 'paranoid' profiles that have
    fewer dangerous systems.
    """
    cfg = load_risk_config()
    alternatives: list[AlternativeRoute] = []

    # Count dangerous systems in current route
    current_dangerous = _count_dangerous_systems(current_route.path, thresholds)

    # Try safer profiles
    profiles_to_try = []
    if current_profile == "shortest":
        profiles_to_try = ["safer", "paranoid"]
    elif current_profile == "safer":
        profiles_to_try = ["paranoid"]

    for profile in profiles_to_try:
        if profile not in cfg.routing_profiles:
            continue

        try:
            alt_route = compute_route(
                from_system,
                to_system,
                profile,
                avoid=avoid_set,
                use_bridges=use_bridges,
            )

            alt_dangerous = _count_dangerous_systems(alt_route.path, thresholds)

            # Only suggest if it's actually better
            if alt_dangerous < current_dangerous:
                jump_diff = alt_route.total_jumps - current_route.total_jumps
                systems_avoided = current_dangerous - alt_dangerous

                if jump_diff > 0:
                    improvement = (
                        f"Adds {jump_diff} jump(s) but avoids {systems_avoided} dangerous system(s)"
                    )
                else:
                    improvement = (
                        f"Same or fewer jumps and avoids {systems_avoided} dangerous system(s)"
                    )

                alternatives.append(
                    AlternativeRoute(
                        profile=profile,
                        total_jumps=alt_route.total_jumps,
                        max_risk=round(alt_route.max_risk, 1),
                        avg_risk=round(alt_route.avg_risk, 1),
                        dangerous_systems=alt_dangerous,
                        improvement=improvement,
                    )
                )
        except ValueError:
            # No route found with this profile, skip
            continue

    return alternatives


def _count_dangerous_systems(path: list, thresholds: dict[str, int]) -> int:
    """Count systems with high or extreme danger level in a path."""
    universe = load_universe()
    count = 0

    for hop in path:
        system = universe.systems[hop.system_name]
        stats = _get_system_stats(system.id)
        danger_level = classify_danger(stats, thresholds)
        if danger_level in (DangerLevel.high, DangerLevel.extreme):
            count += 1

    return count


def get_danger_thresholds() -> DangerThresholdsResponse:
    """Get current danger threshold configuration."""
    cfg = load_risk_config()
    return DangerThresholdsResponse(
        medium=cfg.danger_thresholds.get("medium", 5),
        high=cfg.danger_thresholds.get("high", 10),
        extreme=cfg.danger_thresholds.get("extreme", 20),
        description="Thresholds based on total kills + pods in 24h window",
    )
