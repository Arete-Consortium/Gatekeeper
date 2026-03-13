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
            # NOTE: zKill API puts stats at top level, NOT nested under "info"
            top_all_time = data.get("topAllTime", [])

            # Parse activity by time of day for timezone inference
            activity = data.get("activity") or {}

            # Ships and systems from topAllTime
            top_ships = []
            top_systems = []
            fleet_characters = []
            for entry in top_all_time:
                entry_type = entry.get("type")
                items = entry.get("data", [])
                if entry_type == "ship":
                    top_ships = [
                        {
                            "id": item.get("shipTypeID"),
                            "name": "",  # resolved later via ESI
                            "kills": item.get("kills", 0),
                        }
                        for item in items[:10]
                        if item.get("shipTypeID")
                    ]
                elif entry_type == "system":
                    top_systems = [
                        {
                            "id": item.get("solarSystemID"),
                            "name": "",  # resolved later via ESI
                            "kills": item.get("kills", 0),
                        }
                        for item in items[:5]
                        if item.get("solarSystemID")
                    ]
                elif entry_type == "character":
                    fleet_characters = [
                        {
                            "character_id": item.get("characterID"),
                            "kills": item.get("kills", 0),
                        }
                        for item in items[:15]
                        if item.get("characterID") and item.get("characterID") != character_id
                    ]

            # Resolve ship type and system names via ESI
            type_ids = [s["id"] for s in top_ships if s["id"]]
            system_ids = [s["id"] for s in top_systems if s["id"]]
            all_resolve_ids = type_ids + system_ids
            if all_resolve_ids:
                try:
                    names_resp = await client.post(
                        "https://esi.evetech.net/latest/universe/names/",
                        json=all_resolve_ids,
                    )
                    if names_resp.status_code == 200:
                        name_map = {item["id"]: item["name"] for item in names_resp.json()}
                        for s in top_ships:
                            s["name"] = name_map.get(s["id"], "Unknown")
                        for s in top_systems:
                            s["name"] = name_map.get(s["id"], "Unknown")
                except Exception:
                    pass

            # Resolve fleet companion names
            companion_ids = [c["character_id"] for c in fleet_characters if c["character_id"]]
            if companion_ids:
                comp_names = await _fetch_esi_names(companion_ids, "character")
                for c in fleet_characters:
                    c["name"] = comp_names.get(c["character_id"], "Unknown")

            result = {
                "kills": data.get("shipsDestroyed", 0),
                "losses": data.get("shipsLost", 0),
                "solo_kills": data.get("soloKills", 0),
                "danger_ratio": data.get("dangerRatio", 0),
                "gang_ratio": data.get("gangRatio", 0),
                "active_pvp_kills": 0,
                "active_pvp_systems": 0,
                "activity": activity,
                "top_ships": top_ships,
                "top_systems": top_systems,
                "fleet_characters": fleet_characters,
                "isk_destroyed": data.get("iskDestroyed", 0),
                "isk_lost": data.get("iskLost", 0),
                "raw_top_all_time": top_all_time,
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

    # zKill activity: {"max": N, "0": {"hour": count, ...}, "1": {...}, ...}
    # Keys are months (0-11), values are dicts of {hour_str: kill_count}.
    # Aggregate across all months to get total kills per hour.
    hour_counts: dict[int, int] = {}
    for month_key, month_data in activity.items():
        if not isinstance(month_data, dict):
            continue  # skip "max" and other scalar fields
        for hour_str, count in month_data.items():
            try:
                hour = int(hour_str)
                hour_counts[hour] = hour_counts.get(hour, 0) + int(count)
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
    """Search for system names using local universe data.

    Performs case-insensitive prefix match against all known systems.
    Falls back to ESI /universe/ids/ for exact match if no local results.
    """
    from .data_loader import load_universe

    query_lower = query.lower()
    universe = load_universe()

    # Local prefix search (fast, no API call)
    results = []
    for name, sys_data in universe.systems.items():
        if name.lower().startswith(query_lower):
            results.append({"id": sys_data.id, "name": name})
        if len(results) >= 10:
            break

    if results:
        return results

    # Fallback: ESI /universe/ids/ for exact match
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(
                "https://esi.evetech.net/latest/universe/ids/",
                json=[query],
                params={"datasource": "tranquility"},
            )
            resp.raise_for_status()
            data = resp.json()
            for sys in data.get("systems", []):
                results.append({"id": sys["id"], "name": sys["name"]})
            return results[:10]
    except Exception as e:
        logger.warning(f"System search failed: {e}")
        return []


async def search_characters(query: str) -> list[dict]:
    """Search for character names via zKill autocomplete with ESI fallback.

    zKill autocomplete provides prefix matching (like typing in zKill search).
    Falls back to ESI /universe/ids/ for exact match if zKill fails.
    Returns list of {id, name} dicts.
    """
    if not query or len(query) < 2:
        return []

    # Try zKill autocomplete first (prefix matching, public, no auth)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(
                f"https://zkillboard.com/autocomplete/{query}/",
                headers={"User-Agent": "EVE-Gatekeeper/2.0 github.com/Arete-Consortium/EVE_Gatekeeper"},
            )
            if resp.status_code == 200:
                results = resp.json()
                characters = [
                    {"id": int(r["id"]), "name": r["name"]}
                    for r in results
                    if r.get("type") == "character"
                ][:10]
                if characters:
                    return characters
    except Exception as e:
        logger.debug(f"zKill autocomplete failed, falling back to ESI: {e}")

    # Fallback: ESI /universe/ids/ (exact match only)
    url = "https://esi.evetech.net/latest/universe/ids/"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.post(
                url,
                json=[query],
                params={"datasource": "tranquility"},
            )
            resp.raise_for_status()
            data = resp.json()
            characters = data.get("characters", [])
            return [{"id": c["id"], "name": c["name"]} for c in characters[:10]]
    except Exception as e:
        logger.warning(f"Character search failed: {e}")
        return []


