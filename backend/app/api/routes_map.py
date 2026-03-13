import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query

from ..models.route import RouteResponse
from ..services.data_loader import load_risk_config, load_universe
from ..services.risk_engine import compute_risk, risk_to_color
from ..services.routing import compute_route

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ESI_BASE = "https://esi.evetech.net/latest"
EVE_SCOUT_API = "https://api.eve-scout.com/v2/public/signatures"


@router.get("/config")
async def map_config() -> dict:
    universe = load_universe()
    cfg = load_risk_config()

    systems_payload = {}
    for name, sys in universe.systems.items():
        risk = compute_risk(name)
        color = risk_to_color(risk.score)
        systems_payload[name] = {
            "id": sys.id,
            "region_id": sys.region_id,
            "region_name": sys.region_name,
            "constellation_id": sys.constellation_id,
            "constellation_name": sys.constellation_name,
            "security": sys.security,
            "category": sys.category,
            "position": sys.position.dict(),
            "risk_score": risk.score,
            "risk_color": color,
            # SDE enhancements
            "hub": sys.hub,
            "border": sys.border,
            "corridor": sys.corridor,
            "fringe": sys.fringe,
            "spectral_class": sys.spectral_class,
            "npc_stations": sys.npc_stations,
        }

    gates_payload = [
        {"from_system": g.from_system, "to_system": g.to_system} for g in universe.gates
    ]

    # Load landmarks
    landmarks = []
    landmarks_file = DATA_DIR / "landmarks.json"
    if landmarks_file.exists():
        with landmarks_file.open() as f:
            landmarks = json.load(f)

    # Load factions
    factions = {}
    factions_file = DATA_DIR / "factions.json"
    if factions_file.exists():
        with factions_file.open() as f:
            factions = json.load(f)

    return {
        "metadata": universe.metadata.dict(),
        "systems": systems_payload,
        "gates": gates_payload,
        "layers": cfg.map_layers,
        "landmarks": landmarks,
        "factions": factions,
    }


@router.get("/sovereignty")
async def get_sovereignty() -> dict:
    """Fetch current sovereignty map from ESI."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{ESI_BASE}/sovereignty/map/")
            resp.raise_for_status()
            sov_data = resp.json()
        except httpx.HTTPError:
            logger.exception("Failed to fetch sovereignty data from ESI")
            raise HTTPException(503, "ESI sovereignty data unavailable") from None

    # Build system_id -> sov info
    sov_map = {}
    alliance_ids = set()
    faction_ids = set()
    for entry in sov_data:
        sid = entry.get("system_id")
        if not sid:
            continue
        sov_map[str(sid)] = {
            "alliance_id": entry.get("alliance_id"),
            "corporation_id": entry.get("corporation_id"),
            "faction_id": entry.get("faction_id"),
        }
        if entry.get("alliance_id"):
            alliance_ids.add(entry["alliance_id"])
        if entry.get("faction_id"):
            faction_ids.add(entry["faction_id"])

    # Resolve alliance names (batch)
    alliance_names = {}
    if alliance_ids:
        try:
            resp = await client_post_ids(list(alliance_ids)[:1000])
            for item in resp:
                alliance_names[str(item["id"])] = {
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                }
        except Exception:
            logger.warning("Failed to resolve alliance names")

    return {
        "sovereignty": sov_map,
        "alliances": alliance_names,
    }


async def client_post_ids(ids: list[int]) -> list[dict]:
    """Resolve IDs to names via ESI POST /universe/names/."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{ESI_BASE}/universe/names/",
            json=ids,
        )
        resp.raise_for_status()
        return resp.json()


@router.get("/fw")
async def get_fw_systems() -> dict:
    """Fetch faction warfare system status from ESI."""
    from ..services.fw_cache import ensure_fw_cache

    # Refresh FW cache opportunistically (keeps pirate suppression data fresh)
    await ensure_fw_cache()

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{ESI_BASE}/fw/systems/")
            resp.raise_for_status()
            fw_data = resp.json()
        except httpx.HTTPError:
            logger.exception("Failed to fetch FW data from ESI")
            raise HTTPException(503, "ESI faction warfare data unavailable") from None

    fw_systems = {}
    for entry in fw_data:
        sid = entry.get("solar_system_id")
        if not sid:
            continue
        fw_systems[str(sid)] = {
            "occupier_faction_id": entry.get("occupier_faction_id"),
            "owner_faction_id": entry.get("owner_faction_id"),
            "contested": entry.get("contested", "uncontested"),
            "victory_points": entry.get("victory_points", 0),
            "victory_points_threshold": entry.get("victory_points_threshold", 0),
        }

    return {"fw_systems": fw_systems}


