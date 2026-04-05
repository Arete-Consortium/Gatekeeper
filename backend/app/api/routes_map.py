import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Query

from ..models.route import RouteResponse
from ..services.cache import build_esi_key, build_map_config_key, get_cache
from ..services.data_loader import load_risk_config, load_universe
from ..services.risk_engine import compute_risk, risk_to_color
from ..services.routing import compute_route

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"
ESI_BASE = "https://esi.evetech.net/latest"
EVE_SCOUT_API = "https://api.eve-scout.com/v2/public/signatures"

# Cache TTLs (seconds)
MAP_CONFIG_TTL = 300  # 5 min — risk updates flow via WebSocket in real-time
SOV_TTL = 300  # 5 min — ESI sov data updates hourly
FW_TTL = 300  # 5 min — matches fw_cache.py
THERA_TTL = 120  # 2 min — wormhole connections change frequently
ACTIVITY_TTL = 300  # 5 min — ESI system_kills/jumps update hourly


@router.get("/config")
async def map_config() -> dict:
    cache = await get_cache()
    cache_key = build_map_config_key()
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

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

    result = {
        "metadata": universe.metadata.dict(),
        "systems": systems_payload,
        "gates": gates_payload,
        "layers": cfg.map_layers,
        "landmarks": landmarks,
        "factions": factions,
    }
    await cache.set_json(cache_key, result, ttl=MAP_CONFIG_TTL)
    return result


@router.get("/sovereignty")
async def get_sovereignty() -> dict:
    """Fetch current sovereignty map from ESI."""
    cache = await get_cache()
    cache_key = build_esi_key("sovereignty_map")
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

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

    result = {
        "sovereignty": sov_map,
        "alliances": alliance_names,
    }
    await cache.set_json(cache_key, result, ttl=SOV_TTL)
    return result


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

    # Refresh FW pirate suppression data (separate concern from response cache)
    await ensure_fw_cache()

    cache = await get_cache()
    cache_key = build_esi_key("fw_systems")
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

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

    result = {"fw_systems": fw_systems}
    await cache.set_json(cache_key, result, ttl=FW_TTL)
    return result


# Pirate faction ID → name mapping
PIRATE_FACTIONS: dict[int, str] = {
    500010: "Guristas Pirates",
    500011: "Angel Cartel",
}


@router.get("/pirate-insurgency")
async def get_pirate_insurgency() -> dict:
    """Return systems with pirate faction occupation (security suppressed).

    Uses the FW cache to identify systems occupied by Guristas (500010)
    or Angel Cartel (500011), then enriches with system names from
    universe data.
    """
    from ..services.fw_cache import _cache as fw_cache_data
    from ..services.fw_cache import ensure_fw_cache

    await ensure_fw_cache()

    universe = load_universe()
    # Build system_id → system_name lookup
    id_to_name: dict[int, str] = {}
    for name, sys in universe.systems.items():
        id_to_name[sys.id] = name

    systems = []
    for system_id, occupier_faction_id in fw_cache_data.occupier_by_system.items():
        if occupier_faction_id not in PIRATE_FACTIONS:
            continue
        systems.append(
            {
                "system_id": system_id,
                "system_name": id_to_name.get(system_id, f"Unknown-{system_id}"),
                "occupier_faction_id": occupier_faction_id,
                "faction_name": PIRATE_FACTIONS[occupier_faction_id],
            }
        )

    return {"systems": systems}


@router.get("/sovereignty/structures")
async def get_sov_structures() -> dict:
    """Fetch sovereignty structures (iHubs, ADM levels) from ESI."""
    cache = await get_cache()
    cache_key = build_esi_key("sovereignty_structures")
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

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

    result = {"structures": system_structures}
    await cache.set_json(cache_key, result, ttl=SOV_TTL)
    return result


@router.get("/thera")
async def get_thera_connections() -> dict:
    """Fetch current Thera/Turnur/Zarzakh connections from EVE Scout."""
    cache = await get_cache()
    cache_key = build_esi_key("thera_connections")
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(EVE_SCOUT_API)
            resp.raise_for_status()
            connections = resp.json()
        except httpx.HTTPError:
            logger.exception("Failed to fetch EVE Scout data")
            raise HTTPException(503, "EVE Scout data unavailable") from None

    THERA_ID = 31000005
    thera_connections = []
    for conn in connections:
        out_id = conn.get("out_system_id")
        in_id = conn.get("in_system_id")

        # Only include connections involving Thera
        if out_id != THERA_ID and in_id != THERA_ID:
            continue

        # Determine which end is the k-space system
        if out_id == THERA_ID:
            kspace_id = in_id
            kspace_name = conn.get("in_system_name")
            region_name = conn.get("in_region_name")
        else:
            kspace_id = out_id
            kspace_name = conn.get("out_system_name")
            region_name = conn.get("out_region_name")

        thera_connections.append(
            {
                "id": conn.get("id"),
                "system_id": kspace_id,
                "system_name": kspace_name,
                "region_name": region_name,
                "wh_type": conn.get("wh_type"),
                "max_ship_size": conn.get("max_ship_size"),
                "remaining_hours": conn.get("remaining_hours"),
                "signature_id": conn.get("out_signature"),
                "completed": conn.get("completed", False),
            }
        )

    result = {"connections": thera_connections}
    await cache.set_json(cache_key, result, ttl=THERA_TTL)
    return result


@router.get("/activity")
async def get_system_activity() -> dict:
    """Fetch system jumps + kills from ESI (Dotlan-style activity data)."""
    cache = await get_cache()
    cache_key = build_esi_key("activity")
    cached = await cache.get_json(cache_key)
    if cached:
        return cached

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

    result = {
        "jumps": jumps_data,
        "kills": kills_data,
        "incursions": incursions_data,
    }
    await cache.set_json(cache_key, result, ttl=ACTIVITY_TTL)
    return result


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
