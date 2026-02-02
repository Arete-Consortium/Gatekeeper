"""
EVE Gatekeeper Python Client Library

A reusable Python client for the EVE Gatekeeper API.
Provides both synchronous and asynchronous interfaces.

Usage:
    # Synchronous
    with GatekeeperClient("http://localhost:8000") as client:
        route = client.get_route("Jita", "Amarr", profile="safer")
        risk = client.get_risk("Rancer", live=True)

    # Asynchronous
    async with AsyncGatekeeperClient("http://localhost:8000") as client:
        route = await client.get_route("Jita", "Amarr")
        risks = await client.get_risks(["Jita", "Rancer", "HED-GP"])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Result of a route calculation."""

    from_system: str
    to_system: str
    profile: str
    total_jumps: int
    total_cost: float
    max_risk: float
    avg_risk: float
    path: list[dict[str, Any]]
    bridges_used: int
    thera_used: int
    pochven_used: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RouteResult:
        """Create RouteResult from API response."""
        return cls(
            from_system=data["from_system"],
            to_system=data["to_system"],
            profile=data["profile"],
            total_jumps=data["total_jumps"],
            total_cost=data["total_cost"],
            max_risk=data["max_risk"],
            avg_risk=data["avg_risk"],
            path=data["path"],
            bridges_used=data.get("bridges_used", 0),
            thera_used=data.get("thera_used", 0),
            pochven_used=data.get("pochven_used", 0),
        )


@dataclass
class RiskReport:
    """Risk assessment for a system."""

    system_name: str
    score: float
    danger_level: str
    breakdown: dict[str, float]
    zkill_stats: dict[str, Any] | None
    ship_profile: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RiskReport:
        """Create RiskReport from API response."""
        return cls(
            system_name=data["system_name"],
            score=data["score"],
            danger_level=data["danger_level"],
            breakdown=data["breakdown"],
            zkill_stats=data.get("zkill_stats"),
            ship_profile=data.get("ship_profile"),
        )


