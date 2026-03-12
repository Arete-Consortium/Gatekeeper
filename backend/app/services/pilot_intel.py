"""Pilot intel service — ESI character lookup + zKill aggregate stats.

Provides threat assessment for individual pilots using public ESI data
and zKillboard statistics.
"""

import asyncio
import logging
from datetime import UTC, datetime

import httpx

from ..core.config import settings
from .cache import get_cache

logger = logging.getLogger(__name__)

# Cache TTLs
PILOT_STATS_TTL = 86400  # 24 hours — pilot stats are relatively stable
PILOT_ESI_TTL = 3600  # 1 hour — character info changes rarely

# zKill rate limiting (shared with zkill_stats module)
_last_request_time: datetime = datetime.min.replace(tzinfo=UTC)
_request_interval = 1.0


async def _rate_limit() -> None:
    """Enforce zKillboard rate limiting (1 req/sec)."""
    global _last_request_time
    now = datetime.now(UTC)
    elapsed = (now - _last_request_time).total_seconds()
    if elapsed < _request_interval:
        await asyncio.sleep(_request_interval - elapsed)
    _last_request_time = datetime.now(UTC)


async def _fetch_esi_character(character_id: int) -> dict | None:
    """Fetch public character info from ESI (no auth required)."""
    cache = await get_cache()
    cache_key = f"pilot:esi:{character_id}"

    cached = await cache.get_json(cache_key)
    if cached is not None:
        return cached

    url = f"https://esi.evetech.net/latest/characters/{character_id}/"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(url, params={"datasource": "tranquility"})
            resp.raise_for_status()
            data = resp.json()
            result = {
                "character_id": character_id,
                "name": data.get("name", "Unknown"),
                "corporation_id": data.get("corporation_id"),
                "alliance_id": data.get("alliance_id"),
                "birthday": data.get("birthday"),
                "security_status": data.get("security_status", 0.0),
            }
            await cache.set_json(cache_key, result, PILOT_ESI_TTL)
            return result
    except Exception as e:
        logger.warning(f"Failed to fetch ESI character {character_id}: {e}")
        return None


async def _fetch_esi_names(ids: list[int], category: str) -> dict[int, str]:
    """Bulk resolve IDs to names via ESI /universe/names/."""
    if not ids:
        return {}
    url = "https://esi.evetech.net/latest/universe/names/"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(url, json=ids)
            resp.raise_for_status()
            return {
                item["id"]: item["name"] for item in resp.json() if item.get("category") == category
            }
    except Exception as e:
        logger.warning(f"Failed to resolve {category} names: {e}")
        return {}


async def _fetch_zkill_stats(character_id: int) -> dict | None:
    """Fetch aggregate pilot stats from zKillboard."""
    cache = await get_cache()
    cache_key = f"pilot:zkill:{character_id}"

    cached = await cache.get_json(cache_key)
    if cached is not None:
        return cached

    await _rate_limit()

    url = f"{settings.ZKILL_BASE_URL}/stats/characterID/{character_id}/"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": settings.ZKILL_USER_AGENT},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            # Extract key fields from zKill stats response
            info = data.get("info", {})
            active_pvp = data.get("activepvp", {})
            top_lists = data.get("topLists", [])

            # Parse activity by time of day for timezone inference
            activity = data.get("activity", {})

            # Ships used (from topLists)
            top_ships = []
            top_systems = []
            for tl in top_lists:
                if tl.get("type") == "shipType":
                    top_ships = [
                        {
                            "id": item.get("typeID"),
                            "name": item.get("typeName", ""),
                            "kills": item.get("kills", 0),
                        }
                        for item in tl.get("values", [])[:10]
                    ]
                elif tl.get("type") == "solarSystem":
                    top_systems = [
                        {
                            "id": item.get("solarSystemID"),
                            "name": item.get("solarSystemName", ""),
                            "kills": item.get("kills", 0),
                        }
                        for item in tl.get("values", [])[:5]
                    ]

            result = {
                "kills": info.get("shipsDestroyed", 0),
                "losses": info.get("shipsLost", 0),
                "solo_kills": data.get("soloKills", 0),
                "danger_ratio": data.get("dangerRatio", 0),
                "gang_ratio": data.get("gangRatio", 0),
                "active_pvp_kills": active_pvp.get("kills", {}).get("count", 0),
                "active_pvp_systems": active_pvp.get("systems", {}).get("count", 0),
                "activity": activity,
                "top_ships": top_ships,
                "top_systems": top_systems,
                "isk_destroyed": info.get("iskDestroyed", 0),
                "isk_lost": info.get("iskLost", 0),
            }

            await cache.set_json(cache_key, result, PILOT_STATS_TTL)
            return result
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # No zKill data for this character — not an error
            empty = {
                "kills": 0,
                "losses": 0,
                "solo_kills": 0,
                "danger_ratio": 0,
                "gang_ratio": 0,
                "active_pvp_kills": 0,
                "active_pvp_systems": 0,
                "activity": {},
                "top_ships": [],
                "top_systems": [],
                "isk_destroyed": 0,
                "isk_lost": 0,
            }
            await cache.set_json(cache_key, empty, PILOT_STATS_TTL)
            return empty
        if e.response.status_code == 429:
            logger.warning("zKillboard rate limit hit fetching pilot stats")
        else:
            logger.warning(
                f"HTTP {e.response.status_code} fetching zKill stats for pilot {character_id}"
            )
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch zKill stats for pilot {character_id}: {e}")
        return None