@router.get("/sovereignty/structures")
async def get_sov_structures() -> dict:
    """Fetch sovereignty structures (iHubs, ADM levels) from ESI."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"{ESI_BASE}/sovereignty/structures/")
            resp.raise_for_status()
            structures = resp.json()
        except httpx.HTTPError:
            logger.exception("Failed to fetch sov structures from ESI")
            raise HTTPException(503, "ESI sovereignty structures unavailable") from None

    # Group by system
    system_structures = {}
    for s in structures:
        sid = str(s.get("solar_system_id", 0))
        if sid == "0":
            continue
        if sid not in system_structures:
            system_structures[sid] = []
        system_structures[sid].append(
            {
                "alliance_id": s.get("alliance_id"),
                "structure_type_id": s.get("structure_type_id"),
                "vulnerability_occupancy_level": s.get("vulnerability_occupancy_level"),
                "vulnerable_start_time": s.get("vulnerable_start_time"),
                "vulnerable_end_time": s.get("vulnerable_end_time"),
            }
        )

    return {"structures": system_structures}


@router.get("/thera")
async def get_thera_connections() -> dict:
    """Fetch current Thera/Turnur/Zarzakh connections from EVE Scout."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(EVE_SCOUT_API)
            resp.raise_for_status()
            connections = resp.json()
        except httpx.HTTPError:
            logger.exception("Failed to fetch EVE Scout data")
            raise HTTPException(503, "EVE Scout data unavailable") from None

    result = []
    for conn in connections:
        result.append(
            {
                "id": conn.get("id"),
                "source_system_id": conn.get("out_system_id"),
                "source_system_name": conn.get("out_system_name"),
                "dest_system_id": conn.get("in_system_id"),
                "dest_system_name": conn.get("in_system_name"),
                "dest_region_name": conn.get("in_region_name"),
                "wh_type": conn.get("wh_type"),
                "max_ship_size": conn.get("max_ship_size"),
                "remaining_hours": conn.get("remaining_hours"),
                "signature_id": conn.get("out_signature"),
                "completed": conn.get("completed", False),
            }
        )

    return {"connections": result}


@router.get("/activity")
async def get_system_activity() -> dict:
    """Fetch system jumps + kills from ESI (Dotlan-style activity data)."""
    async with httpx.AsyncClient(timeout=15) as client:
        jumps_data = {}
        kills_data = {}
        incursions_data = []

        # Fetch jumps
        try:
            resp = await client.get(f"{ESI_BASE}/universe/system_jumps/")
            resp.raise_for_status()
            for entry in resp.json():
                sid = entry.get("system_id")
                if sid:
                    jumps_data[str(sid)] = entry.get("ship_jumps", 0)
        except httpx.HTTPError:
            logger.warning("Failed to fetch system jumps from ESI")

        # Fetch kills
        try:
            resp = await client.get(f"{ESI_BASE}/universe/system_kills/")
            resp.raise_for_status()
            for entry in resp.json():
                sid = entry.get("system_id")
                if sid:
                    kills_data[str(sid)] = {
                        "ship_kills": entry.get("ship_kills", 0),
                        "npc_kills": entry.get("npc_kills", 0),
                        "pod_kills": entry.get("pod_kills", 0),
                    }
        except httpx.HTTPError:
            logger.warning("Failed to fetch system kills from ESI")

        # Fetch incursions
        try:
            resp = await client.get(f"{ESI_BASE}/incursions/")
            resp.raise_for_status()
            for inc in resp.json():
                incursions_data.append(
                    {
                        "type": inc.get("type"),
                        "state": inc.get("state"),
                        "staging_system_id": inc.get("staging_solar_system_id"),
                        "constellation_id": inc.get("constellation_id"),
                        "infested_systems": inc.get("infested_solar_systems", []),
                        "has_boss": inc.get("has_boss", False),
                        "influence": inc.get("influence", 0),
                    }
                )
        except httpx.HTTPError:
            logger.warning("Failed to fetch incursions from ESI")

    return {
        "jumps": jumps_data,
        "kills": kills_data,
        "incursions": incursions_data,
    }


@router.get("/route", response_model=RouteResponse)
def get_route(
    from_system: str = Query(..., alias="from"),
    to_system: str = Query(..., alias="to"),
    profile: str = Query("shortest"),
    avoid: list[str] | None = Query(None, description="Systems to avoid"),
    bridges: bool = Query(False, description="Use Ansiblex jump bridges"),
    thera: bool = Query(False, description="Use Thera wormhole shortcuts"),
) -> RouteResponse:
    cfg = load_risk_config()
    if profile not in cfg.routing_profiles:
        raise HTTPException(status_code=400, detail=f"Unknown routing profile: {profile}")

    avoid_set: set[str] = set()
    if avoid:
        for item in avoid:
            avoid_set.update(name.strip() for name in item.split(",") if name.strip())

    try:
        return compute_route(
            from_system,
            to_system,
            profile,
            avoid=avoid_set,
            use_bridges=bridges,
            use_thera=thera,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
