#!/usr/bin/env python3
"""Generate universe.json from EVE SDE CSV data."""

import csv
import json
from datetime import datetime
from pathlib import Path


def get_security_category(security: float) -> str:
    """Determine security category from security status."""
    if security >= 0.5:
        return "highsec"
    elif security > 0.0:
        return "lowsec"
    else:
        return "nullsec"


def main():
    # Load regions
    regions = {}
    with open("/tmp/mapRegions.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            regions[int(row["regionID"])] = row["regionName"]

    # Load constellations
    constellations = {}
    with open("/tmp/mapConstellations.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            constellations[int(row["constellationID"])] = {
                "name": row["constellationName"],
                "region_id": int(row["regionID"]),
            }

    # Load solar systems
    systems = {}
    with open("/tmp/mapSolarSystems.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            system_id = int(row["solarSystemID"])
            region_id = int(row["regionID"])
            constellation_id = int(row["constellationID"])
            security = float(row["security"])

            # Skip wormhole systems (region IDs 11000000+)
            if region_id >= 11000000:
                continue

            # Skip Abyssal/Pochven placeholder regions
            if region_id >= 12000000:
                continue

            # Get region and constellation names
            region_name = regions.get(region_id, "Unknown")
            constellation_data = constellations.get(constellation_id, {})
            constellation_name = constellation_data.get("name", "Unknown")

            systems[row["solarSystemName"]] = {
                "id": system_id,
                "region_id": region_id,
                "region_name": region_name,
                "constellation_id": constellation_id,
                "constellation_name": constellation_name,
                "security": round(security, 2),
                "category": get_security_category(security),
                "position": {
                    "x": float(row["x"]) / 1e16,  # Normalize coordinates
                    "y": float(row["z"]) / 1e16,  # Use Z as Y for 2D map
                },
            }

    # Load stargate connections
    gates = []
    seen_connections = set()

    with open("/tmp/mapSolarSystemJumps.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            from_id = int(row["fromSolarSystemID"])
            to_id = int(row["toSolarSystemID"])

            # Create sorted tuple to avoid duplicates
            connection = tuple(sorted([from_id, to_id]))
            if connection in seen_connections:
                continue
            seen_connections.add(connection)

            # Find system names
            from_name = None
            to_name = None
            for name, data in systems.items():
                if data["id"] == from_id:
                    from_name = name
                if data["id"] == to_id:
                    to_name = name

            if from_name and to_name:
                gates.append({"from": from_name, "to": to_name, "distance": 1})

    # Build output
    universe = {
        "metadata": {
            "version": "1.0.0",
            "source": "eve_sde_fuzzwork",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "system_count": len(systems),
            "gate_count": len(gates),
        },
        "systems": systems,
        "gates": gates,
    }

    # Write output
    output_path = Path(__file__).parent.parent / "backend" / "app" / "data" / "universe.json"
    with open(output_path, "w") as f:
        json.dump(universe, f, indent=2)

    print("Generated universe.json:")
    print(f"  - {len(systems)} solar systems")
    print(f"  - {len(gates)} stargate connections")
    print(f"  - Saved to {output_path}")


if __name__ == "__main__":
    main()
