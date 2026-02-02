"""
API Integration Examples for EVE Gatekeeper

This file demonstrates various ways to integrate with the EVE Gatekeeper API.
All examples assume the backend server is running on http://localhost:8000

API Base URL: http://localhost:8000/api/v1/
Documentation: http://localhost:8000/docs
"""

import requests

BASE_URL = "http://localhost:8000/api/v1"


def example_1_list_systems():
    """Example 1: List all systems in the universe with pagination."""
    print("=" * 70)
    print("Example 1: List All Systems (Paginated)")
    print("=" * 70)

    # Get first page with pagination
    response = requests.get(f"{BASE_URL}/systems/", params={"page": 1, "page_size": 20})
    data = response.json()

    print(f"\nTotal systems: {data['pagination']['total']}")
    print(f"Page {data['pagination']['page']} of {data['pagination']['total_pages']}")
    print("\nFirst 5 systems:")
    for system in data["items"][:5]:
        print(f"  - {system['name']}: {system['security']:.2f} sec, {system['region_name']}")

    # Filter by category
    print("\n\nFiltering by category (lowsec):")
    response = requests.get(
        f"{BASE_URL}/systems/", params={"category": "lowsec", "page": 1, "page_size": 5}
    )
    data = response.json()
    print(f"Found {data['pagination']['total']} lowsec systems")
    for system in data["items"]:
        print(f"  - {system['name']}: {system['security']:.2f} sec")
    print()


def example_2_get_risk_report():
    """Example 2: Get risk assessment for a specific system."""
    print("=" * 70)
    print("Example 2: Get Risk Report for Rancer (with live zKill data)")
    print("=" * 70)

    # Get risk with live zKillboard data
    response = requests.get(f"{BASE_URL}/systems/Rancer/risk", params={"live": True})
    risk_data = response.json()

    print(f"\nSystem: {risk_data['system_name']}")
    print(f"Risk Score: {risk_data['score']:.1f}/100")
    print(f"Danger Level: {risk_data['danger_level']}")

    print("\nRisk Breakdown:")
    breakdown = risk_data["breakdown"]
    print(f"  - Security Component: {breakdown['security_component']:.1f}")
    print(f"  - Kills Component: {breakdown['kills_component']:.1f}")
    print(f"  - Pods Component: {breakdown['pods_component']:.1f}")

    if risk_data.get("zkill_stats"):
        print("\nzKillboard Stats (last 24h):")
        stats = risk_data["zkill_stats"]
        print(f"  - Recent Kills: {stats.get('kills', 0)}")
        print(f"  - Recent Pods: {stats.get('pods', 0)}")

    # Get risk with ship profile
    print("\n\nRisk for Hauler in same system:")
    response = requests.get(
        f"{BASE_URL}/systems/Rancer/risk", params={"live": True, "ship_profile": "hauler"}
    )
    hauler_risk = response.json()
    print(f"  Hauler Risk Score: {hauler_risk['score']:.1f}/100 (profile: hauler)")
    print()


def example_3_calculate_route():
    """Example 3: Calculate route between systems with risk awareness."""
    print("=" * 70)
    print("Example 3: Calculate Route from Jita to Amarr")
    print("=" * 70)

    params = {"from": "Jita", "to": "Amarr", "profile": "safer"}

    response = requests.get(f"{BASE_URL}/route/", params=params)
    route = response.json()

    print(f"\nRoute Profile: {route['profile']}")
    print(f"Total Jumps: {route['total_jumps']}")
    print(f"Max Risk: {route['max_risk']:.1f}")
    print(f"Average Risk: {route['avg_risk']:.1f}")

    print("\nRoute Path (first 10 systems):")
    for i, hop in enumerate(route["path"][:10]):
        print(
            f"  {i + 1}. {hop['system_name']} "
            f"(risk: {hop['risk_score']:.1f}, type: {hop['connection_type']})"
        )
    if len(route["path"]) > 10:
        print(f"  ... and {len(route['path']) - 10} more systems")
    print()


def example_4_get_neighbors():
    """Example 4: Get neighboring systems."""
    print("=" * 70)
    print("Example 4: Get Neighbors of Jita")
    print("=" * 70)

    response = requests.get(f"{BASE_URL}/systems/Jita/neighbors")
    neighbors = response.json()

    print(f"\nJita has {len(neighbors)} neighboring systems:")
    for neighbor in neighbors:
        print(f"  - {neighbor}")
    print()


def example_5_get_map_config():
    """Example 5: Get complete map configuration."""
    print("=" * 70)
    print("Example 5: Get Map Configuration")
    print("=" * 70)

    response = requests.get(f"{BASE_URL}/route/config")
    config = response.json()

    print(f"\nTotal Systems: {len(config['systems'])}")

    # Count systems by security category
    categories = {}
    for sys in config["systems"].values():
        cat = sys["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\nSecurity Breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat.title()}: {count} systems")

    print("\nRouting Profiles Available:")
    for profile_name in config["routing_profiles"]:
        print(f"  - {profile_name}")
    print()