def _compute_threat_level(zkill: dict) -> str:
    """Compute threat level from zKill stats."""
    kills = zkill.get("kills", 0)
    danger = zkill.get("danger_ratio", 0)
    solo = zkill.get("solo_kills", 0)

    # Weighted score
    score = 0
    if kills > 10000:
        score += 4
    elif kills > 5000:
        score += 3
    elif kills > 1000:
        score += 2
    elif kills > 100:
        score += 1

    if danger > 80:
        score += 3
    elif danger > 60:
        score += 2
    elif danger > 40:
        score += 1

    if solo > 500:
        score += 2
    elif solo > 100:
        score += 1

    if score >= 7:
        return "extreme"
    if score >= 5:
        return "high"
    if score >= 3:
        return "moderate"
    if score >= 1:
        return "low"
    return "minimal"


def _infer_active_timezone(activity: dict) -> str | None:
    """Infer primary timezone from zKill activity hours."""
    if not activity:
        return None

    # activity is a dict like {"0": count, "1": count, ...} for UTC hours
    hour_counts = {}
    for hour_str, count in activity.items():
        try:
            hour_counts[int(hour_str)] = count
        except (ValueError, TypeError):
            continue

    if not hour_counts:
        return None

    # Find peak 6-hour window
    best_start = 0
    best_total = 0
    for start in range(24):
        total = sum(hour_counts.get((start + h) % 24, 0) for h in range(6))
        if total > best_total:
            best_total = total
            best_start = start

    # Map peak window to timezone label
    peak_center = (best_start + 3) % 24
    if 12 <= peak_center <= 22:
        return "USTZ"
    if 6 <= peak_center < 12:
        return "AUTZ"
    return "EUTZ"


def _detect_flags(zkill: dict) -> list[str]:
    """Detect notable behavior flags from stats."""
    flags = []
    top_ships = zkill.get("top_ships", [])
    ship_names = [s.get("name", "").lower() for s in top_ships]

    # Cyno flag — uses covert cynos or regular cynos
    cyno_ships = {
        "prospect",
        "venture",
        "endurance",
        "force recon",
        "falcon",
        "rapier",
        "arazu",
        "pilgrim",
        "lachesis",
        "huginn",
    }
    if any(name in cyno_ships for name in ship_names):
        flags.append("possible_cyno")

    # Capital pilot
    cap_keywords = {
        "dreadnought",
        "carrier",
        "supercarrier",
        "titan",
        "force auxiliary",
        "revelation",
        "naglfar",
        "moros",
        "phoenix",
        "archon",
        "thanatos",
        "chimera",
        "nidhoggur",
        "nyx",
        "hel",
        "aeon",
        "wyvern",
        "avatar",
        "erebus",
        "ragnarok",
        "leviathan",
        "apostle",
        "lif",
        "minokawa",
        "ninazu",
    }
    if any(name in cap_keywords for name in ship_names):
        flags.append("capital_pilot")

    # Solo hunter
    if zkill.get("solo_kills", 0) > 100 and zkill.get("danger_ratio", 0) > 60:
        flags.append("solo_hunter")

    # Gang focus
    if zkill.get("gang_ratio", 0) > 80:
        flags.append("gang_focus")

    # High activity
    if zkill.get("active_pvp_kills", 0) > 50:
        flags.append("recently_active")

    return flags


async def resolve_character_names(names: list[str]) -> dict[str, int]:
    """Resolve character names to IDs via ESI POST /universe/ids/.

    Returns dict of name → character_id for successfully resolved names.
    """
    if not names:
        return {}

    url = "https://esi.evetech.net/latest/universe/ids/"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(url, json=names, params={"datasource": "tranquility"})
            resp.raise_for_status()
            data = resp.json()
            characters = data.get("characters", [])
            return {c["name"]: c["id"] for c in characters}
    except Exception as e:
        logger.warning(f"Failed to resolve character names: {e}")
        return {}