async def _fetch_corp_history(character_id: int) -> list[dict]:
    """Fetch corporation history from ESI."""
    cache = await get_cache()
    cache_key = f"pilot:corp_history:{character_id}"

    cached = await cache.get_json(cache_key)
    if cached is not None:
        return cached

    url = f"https://esi.evetech.net/latest/characters/{character_id}/corporationhistory/"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(url, params={"datasource": "tranquility"})
            resp.raise_for_status()
            history = resp.json()

            # Resolve corp names
            corp_ids = list({entry["corporation_id"] for entry in history})
            corp_names = await _fetch_esi_names(corp_ids, "corporation")

            result = [
                {
                    "corporation_id": entry["corporation_id"],
                    "corporation_name": corp_names.get(entry["corporation_id"], "Unknown"),
                    "start_date": entry.get("start_date", ""),
                }
                for entry in history
            ]
            await cache.set_json(cache_key, result, PILOT_STATS_TTL)
            return result
    except Exception as e:
        logger.warning(f"Failed to fetch corp history for {character_id}: {e}")
        return []


async def _fetch_recent_killmails(character_id: int, limit: int = 15) -> list[dict]:
    """Fetch recent killmails from zKill + ESI details."""
    cache = await get_cache()
    cache_key = f"pilot:recent_kills:{character_id}"

    cached = await cache.get_json(cache_key)
    if cached is not None:
        return cached

    await _rate_limit()

    url = f"{settings.ZKILL_BASE_URL}/characterID/{character_id}/"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": settings.ZKILL_USER_AGENT},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            zkill_kills = resp.json()[:limit]

            if not zkill_kills:
                await cache.set_json(cache_key, [], 3600)
                return []

            # Fetch ESI killmail details in parallel
            async def fetch_detail(km: dict) -> dict | None:
                km_id = km.get("killmail_id")
                zkb = km.get("zkb", {})
                km_hash = zkb.get("hash")
                if not km_id or not km_hash:
                    return None
                try:
                    detail_resp = await client.get(
                        f"https://esi.evetech.net/latest/killmails/{km_id}/{km_hash}/",
                        params={"datasource": "tranquility"},
                    )
                    detail_resp.raise_for_status()
                    detail = detail_resp.json()

                    victim = detail.get("victim", {})
                    is_loss = victim.get("character_id") == character_id
                    attackers = detail.get("attackers", [])

                    return {
                        "kill_id": km_id,
                        "timestamp": detail.get("killmail_time", ""),
                        "system_id": detail.get("solar_system_id"),
                        "ship_type_id": victim.get("ship_type_id"),
                        "ship_name": "",  # resolved below
                        "value": zkb.get("totalValue", 0),
                        "is_loss": is_loss,
                        "attacker_count": len(attackers),
                        "attacker_ids": [
                            a.get("character_id")
                            for a in attackers
                            if a.get("character_id") and a.get("character_id") != character_id
                        ][:20],
                    }
                except Exception:
                    return None

            details = await asyncio.gather(*[fetch_detail(km) for km in zkill_kills])
            kills = [d for d in details if d is not None]

            # Resolve ship type and system names
            type_ids = list({k["ship_type_id"] for k in kills if k["ship_type_id"]})
            system_ids = list({k["system_id"] for k in kills if k["system_id"]})
            all_ids = type_ids + system_ids

            if all_ids:
                try:
                    names_resp = await client.post(
                        "https://esi.evetech.net/latest/universe/names/",
                        json=all_ids,
                    )
                    if names_resp.status_code == 200:
                        name_map = {item["id"]: item["name"] for item in names_resp.json()}
                        for k in kills:
                            k["ship_name"] = name_map.get(k["ship_type_id"], "Unknown")
                            k["system_name"] = name_map.get(k["system_id"], "Unknown")
                except Exception:
                    pass

            # Remove internal attacker_ids from cached result (used for companion extraction)
            result = kills
            await cache.set_json(cache_key, result, 3600)
            return result
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("zKillboard rate limit hit fetching recent kills")
        else:
            logger.warning(f"HTTP {e.response.status_code} fetching recent kills for {character_id}")
        return []
    except Exception as e:
        logger.warning(f"Failed to fetch recent kills for {character_id}: {e}")
        return []


