"""In-memory feature usage and endpoint tracking for admin analytics.

Tracks:
- Feature usage counters (map views, route calculations, intel lookups, kill feed connections)
- Endpoint hit counts (top N most-hit API endpoints)
- Unique IPs in last 24h for DAU estimation

All data is in-memory — resets on server restart. No new DB tables needed.
"""

import time
from collections import Counter
from threading import Lock

# ---------------------------------------------------------------------------
# Feature usage counters
# ---------------------------------------------------------------------------

_feature_lock = Lock()
_feature_counts: Counter[str] = Counter()


def track_feature(feature: str) -> None:
    """Increment a feature usage counter."""
    with _feature_lock:
        _feature_counts[feature] += 1


def get_feature_usage() -> dict[str, int]:
    """Return current feature usage counts."""
    with _feature_lock:
        return dict(_feature_counts)


# ---------------------------------------------------------------------------
# Endpoint hit tracking
# ---------------------------------------------------------------------------

_endpoint_lock = Lock()
_endpoint_counts: Counter[str] = Counter()


def track_endpoint(path: str) -> None:
    """Increment an endpoint hit counter."""
    with _endpoint_lock:
        _endpoint_counts[path] += 1


def get_top_endpoints(n: int = 10) -> list[dict[str, int | str]]:
    """Return top N most-hit endpoints."""
    with _endpoint_lock:
        return [
            {"endpoint": path, "count": count} for path, count in _endpoint_counts.most_common(n)
        ]


# ---------------------------------------------------------------------------
# DAU estimation (unique IPs in 24h window)
# ---------------------------------------------------------------------------

_dau_lock = Lock()
_ip_timestamps: dict[str, float] = {}
_DAU_WINDOW = 86400.0  # 24 hours


def track_request_ip(ip: str) -> None:
    """Record an IP as active. Keeps latest timestamp per IP."""
    now = time.time()
    with _dau_lock:
        _ip_timestamps[ip] = now


def get_dau_estimate() -> int:
    """Return count of unique IPs seen in the last 24 hours."""
    cutoff = time.time() - _DAU_WINDOW
    with _dau_lock:
        # Prune old entries while counting
        active = {ip: ts for ip, ts in _ip_timestamps.items() if ts >= cutoff}
        _ip_timestamps.clear()
        _ip_timestamps.update(active)
        return len(active)
