"""
API Integration Examples for EVE Map Visualization

This file demonstrates various ways to integrate with the EVE Map API.
All examples assume the backend server is running on http://localhost:8000
"""

import requests


def example_1_list_systems():
    """Example 1: List all systems in the universe."""
    print("=" * 70)
    print("Example 1: List All Systems")
    print("=" * 70)

    response = requests.get("http://localhost:8000/systems/")
    systems = response.json()

    print(f"\nTotal systems: {len(systems)}")
    print("\nFirst 5 systems:")
    for system in systems[:5]:
        print(f"  - {system['name']}: {system['security_status']} sec, {system['region']}")
    print()


def example_2_get_risk_report():
    """Example 2: Get risk assessment for a specific system."""
    print("=" * 70)
    print("Example 2: Get Risk Report for Jita")
    print("=" * 70)

    response = requests.get("http://localhost:8000/systems/Jita/risk")
    risk_data = response.json()

    print(f"\nSystem: {risk_data['system']}")
    print(f"Risk Score: {risk_data['risk_score']:.2f}")
    print(f"Classification: {risk_data['classification']}")
    print("\nRisk Factors:")
    for factor, value in risk_data["factors"].items():
        print(f"  - {factor}: {value:.2f}")
    print()


def example_3_calculate_route():
    """Example 3: Calculate route between systems with risk awareness."""
    print("=" * 70)
    print("Example 3: Calculate Route from Jita to Niarja")
    print("=" * 70)

    params = {"from": "Jita", "to": "Niarja", "profile": "safer"}

    response = requests.get("http://localhost:8000/map/route", params=params)
    route = response.json()

    # Extract system names from route
    system_names = [hop["system"] for hop in route["path"]]

    print(f"\nRoute Profile: {params['profile']}")
    print(f"Route: {' -> '.join(system_names)}")
    print(f"Total Jumps: {len(route['path']) - 1}")
    print(f"Total Risk: {route['total_risk']:.2f}")

    print("\nDetailed Hops:")
    for i, hop in enumerate(route["path"]):
        print(f"  {i + 1}. {hop['system']} (risk: {hop['risk']:.2f})")
    print()


def example_4_get_neighbors():
    """Example 4: Get neighboring systems."""
    print("=" * 70)
    print("Example 4: Get Neighbors of Jita")
    print("=" * 70)

    response = requests.get("http://localhost:8000/systems/Jita/neighbors")
    neighbors = response.json()

    print(f"\nJita has {len(neighbors)} neighboring systems:")
    for gate in neighbors:
        print(f"  - {gate['to_system']} (distance: {gate['distance']})")
    print()


def example_5_get_map_config():
    """Example 5: Get complete map configuration."""
    print("=" * 70)
    print("Example 5: Get Map Configuration")
    print("=" * 70)

    response = requests.get("http://localhost:8000/map/config")
    config = response.json()

    print(f"\nTotal Systems: {len(config['systems'])}")
    print(f"Total Gates: {len(config['gates'])}")

    # Count systems by security
    high_sec = sum(1 for s in config["systems"].values() if s["security_status"] >= 0.5)
    low_sec = sum(1 for s in config["systems"].values() if 0.0 < s["security_status"] < 0.5)
    null_sec = sum(1 for s in config["systems"].values() if s["security_status"] <= 0.0)

    print("\nSecurity Breakdown:")
    print(f"  - High Sec: {high_sec} systems")
    print(f"  - Low Sec: {low_sec} systems")
    print(f"  - Null Sec: {null_sec} systems")

    print("\nRisk Profiles Available:")
    for profile_name in config["risk_config"]["profiles"].keys():
        print(f"  - {profile_name}")
    print()


def example_6_compare_routes():
    """Example 6: Compare different routing profiles."""
    print("=" * 70)
    print("Example 6: Compare Routing Profiles (Jita to Niarja)")
    print("=" * 70)

    profiles = ["shortest", "safer", "paranoid"]

    print()
    for profile in profiles:
        params = {"from": "Jita", "to": "Niarja", "profile": profile}

        try:
            response = requests.get("http://localhost:8000/map/route", params=params)
            route = response.json()

            system_names = [hop["system"] for hop in route["path"]]

            print(f"{profile.upper()} Profile:")
            print(f"  Route: {' -> '.join(system_names)}")
            print(f"  Jumps: {len(route['path']) - 1}")
            print(f"  Total Risk: {route['total_risk']:.2f}")
            print()
        except Exception as e:
            print(f"{profile.upper()} Profile: Error - {e}\n")


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

async def get_system_info(system_name: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'http://localhost:8000/systems/{system_name}/risk'
        )
        return response.json()

async def main():
    # Get multiple systems concurrently
    tasks = [
        get_system_info('Jita'),
        get_system_info('Perimeter'),
        get_system_info('Niarja')
    ]
    results = await asyncio.gather(*tasks)

    for result in results:
        print(f"{result['system']}: Risk {result['risk_score']:.2f}")

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
        response = requests.get("http://localhost:8000/systems/NonExistentSystem/risk")
        response.raise_for_status()  # Raise exception for 4xx/5xx status codes
        data = response.json()
        print(f"Risk data: {data}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(f"Error detail: {e.response.json()}")
    except requests.exceptions.ConnectionError:
        print("Could not connect to API. Is the server running?")
    except requests.exceptions.Timeout:
        print("Request timed out")
    except Exception as e:
        print(f"Unexpected error: {e}")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("*" * 70)
    print("EVE MAP VISUALIZATION - API INTEGRATION EXAMPLES")
    print("*" * 70)
    print("\nMake sure the backend server is running:")
    print("  cd backend && uvicorn app.main:app --reload")
    print("\n" + "*" * 70)
    print()

    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            print("✓ Server is running!\n")
        else:
            print("✗ Server returned unexpected status\n")
            return
    except requests.exceptions.RequestException:
        print("✗ Cannot connect to server at http://localhost:8000")
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
