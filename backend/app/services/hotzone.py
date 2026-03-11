"""Hotzone detection service.

Computes top active systems from real-time kill history with trend prediction.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from .data_loader import load_universe
from .kill_history import get_kill_history

logger = logging.getLogger(__name__)

# Trend decay factor for prediction
TREND_DECAY = 0.7


class HotzoneSystem(BaseModel):
    """A system with current hotzone activity and trend prediction."""

    system_id: int
    system_name: str
    security: float
    category: str
    region_name: str = ""
    kills_current: int = Field(0, description="Kills in the selected time window")
    pods_current: int = Field(0, description="Pods in the selected time window")
    kills_previous: int = Field(0, description="Kills in the previous equivalent window")
    trend: float = Field(0.0, description=">1.0 heating up, <1.0 cooling down")
    predicted_1hr: int = Field(0, description="Predicted kills in next hour")
    predicted_2hr: int = Field(0, description="Predicted kills in next 2 hours")
    gate_camp_likely: bool = Field(False, description="High pod:kill ratio detected")


def _sec_category(sec: float) -> str:
    if sec >= 0.5:
        return "high_sec"
    if sec > 0.0:
        return "low_sec"
    return "null_sec"


def _count_kills_in_window(
    kills: list[dict[str, Any]], start: datetime, end: datetime
) -> tuple[int, int]:
    """Count ship kills and pod kills within a time window."""
    ship_kills = 0
    pod_kills = 0
    for kill in kills:
        received_str = kill.get("received_at") or kill.get("kill_time", "")
        if not received_str:
            continue
        try:
            received = datetime.fromisoformat(received_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if start <= received <= end:
            if kill.get("is_pod", False):
                pod_kills += 1
            else:
                ship_kills += 1
    return ship_kills, pod_kills


def get_hotzone_systems(
    hours: int = 1,
    limit: int = 25,
    sec_filter: str | None = None,
) -> list[HotzoneSystem]:
    """Get top active systems from kill history with trend data.

    Args:
        hours: Time window for current activity (1, 6, or 24)
        limit: Max systems to return
        sec_filter: Optional security filter: "high", "low", "null"

    Returns:
        List of HotzoneSystem sorted by current kills descending.
    """
    history = get_kill_history()
    universe = load_universe()

    now = datetime.now(UTC)
    window_start = now - timedelta(hours=hours)
    prev_window_start = window_start - timedelta(hours=hours)

    # Build system info lookup
    id_to_info: dict[int, dict] = {}
    for name, sys in universe.systems.items():
        id_to_info[sys.id] = {
            "name": name,
            "security": sys.security,
            "category": _sec_category(sys.security),
            "region_id": sys.region_id,
        }

    # Region name lookup from map config (optional)
    region_names: dict[int, str] = {}
    try:
        from .data_loader import load_map_config
        config = load_map_config()
        if config and hasattr(config, "systems"):
            for sys_data in config.systems.values():
                if hasattr(sys_data, "region_name") and hasattr(sys_data, "region_id"):
                    region_names[sys_data.region_id] = sys_data.region_name
    except Exception:
        pass

    # Aggregate kills per system
    results: list[HotzoneSystem] = []
    for system_id, kill_ids in history._by_system.items():
        if system_id not in id_to_info:
            continue

        info = id_to_info[system_id]

        # Apply security filter
        if sec_filter:
            if sec_filter == "high" and info["category"] != "high_sec":
                continue
            if sec_filter == "low" and info["category"] != "low_sec":
                continue
            if sec_filter == "null" and info["category"] != "null_sec":
                continue

        # Get all kills for this system
        system_kills = [history._kills[kid] for kid in kill_ids if kid in history._kills]

        # Count current window
        kills_current, pods_current = _count_kills_in_window(system_kills, window_start, now)
        if kills_current == 0 and pods_current == 0:
            continue

        # Count previous window (for trend)
        kills_previous, _ = _count_kills_in_window(system_kills, prev_window_start, window_start)

        # Compute trend: current / previous baseline
        baseline = max(kills_previous, 1)
        trend = kills_current / baseline

        # Prediction: simple decay
        hourly_rate = kills_current / max(hours, 1)
        predicted_1hr = max(0, round(hourly_rate * TREND_DECAY))
        predicted_2hr = max(0, round(hourly_rate * TREND_DECAY * TREND_DECAY))

        # Gate camp detection
        total_activity = kills_current + pods_current
        gate_camp_likely = (
            pods_current > 0
            and kills_current > 0
            and (pods_current / kills_current) > 0.5
            and total_activity >= 3
        )

        results.append(
            HotzoneSystem(
                system_id=system_id,
                system_name=info["name"],
                security=round(info["security"], 1),
                category=info["category"],
                region_name=region_names.get(info["region_id"], ""),
                kills_current=kills_current,
                pods_current=pods_current,
                kills_previous=kills_previous,
                trend=round(trend, 2),
                predicted_1hr=predicted_1hr,
                predicted_2hr=predicted_2hr,
                gate_camp_likely=gate_camp_likely,
            )
        )

    # Sort by current kills descending
    results.sort(key=lambda s: s.kills_current + s.pods_current, reverse=True)
    return results[:limit]
