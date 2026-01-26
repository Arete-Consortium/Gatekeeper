"""Route sharing service for generating and resolving shared routes.

Enables sharing routes via short tokens and URLs.
"""

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any


@dataclass
class SharedRoute:
    """A shared route with metadata."""

    token: str
    route_data: dict[str, Any]  # Full route response data
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    creator_name: str | None = None
    description: str | None = None
    access_count: int = 0
    last_accessed: datetime | None = None

    # Route summary for quick access
    from_system: str = ""
    to_system: str = ""
    total_jumps: int = 0
    profile: str = ""

    @property
    def is_expired(self) -> bool:
        """Check if route has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def url_path(self) -> str:
        """Get URL path for this shared route."""
        return f"/s/{self.token}"


class RouteShareStore:
    """In-memory storage for shared routes."""

    def __init__(
        self,
        default_ttl_hours: int = 24,
        max_routes: int = 1000,
        token_length: int = 8,
    ):
        self._routes: dict[str, SharedRoute] = {}
        self._lock = RLock()
        self.default_ttl_hours = default_ttl_hours
        self.max_routes = max_routes
        self.token_length = token_length

    def _generate_token(self) -> str:
        """Generate a unique short token."""
        while True:
            # URL-safe base64 token
            raw = secrets.token_bytes(self.token_length)
            token = base64.urlsafe_b64encode(raw).decode("ascii")[: self.token_length]
            # Remove potentially confusing characters
            token = token.replace("-", "x").replace("_", "y")

            with self._lock:
                if token not in self._routes:
                    return token

    def _prune_expired(self) -> None:
        """Remove expired routes."""
        now = datetime.now(UTC)
        with self._lock:
            expired = [
                token
                for token, route in self._routes.items()
                if route.expires_at and route.expires_at < now
            ]
            for token in expired:
                del self._routes[token]

    def _prune_if_full(self) -> None:
        """Remove oldest routes if at capacity."""
        with self._lock:
            if len(self._routes) >= self.max_routes:
                # Sort by last accessed (oldest first) and remove 10%
                sorted_routes = sorted(
                    self._routes.items(),
                    key=lambda x: x[1].last_accessed or x[1].created_at,
                )
                to_remove = len(sorted_routes) // 10
                for token, _ in sorted_routes[: max(to_remove, 1)]:
                    del self._routes[token]

    def create_share(
        self,
        route_data: dict[str, Any],
        ttl_hours: int | None = None,
        creator_name: str | None = None,
        description: str | None = None,
    ) -> SharedRoute:
        """
        Create a shared route.

        Args:
            route_data: Full route response data
            ttl_hours: Hours until expiry (None for default, -1 for never)
            creator_name: Optional creator name
            description: Optional description

        Returns:
            SharedRoute with token
        """
        self._prune_expired()
        self._prune_if_full()

        token = self._generate_token()

        # Calculate expiry
        if ttl_hours == -1:
            expires_at = None
        elif ttl_hours is not None:
            expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        else:
            expires_at = datetime.now(UTC) + timedelta(hours=self.default_ttl_hours)

        # Extract summary fields
        from_system = route_data.get("from_system", "")
        to_system = route_data.get("to_system", "")
        total_jumps = route_data.get("total_jumps", 0)
        profile = route_data.get("profile", "")

        shared = SharedRoute(
            token=token,
            route_data=route_data,
            expires_at=expires_at,
            creator_name=creator_name,
            description=description,
            from_system=from_system,
            to_system=to_system,
            total_jumps=total_jumps,
            profile=profile,
        )

        with self._lock:
            self._routes[token] = shared

        return shared

    def get_share(self, token: str) -> SharedRoute | None:
        """
        Get a shared route by token.

        Updates access count and timestamp.

        Args:
            token: Route token

        Returns:
            SharedRoute or None if not found/expired
        """
        self._prune_expired()

        with self._lock:
            if token not in self._routes:
                return None

            route = self._routes[token]
            if route.is_expired:
                del self._routes[token]
                return None

            route.access_count += 1
            route.last_accessed = datetime.now(UTC)
            return route

    def delete_share(self, token: str) -> bool:
        """
        Delete a shared route.

        Args:
            token: Route token

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if token in self._routes:
                del self._routes[token]
                return True
            return False

    def list_shares(
        self,
        creator_name: str | None = None,
        limit: int = 50,
    ) -> list[SharedRoute]:
        """
        List shared routes.

        Args:
            creator_name: Optional filter by creator
            limit: Max routes to return

        Returns:
            List of SharedRoute (most recent first)
        """
        self._prune_expired()

        with self._lock:
            routes = list(self._routes.values())

            if creator_name:
                routes = [r for r in routes if r.creator_name == creator_name]

            # Sort by created_at descending
            routes.sort(key=lambda x: x.created_at, reverse=True)

            return routes[:limit]

    @property
    def count(self) -> int:
        """Get number of active shared routes."""
        with self._lock:
            return len(self._routes)