async def _extract_fleet_companions_from_kills(
    recent_kills: list[dict], exclude_id: int = 0
) -> list[dict]:
    """Extract fleet companions by aggregating attacker_ids from recent killmails.

    Counts how often each character appears alongside the target pilot,
    then resolves names via ESI. Excludes the target pilot themselves.
    """
    from collections import Counter

    companion_counts: Counter = Counter()
    for kill in recent_kills:
        for char_id in kill.get("attacker_ids", []):
            if char_id and char_id != exclude_id:
                companion_counts[char_id] += 1

    if not companion_counts:
        return []

    # Top 10 by frequency
    top = companion_counts.most_common(10)
    top_ids = [cid for cid, _ in top]

    # Resolve names
    names = await _fetch_esi_names(top_ids, "character")

    return [
        {
            "character_id": cid,
            "name": names.get(cid, f"Unknown ({cid})"),
            "kills": count,
        }
        for cid, count in top
    ]


def _build_activity_pattern(activity: dict) -> dict:
    """Build structured activity pattern from zKill activity hours.

    zKill format: {"max": N, "0": {"hour": count}, "1": {...}, ...}
    Keys are months (0-11), values are dicts of {hour_str: kill_count}.
    """
    hourly: dict[int, int] = {}
    for month_key, month_data in activity.items():
        if not isinstance(month_data, dict):
            continue
        for hour_str, count in month_data.items():
            try:
                hour = int(hour_str)
                hourly[hour] = hourly.get(hour, 0) + int(count)
            except (ValueError, TypeError):
                continue

    # Day-of-week buckets (not available from zKill stats, return hourly only)
    peak_hours = sorted(hourly.keys(), key=lambda h: hourly.get(h, 0), reverse=True)[:6]

    return {
        "hourly": {str(h): hourly.get(h, 0) for h in range(24)},
        "peak_hours": peak_hours,
    }


async def get_pilot_deep_dive(character_id: int) -> dict | None:
    """Get comprehensive pilot intel deep-dive.

    Returns all data from get_pilot_stats() plus fleet companions,
    activity patterns, corp history, and recent kills.
    """
    # Fetch all data in parallel where possible
    # ESI + zKill stats (existing)
    esi_task = _fetch_esi_character(character_id)
    zkill_task = _fetch_zkill_stats(character_id)
    corp_task = _fetch_corp_history(character_id)
    kills_task = _fetch_recent_killmails(character_id)

    esi_data, zkill_data, corp_history, recent_kills = await asyncio.gather(
        esi_task, zkill_task, corp_task, kills_task
    )

    if esi_data is None:
        return None

    # Get base stats
    base = await get_pilot_stats(character_id)
    if base is None:
        return None

    # Extract fleet companions from killmail attacker lists
    fleet_companions = await _extract_fleet_companions_from_kills(
        recent_kills, exclude_id=character_id
    )

    # Build activity pattern
    activity = zkill_data.get("activity", {}) if zkill_data else {}
    activity_pattern = _build_activity_pattern(activity)

    # Strip attacker_ids from recent kills (internal only)
    clean_kills = [
        {k: v for k, v in kill.items() if k != "attacker_ids"}
        for kill in recent_kills
    ]

    return {
        **base,
        "fleet_companions": fleet_companions,
        "activity_pattern": activity_pattern,
        "corp_history": corp_history,
        "recent_kills": clean_kills,
    }


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
