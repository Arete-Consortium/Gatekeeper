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