# Global store instance
_share_store: RouteShareStore | None = None


def get_share_store() -> RouteShareStore:
    """Get the global share store instance."""
    global _share_store
    if _share_store is None:
        _share_store = RouteShareStore()
    return _share_store


def reset_share_store() -> None:
    """Reset the global share store (for testing)."""
    global _share_store
    _share_store = None


# =============================================================================
# Route Export Formats
# =============================================================================


def export_to_text(route_data: dict[str, Any]) -> str:
    """
    Export route to plain text format.

    Example output:
    ```
    Route: Jita -> Amarr (15 jumps, safer)
    1. Jita (0.95)
    2. Perimeter (0.94)
    ...
    ```
    """
    lines = []

    from_sys = route_data.get("from_system", "?")
    to_sys = route_data.get("to_system", "?")
    jumps = route_data.get("total_jumps", 0)
    profile = route_data.get("profile", "?")

    lines.append(f"Route: {from_sys} -> {to_sys} ({jumps} jumps, {profile})")
    lines.append("")

    path = route_data.get("path", [])
    for i, hop in enumerate(path, 1):
        name = hop.get("system_name", "?")
        security = hop.get("security", 0)
        if security is not None:
            lines.append(f"{i}. {name} ({security:.2f})")
        else:
            lines.append(f"{i}. {name}")

    return "\n".join(lines)


def export_to_waypoint_names(route_data: dict[str, Any]) -> list[str]:
    """
    Export route as list of system names for waypoint setting.

    Returns list of system names in order.
    """
    path = route_data.get("path", [])
    return [hop.get("system_name", "") for hop in path if hop.get("system_name")]


def export_to_dotlan_url(route_data: dict[str, Any]) -> str:
    """
    Generate Dotlan route URL.

    Dotlan uses format: https://evemaps.dotlan.net/route/System1:System2:System3
    """
    base_url = "https://evemaps.dotlan.net/route/"
    path = route_data.get("path", [])
    names = [hop.get("system_name", "") for hop in path if hop.get("system_name")]

    if not names:
        return base_url

    # Dotlan uses : separator
    route_str = ":".join(names)
    return base_url + route_str


def export_to_eveeye_url(route_data: dict[str, Any]) -> str:
    """
    Generate EVE Eye route URL.

    EVE Eye uses format: https://eveeye.com/?route=System1:System2
    """
    base_url = "https://eveeye.com/"
    path = route_data.get("path", [])

    if len(path) < 2:
        return base_url

    from_sys = path[0].get("system_name", "")
    to_sys = path[-1].get("system_name", "")

    return f"{base_url}?route={from_sys}:{to_sys}"


def export_to_json(route_data: dict[str, Any], pretty: bool = False) -> str:
    """
    Export route to JSON string.

    Args:
        route_data: Route data
        pretty: If True, format with indentation

    Returns:
        JSON string
    """
    if pretty:
        return json.dumps(route_data, indent=2, default=str)
    return json.dumps(route_data, default=str)


def create_route_hash(route_data: dict[str, Any]) -> str:
    """
    Create a deterministic hash of a route for comparison.

    Useful for detecting if two routes are identical.
    """
    # Use only route-defining fields
    key_data = {
        "from": route_data.get("from_system", ""),
        "to": route_data.get("to_system", ""),
        "profile": route_data.get("profile", ""),
        "path": [h.get("system_name", "") for h in route_data.get("path", [])],
    }
    data_str = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(data_str.encode()).hexdigest()[:12]