async def search_systems(query: str) -> list[dict]:
    """Search for system names via ESI search endpoint."""
    url = "https://esi.evetech.net/latest/search/"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(
                url,
                params={
                    "categories": "solar_system",
                    "search": query,
                    "datasource": "tranquility",
                    "strict": "false",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            system_ids = data.get("solar_system", [])[:10]

            if not system_ids:
                return []

            names_resp = await client.post(
                "https://esi.evetech.net/latest/universe/names/",
                json=system_ids,
                params={"datasource": "tranquility"},
            )
            names_resp.raise_for_status()
            results = []
            for entry in names_resp.json():
                if entry.get("category") == "solar_system":
                    results.append({"id": entry["id"], "name": entry["name"]})
            return results
    except Exception as e:
        logger.warning(f"System search failed: {e}")
        return []


async def search_characters(query: str) -> list[dict]:
    """Search for character names via ESI POST /universe/ids/.

    Returns list of {id, name} dicts for matching characters.
    ESI /universe/ids/ does exact name match, so we also try the
    ESI search endpoint for prefix matching.
    """
    url = "https://esi.evetech.net/latest/search/"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(
                url,
                params={
                    "categories": "character",
                    "search": query,
                    "datasource": "tranquility",
                    "strict": "false",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            char_ids = data.get("character", [])[:10]

            if not char_ids:
                return []

            # Resolve IDs to names
            results = []
            names_resp = await client.post(
                "https://esi.evetech.net/latest/universe/names/",
                json=char_ids,
                params={"datasource": "tranquility"},
            )
            names_resp.raise_for_status()
            for entry in names_resp.json():
                if entry.get("category") == "character":
                    results.append({"id": entry["id"], "name": entry["name"]})
            return results
    except Exception as e:
        logger.warning(f"Character search failed: {e}")
        return []


async def get_pilot_stats(character_id: int) -> dict | None:
    """Get comprehensive pilot threat assessment.

    Returns combined ESI + zKill data with computed threat metrics.
    Returns None if character cannot be found.
    """
    # Fetch ESI and zKill in parallel
    esi_task = _fetch_esi_character(character_id)
    zkill_task = _fetch_zkill_stats(character_id)
    esi_data, zkill_data = await asyncio.gather(esi_task, zkill_task)

    if esi_data is None:
        return None

    # Resolve corp/alliance names
    ids_to_resolve = []
    corp_id = esi_data.get("corporation_id")
    alliance_id = esi_data.get("alliance_id")
    if corp_id:
        ids_to_resolve.append(corp_id)
    if alliance_id:
        ids_to_resolve.append(alliance_id)

    names = {}
    if ids_to_resolve:
        # ESI /universe/names/ accepts mixed categories
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                resp = await client.post(
                    "https://esi.evetech.net/latest/universe/names/",
                    json=ids_to_resolve,
                )
                if resp.status_code == 200:
                    for item in resp.json():
                        names[item["id"]] = item["name"]
        except Exception:
            pass

    zkill = zkill_data or {
        "kills": 0,
        "losses": 0,
        "solo_kills": 0,
        "danger_ratio": 0,
        "gang_ratio": 0,
        "active_pvp_kills": 0,
        "active_pvp_systems": 0,
        "activity": {},
        "top_ships": [],
        "top_systems": [],
        "isk_destroyed": 0,
        "isk_lost": 0,
    }

    threat_level = _compute_threat_level(zkill)
    active_tz = _infer_active_timezone(zkill.get("activity", {}))
    flags = _detect_flags(zkill)

    # Calculate K/D ratio
    kills = zkill.get("kills", 0)
    losses = zkill.get("losses", 0)
    kd_ratio = round(kills / max(losses, 1), 2)

    return {
        "character_id": character_id,
        "name": esi_data.get("name", "Unknown"),
        "corporation_id": corp_id,
        "corporation_name": names.get(corp_id, "Unknown"),
        "alliance_id": alliance_id,
        "alliance_name": names.get(alliance_id) if alliance_id else None,
        "security_status": round(esi_data.get("security_status", 0.0), 2),
        "birthday": esi_data.get("birthday"),
        "kills": kills,
        "losses": losses,
        "kd_ratio": kd_ratio,
        "solo_kills": zkill.get("solo_kills", 0),
        "danger_ratio": zkill.get("danger_ratio", 0),
        "gang_ratio": zkill.get("gang_ratio", 0),
        "isk_destroyed": zkill.get("isk_destroyed", 0),
        "isk_lost": zkill.get("isk_lost", 0),
        "active_pvp_kills": zkill.get("active_pvp_kills", 0),
        "threat_level": threat_level,
        "active_timezone": active_tz,
        "flags": flags,
        "top_ships": zkill.get("top_ships", [])[:5],
        "top_systems": zkill.get("top_systems", [])[:3],
    }