class GatekeeperError(Exception):
    """Base exception for Gatekeeper client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SystemNotFoundError(GatekeeperError):
    """Raised when a system is not found."""

    pass


class InvalidProfileError(GatekeeperError):
    """Raised when an invalid routing profile is specified."""

    pass


class ConnectionError(GatekeeperError):
    """Raised when connection to API fails."""

    pass


class GatekeeperClient:
    """
    Synchronous client for EVE Gatekeeper API.

    Example:
        with GatekeeperClient("http://localhost:8000") as client:
            route = client.get_route("Jita", "Amarr")
            print(f"Route takes {route.total_jumps} jumps")
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the client.

        Args:
            base_url: Base URL of the API (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
        """
        import httpx

        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def __enter__(self) -> GatekeeperClient:
        import httpx

        self._client = httpx.Client(timeout=self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            self._client.close()
            self._client = None

    @property
    def client(self):
        """Get the HTTP client, creating one if needed."""
        import httpx

        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _handle_error(self, response) -> None:
        """Handle error responses from the API."""
        if response.status_code == 404:
            detail = response.json().get("detail", "Not found")
            if "not found" in detail.lower():
                raise SystemNotFoundError(detail, status_code=404)
            raise GatekeeperError(detail, status_code=404)
        elif response.status_code == 400:
            detail = response.json().get("detail", "Bad request")
            if "profile" in detail.lower():
                raise InvalidProfileError(detail, status_code=400)
            raise GatekeeperError(detail, status_code=400)
        elif response.status_code >= 500:
            raise GatekeeperError(
                f"Server error: {response.status_code}", status_code=response.status_code
            )
        elif response.status_code >= 400:
            detail = response.json().get("detail", f"HTTP {response.status_code}")
            raise GatekeeperError(detail, status_code=response.status_code)

    def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            response = self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    def get_route(
        self,
        from_system: str,
        to_system: str,
        profile: str = "shortest",
        avoid: list[str] | None = None,
        use_bridges: bool = False,
        use_thera: bool = False,
        use_pochven: bool = False,
    ) -> RouteResult:
        """
        Calculate a route between two systems.

        Args:
            from_system: Origin system name
            to_system: Destination system name
            profile: Routing profile ("shortest", "safer", "paranoid")
            avoid: List of system names to avoid
            use_bridges: Use Ansiblex jump bridges
            use_thera: Use Thera wormhole shortcuts
            use_pochven: Use Pochven filament routing

        Returns:
            RouteResult with route details

        Raises:
            SystemNotFoundError: If system not found
            InvalidProfileError: If profile is invalid
            GatekeeperError: For other API errors
        """
        params = {
            "from": from_system,
            "to": to_system,
            "profile": profile,
            "bridges": use_bridges,
            "thera": use_thera,
            "pochven": use_pochven,
        }
        if avoid:
            params["avoid"] = avoid

        response = self.client.get(f"{self.api_url}/route/", params=params)

        if response.status_code != 200:
            self._handle_error(response)

        return RouteResult.from_dict(response.json())

    def get_risk(
        self,
        system_name: str,
        live: bool = True,
        ship_profile: str | None = None,
    ) -> RiskReport:
        """
        Get risk assessment for a system.

        Args:
            system_name: Name of the system
            live: Fetch fresh data from zKillboard
            ship_profile: Ship profile for adjusted risk

        Returns:
            RiskReport with risk details

        Raises:
            SystemNotFoundError: If system not found
            InvalidProfileError: If ship profile is invalid
            GatekeeperError: For other API errors
        """
        params = {"live": live}
        if ship_profile:
            params["ship_profile"] = ship_profile

        response = self.client.get(f"{self.api_url}/systems/{system_name}/risk", params=params)

        if response.status_code != 200:
            self._handle_error(response)

        return RiskReport.from_dict(response.json())

    def get_system(self, system_name: str) -> dict[str, Any]:
        """
        Get system details.

        Args:
            system_name: Name of the system

        Returns:
            Dictionary with system details

        Raises:
            SystemNotFoundError: If system not found
        """
        response = self.client.get(f"{self.api_url}/systems/{system_name}")

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    def get_neighbors(self, system_name: str) -> list[str]:
        """
        Get neighboring systems connected via stargates.

        Args:
            system_name: Name of the system

        Returns:
            List of neighboring system names

        Raises:
            SystemNotFoundError: If system not found
        """
        response = self.client.get(f"{self.api_url}/systems/{system_name}/neighbors")

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    def list_systems(
        self,
        page: int = 1,
        page_size: int = 100,
        category: str | None = None,
        region_name: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """
        List systems with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            category: Filter by category (highsec, lowsec, nullsec, wh)
            region_name: Filter by region name
            search: Search by system name (partial match)

        Returns:
            Dictionary with "items" and "pagination" keys
        """
        params = {"page": page, "page_size": page_size}
        if category:
            params["category"] = category
        if region_name:
            params["region_name"] = region_name
        if search:
            params["search"] = search

        response = self.client.get(f"{self.api_url}/systems/", params=params)

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    def compare_routes(
        self,
        from_system: str,
        to_system: str,
        profiles: list[str] | None = None,
        avoid: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Compare routes using different profiles.

        Args:
            from_system: Origin system name
            to_system: Destination system name
            profiles: List of profiles to compare (default: all)
            avoid: List of systems to avoid

        Returns:
            Comparison result with routes and recommendation
        """
        if profiles is None:
            profiles = ["shortest", "safer", "paranoid"]

        request_body = {
            "from_system": from_system,
            "to_system": to_system,
            "profiles": profiles,
            "avoid": avoid or [],
            "use_bridges": False,
            "use_thera": False,
            "use_pochven": False,
        }

        response = self.client.post(f"{self.api_url}/route/compare", json=request_body)

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    def get_status(self) -> dict[str, Any]:
        """Get API status and health information."""
        response = self.client.get(f"{self.api_url}/status/")

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()


class AsyncGatekeeperClient:
    """
    Asynchronous client for EVE Gatekeeper API.

    Example:
        async with AsyncGatekeeperClient("http://localhost:8000") as client:
            route = await client.get_route("Jita", "Amarr")
            risks = await client.get_risks(["Jita", "Rancer", "HED-GP"])
    """

    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize the async client.

        Args:
            base_url: Base URL of the API (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.timeout = timeout
        self._client = None

    async def __aenter__(self) -> AsyncGatekeeperClient:
        import httpx

        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self):
        """Get the HTTP client."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _handle_error(self, response) -> None:
        """Handle error responses from the API."""
        if response.status_code == 404:
            detail = response.json().get("detail", "Not found")
            if "not found" in detail.lower():
                raise SystemNotFoundError(detail, status_code=404)
            raise GatekeeperError(detail, status_code=404)
        elif response.status_code == 400:
            detail = response.json().get("detail", "Bad request")
            if "profile" in detail.lower():
                raise InvalidProfileError(detail, status_code=400)
            raise GatekeeperError(detail, status_code=400)
        elif response.status_code >= 500:
            raise GatekeeperError(
                f"Server error: {response.status_code}", status_code=response.status_code
            )
        elif response.status_code >= 400:
            detail = response.json().get("detail", f"HTTP {response.status_code}")
            raise GatekeeperError(detail, status_code=response.status_code)

    async def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    async def get_route(
        self,
        from_system: str,
        to_system: str,
        profile: str = "shortest",
        avoid: list[str] | None = None,
        use_bridges: bool = False,
        use_thera: bool = False,
        use_pochven: bool = False,
    ) -> RouteResult:
        """Calculate a route between two systems."""
        params = {
            "from": from_system,
            "to": to_system,
            "profile": profile,
            "bridges": use_bridges,
            "thera": use_thera,
            "pochven": use_pochven,
        }
        if avoid:
            params["avoid"] = avoid

        response = await self.client.get(f"{self.api_url}/route/", params=params)

        if response.status_code != 200:
            self._handle_error(response)

        return RouteResult.from_dict(response.json())

    async def get_risk(
        self,
        system_name: str,
        live: bool = True,
        ship_profile: str | None = None,
    ) -> RiskReport:
        """Get risk assessment for a system."""
        params = {"live": live}
        if ship_profile:
            params["ship_profile"] = ship_profile

        response = await self.client.get(
            f"{self.api_url}/systems/{system_name}/risk", params=params
        )

        if response.status_code != 200:
            self._handle_error(response)

        return RiskReport.from_dict(response.json())

    async def get_risks(
        self,
        system_names: list[str],
        live: bool = True,
        ship_profile: str | None = None,
    ) -> list[RiskReport]:
        """
        Get risk assessments for multiple systems concurrently.

        Args:
            system_names: List of system names
            live: Fetch fresh data from zKillboard
            ship_profile: Ship profile for adjusted risk

        Returns:
            List of RiskReport objects
        """
        import asyncio

        tasks = [self.get_risk(name, live=live, ship_profile=ship_profile) for name in system_names]
        return await asyncio.gather(*tasks)

    async def get_system(self, system_name: str) -> dict[str, Any]:
        """Get system details."""
        response = await self.client.get(f"{self.api_url}/systems/{system_name}")

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()

    async def get_neighbors(self, system_name: str) -> list[str]:
        """Get neighboring systems connected via stargates."""
        response = await self.client.get(f"{self.api_url}/systems/{system_name}/neighbors")

        if response.status_code != 200:
            self._handle_error(response)

        return response.json()


# Example usage
if __name__ == "__main__":
    import asyncio

    # Synchronous example
    print("Synchronous Example:")
    print("-" * 40)
    try:
        with GatekeeperClient("http://localhost:8000") as client:
            if client.health_check():
                print("API is healthy")

                # Get a route
                route = client.get_route("Jita", "Amarr", profile="safer")
                print(f"Route from {route.from_system} to {route.to_system}:")
                print(f"  Jumps: {route.total_jumps}")
                print(f"  Max Risk: {route.max_risk:.1f}")

                # Get risk for a dangerous system
                risk = client.get_risk("Rancer", live=False)
                print(f"\nRisk for {risk.system_name}:")
                print(f"  Score: {risk.score:.1f}")
                print(f"  Danger: {risk.danger_level}")
            else:
                print("API is not available")
    except ConnectionError as e:
        print(f"Could not connect: {e}")
    except GatekeeperError as e:
        print(f"API error: {e}")

    # Async example
    print("\n\nAsynchronous Example:")
    print("-" * 40)

    async def async_demo():
        try:
            async with AsyncGatekeeperClient("http://localhost:8000") as client:
                if await client.health_check():
                    # Get multiple risks concurrently
                    systems = ["Jita", "Rancer", "HED-GP"]
                    risks = await client.get_risks(systems, live=False)

                    print("Concurrent risk check:")
                    for risk in risks:
                        print(f"  {risk.system_name}: {risk.score:.1f} ({risk.danger_level})")
                else:
                    print("API is not available")
        except GatekeeperError as e:
            print(f"API error: {e}")

    asyncio.run(async_demo())