def example_6_compare_routes():
    """Example 6: Compare different routing profiles using the compare endpoint."""
    print("=" * 70)
    print("Example 6: Compare Routing Profiles (Jita to HED-GP)")
    print("=" * 70)

    # Use the compare endpoint for side-by-side comparison
    compare_request = {
        "from_system": "Jita",
        "to_system": "HED-GP",
        "profiles": ["shortest", "safer", "paranoid"],
        "avoid": [],
        "use_bridges": False,
        "use_thera": False,
        "use_pochven": False,
    }

    response = requests.post(f"{BASE_URL}/route/compare", json=compare_request)
    comparison = response.json()

    print(f"\nRoute: {comparison['from_system']} -> {comparison['to_system']}")
    print("\nProfile Comparison:")

    for route in comparison["routes"]:
        print(f"\n  {route['profile'].upper()}:")
        print(f"    Jumps: {route['total_jumps']}")
        print(f"    Max Risk: {route['max_risk']:.1f}")
        print(f"    Avg Risk: {route['avg_risk']:.1f}")
        print(
            f"    Security: {route['highsec_jumps']} highsec, "
            f"{route['lowsec_jumps']} lowsec, {route['nullsec_jumps']} nullsec"
        )

    print(f"\nRecommendation: {comparison['recommendation']}")
    print()


def example_7_async_integration():
    """Example 7: Async integration using httpx (for async applications)."""
    print("=" * 70)
    print("Example 7: Async API Integration (requires httpx)")
    print("=" * 70)

    print("\nFor async applications, use httpx.AsyncClient:")
    print(
        """
import httpx
import asyncio

BASE_URL = "http://localhost:8000/api/v1"

async def get_system_risk(system_name: str, ship_profile: str = None):
    async with httpx.AsyncClient() as client:
        params = {"live": True}
        if ship_profile:
            params["ship_profile"] = ship_profile
        response = await client.get(
            f'{BASE_URL}/systems/{system_name}/risk',
            params=params
        )
        return response.json()

async def main():
    # Get risk for multiple systems concurrently
    systems = ['Jita', 'Rancer', 'HED-GP']
    tasks = [get_system_risk(s) for s in systems]
    results = await asyncio.gather(*tasks)

    for result in results:
        print(f"{result['system_name']}: "
              f"Risk {result['score']:.1f}, "
              f"Danger: {result['danger_level']}")

# Run the async code
asyncio.run(main())
    """
    )
    print()


def example_8_error_handling():
    """Example 8: Proper error handling."""
    print("=" * 70)
    print("Example 8: Error Handling Best Practices")
    print("=" * 70)

    print("\nTrying to get info for non-existent system...")

    try:
        response = requests.get(f"{BASE_URL}/systems/NonExistentSystem/risk")
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes
        data = response.json()
        print(f"Risk data: {data}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}")
        error_detail = e.response.json()
        print(f"Error detail: {error_detail.get('detail', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to API. Is the server running?")
    except requests.exceptions.Timeout:
        print("Request timed out")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print("\nTrying invalid routing profile...")

    try:
        response = requests.get(
            f"{BASE_URL}/route/", params={"from": "Jita", "to": "Amarr", "profile": "invalid"}
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}")
        error_detail = e.response.json()
        print(f"Error detail: {error_detail.get('detail', 'Unknown error')}")
    print()


def example_9_ship_profiles():
    """Example 9: List available ship profiles for risk calculation."""
    print("=" * 70)
    print("Example 9: Available Ship Profiles")
    print("=" * 70)

    response = requests.get(f"{BASE_URL}/systems/profiles/ships")
    data = response.json()

    print("\nShip profiles adjust risk scores based on ship vulnerability:")
    for profile in data["profiles"]:
        print(f"\n  {profile['name'].upper()}:")
        print(f"    {profile['description']}")
        print(f"    Highsec multiplier: {profile['highsec_multiplier']}")
        print(f"    Lowsec multiplier: {profile['lowsec_multiplier']}")
        print(f"    Nullsec multiplier: {profile['nullsec_multiplier']}")
    print()


def example_10_route_with_options():
    """Example 10: Advanced routing with avoidance and special connections."""
    print("=" * 70)
    print("Example 10: Advanced Routing Options")
    print("=" * 70)

    # Route with systems to avoid
    print("\nRoute avoiding specific systems:")
    params = {
        "from": "Jita",
        "to": "Amarr",
        "profile": "shortest",
        "avoid": ["Niarja", "Uedama"],  # Notorious gank systems
    }
    response = requests.get(f"{BASE_URL}/route/", params=params)
    route = response.json()
    print(f"  Jumps (avoiding Niarja, Uedama): {route['total_jumps']}")

    # Route using Thera wormhole shortcuts
    print("\nRoute using Thera wormhole connections:")
    params = {"from": "Jita", "to": "HED-GP", "profile": "shortest", "thera": True}
    response = requests.get(f"{BASE_URL}/route/", params=params)
    route = response.json()
    print(f"  Jumps with Thera: {route['total_jumps']}")
    print(f"  Thera connections used: {route['thera_used']}")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("*" * 70)
    print("EVE GATEKEEPER - API INTEGRATION EXAMPLES")
    print("*" * 70)
    print("\nMake sure the backend server is running:")
    print("  cd backend && uvicorn app.main:app --reload")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("\n" + "*" * 70)
    print()

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("Server is running!\n")
        else:
            print("Server returned unexpected status\n")
            return
    except requests.exceptions.RequestException:
        print("Cannot connect to server at http://localhost:8000")
        print("  Please start the backend server first.\n")
        return

    # Run examples
    try:
        example_1_list_systems()
        example_2_get_risk_report()
        example_3_calculate_route()
        example_4_get_neighbors()
        example_5_get_map_config()
        example_6_compare_routes()
        example_7_async_integration()
        example_8_error_handling()
        example_9_ship_profiles()
        example_10_route_with_options()
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "*" * 70)
    print("All examples completed!")
    print("*" * 70)
    print()


if __name__ == "__main__":
    main()
