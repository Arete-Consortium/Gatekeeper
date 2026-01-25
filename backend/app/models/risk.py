from enum import Enum

from pydantic import BaseModel


class DangerLevel(str, Enum):
    """Danger classification levels for systems based on kill activity."""

    low = "low"
    medium = "medium"
    high = "high"
    extreme = "extreme"


class RiskConfig(BaseModel):
    security_category_weights: dict[str, float]
    kill_weights: dict[str, float]
    clamp: dict[str, int]
    risk_colors: dict[str, str]
    map_layers: dict[str, bool]
    routing_profiles: dict[str, dict[str, float]]
    danger_thresholds: dict[str, int] = {"medium": 5, "high": 10, "extreme": 20}


class ZKillStats(BaseModel):
    recent_kills: int = 0
    recent_pods: int = 0


class RiskBreakdown(BaseModel):
    security_component: float
    kills_component: float
    pods_component: float


class RiskReport(BaseModel):
    system_name: str
    system_id: int
    category: str
    security: float
    score: float
    breakdown: RiskBreakdown
    zkill_stats: ZKillStats | None = None
    danger_level: DangerLevel | None = None
    ship_profile: str | None = None  # Ship profile used for calculation


class ShipProfile(BaseModel):
    """Ship-type risk profile for adjusted danger calculations."""

    name: str
    description: str
    # Multipliers for different security spaces
    highsec_multiplier: float = 1.0  # Ganks in highsec
    lowsec_multiplier: float = 1.0  # Gate camps in lowsec
    nullsec_multiplier: float = 1.0  # Bubbles in nullsec
    # Multipliers for kill types
    kills_multiplier: float = 1.0  # Recent ship kills weight
    pods_multiplier: float = 1.0  # Recent pod kills weight (indicates camps)


# Predefined ship profiles
SHIP_PROFILES: dict[str, ShipProfile] = {
    "default": ShipProfile(
        name="default",
        description="Standard risk assessment",
    ),
    "hauler": ShipProfile(
        name="hauler",
        description="Industrial ships (Iteron, Bestower, freighters)",
        highsec_multiplier=2.0,  # High gank risk in trade routes
        lowsec_multiplier=1.5,
        nullsec_multiplier=1.2,
        kills_multiplier=1.5,
        pods_multiplier=0.8,  # Pods less relevant for haulers
    ),
    "frigate": ShipProfile(
        name="frigate",
        description="Fast frigates (interceptors, assault frigs)",
        highsec_multiplier=0.5,  # Can often escape ganks
        lowsec_multiplier=0.7,  # Can burn back to gate
        nullsec_multiplier=0.6,  # Interceptors are nullified
        kills_multiplier=0.6,
        pods_multiplier=1.2,  # Pods indicate bubble camps
    ),
    "cruiser": ShipProfile(
        name="cruiser",
        description="Cruisers and battlecruisers",
        highsec_multiplier=1.0,
        lowsec_multiplier=1.2,
        nullsec_multiplier=1.3,
        kills_multiplier=1.0,
        pods_multiplier=1.0,
    ),
    "battleship": ShipProfile(
        name="battleship",
        description="Battleships (slow, high value)",
        highsec_multiplier=1.5,  # Gank magnet
        lowsec_multiplier=1.5,
        nullsec_multiplier=1.8,  # Slow to align, can't escape bubbles
        kills_multiplier=1.3,
        pods_multiplier=1.5,
    ),
    "mining": ShipProfile(
        name="mining",
        description="Mining barges and exhumers",
        highsec_multiplier=2.5,  # Primary gank target
        lowsec_multiplier=2.0,
        nullsec_multiplier=1.5,  # Usually mining in organized space
        kills_multiplier=1.8,
        pods_multiplier=0.5,
    ),
    "capital": ShipProfile(
        name="capital",
        description="Capital ships (use jump drives, not gates)",
        highsec_multiplier=0.0,  # Can't enter highsec
        lowsec_multiplier=0.5,  # Usually cynoing, not gating
        nullsec_multiplier=0.8,  # Jump fatigue is the real concern
        kills_multiplier=0.5,
        pods_multiplier=0.3,
    ),
    "cloaky": ShipProfile(
        name="cloaky",
        description="Covert ops, blockade runners, T3 cruisers",
        highsec_multiplier=0.3,  # Can cloak through danger
        lowsec_multiplier=0.4,
        nullsec_multiplier=0.5,  # Can warp cloaked
        kills_multiplier=0.4,
        pods_multiplier=0.8,  # Decloaking on gate is the risk
    ),
}


def get_ship_profile(profile_name: str) -> ShipProfile:
    """Get a ship profile by name, returns default if not found."""
    return SHIP_PROFILES.get(profile_name, SHIP_PROFILES["default"])
