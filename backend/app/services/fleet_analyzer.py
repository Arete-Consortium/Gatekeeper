"""Fleet composition analyzer service.

Parses EVE Online fleet composition text and produces threat assessments
based on ship types, roles, and fleet size.
"""

import logging
import re
from enum import StrEnum

logger = logging.getLogger(__name__)


class ShipRole(StrEnum):
    """Ship role classification for fleet analysis."""

    DPS = "dps"
    LOGISTICS = "logistics"
    TACKLE = "tackle"
    EWAR = "ewar"
    SCOUT = "scout"
    CAPITAL = "capital"
    SUPPORT = "support"
    UNKNOWN = "unknown"


class ThreatLevel(StrEnum):
    """Overall fleet threat classification."""

    MINIMAL = "minimal"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"
    OVERWHELMING = "overwhelming"


class DPSCategory(StrEnum):
    """Estimated DPS output category."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


# fmt: off
SHIP_CLASSIFICATIONS: dict[str, ShipRole] = {
    # DPS - T2 HACs / Command Ships / Battlecruisers / Battleships / T3Cs
    "Muninn":       ShipRole.DPS,
    "Cerberus":     ShipRole.DPS,
    "Eagle":        ShipRole.DPS,
    "Sacrilege":    ShipRole.DPS,
    "Vagabond":     ShipRole.DPS,
    "Ishtar":       ShipRole.DPS,
    "Deimos":       ShipRole.DPS,
    "Zealot":       ShipRole.DPS,
    "Ferox":        ShipRole.DPS,
    "Hurricane":    ShipRole.DPS,
    "Drake":        ShipRole.DPS,
    "Harbinger":    ShipRole.DPS,
    "Myrmidon":     ShipRole.DPS,
    "Brutix":       ShipRole.DPS,
    "Tornado":      ShipRole.DPS,
    "Naga":         ShipRole.DPS,
    "Oracle":       ShipRole.DPS,
    "Talos":        ShipRole.DPS,
    "Machariel":    ShipRole.DPS,
    "Nightmare":    ShipRole.DPS,
    "Vindicator":   ShipRole.DPS,
    "Bhaalgorn":    ShipRole.DPS,
    "Loki":         ShipRole.DPS,
    "Legion":       ShipRole.DPS,
    "Tengu":        ShipRole.DPS,
    "Proteus":      ShipRole.DPS,
    "Megathron":    ShipRole.DPS,
    "Tempest":      ShipRole.DPS,
    "Raven":        ShipRole.DPS,
    "Abaddon":      ShipRole.DPS,
    "Rokh":         ShipRole.DPS,
    "Maelstrom":    ShipRole.DPS,
    "Hyperion":     ShipRole.DPS,
    "Dominix":      ShipRole.DPS,
    "Typhoon":      ShipRole.DPS,
    "Armageddon":   ShipRole.DPS,
    "Apocalypse":   ShipRole.DPS,
    "Sleipnir":     ShipRole.DPS,
    "Claymore":     ShipRole.DPS,
    "Absolution":   ShipRole.DPS,
    "Damnation":    ShipRole.DPS,
    "Astarte":      ShipRole.DPS,
    "Eos":          ShipRole.DPS,
    "Vulture":      ShipRole.DPS,
    "Nighthawk":    ShipRole.DPS,
    "Retribution":  ShipRole.DPS,
    "Jaguar":       ShipRole.DPS,
    "Wolf":         ShipRole.DPS,
    "Enyo":         ShipRole.DPS,
    "Harpy":        ShipRole.DPS,
    "Hawk":         ShipRole.DPS,
    "Vengeance":    ShipRole.DPS,
    "Ishkur":       ShipRole.DPS,

    # Logistics - T2 Logi / T1 Logi / Triage
    "Guardian":     ShipRole.LOGISTICS,
    "Basilisk":     ShipRole.LOGISTICS,
    "Oneiros":      ShipRole.LOGISTICS,
    "Scimitar":     ShipRole.LOGISTICS,
    "Nestor":       ShipRole.LOGISTICS,
    "Apostle":      ShipRole.LOGISTICS,
    "Minokawa":     ShipRole.LOGISTICS,
    "Ninazu":       ShipRole.LOGISTICS,
    "Lif":          ShipRole.LOGISTICS,
    "Augoror":      ShipRole.LOGISTICS,
    "Osprey":       ShipRole.LOGISTICS,
    "Exequror":     ShipRole.LOGISTICS,
    "Scythe":       ShipRole.LOGISTICS,
    "Deacon":       ShipRole.LOGISTICS,
    "Kirin":        ShipRole.LOGISTICS,
    "Thalia":       ShipRole.LOGISTICS,
    "Burst":        ShipRole.LOGISTICS,

    # Tackle - Interdictors / HICs / Interceptors
    "Sabre":        ShipRole.TACKLE,
    "Flycatcher":   ShipRole.TACKLE,
    "Eris":         ShipRole.TACKLE,
    "Heretic":      ShipRole.TACKLE,
    "Broadsword":   ShipRole.TACKLE,
    "Devoter":      ShipRole.TACKLE,
    "Onyx":         ShipRole.TACKLE,
    "Phobos":       ShipRole.TACKLE,
    "Stiletto":     ShipRole.TACKLE,
    "Ares":         ShipRole.TACKLE,
    "Malediction":  ShipRole.TACKLE,
    "Crow":         ShipRole.TACKLE,
    "Raptor":       ShipRole.TACKLE,
    "Crusader":     ShipRole.TACKLE,
    "Claw":         ShipRole.TACKLE,
    "Taranis":      ShipRole.TACKLE,

    # EWAR - ECM / Damps / Tracking Disruption / Neuts / Webs
    "Kitsune":      ShipRole.EWAR,
    "Blackbird":    ShipRole.EWAR,
    "Falcon":       ShipRole.EWAR,
    "Rook":         ShipRole.EWAR,
    "Scorpion":     ShipRole.EWAR,
    "Griffin":      ShipRole.EWAR,
    "Crucifier":    ShipRole.EWAR,
    "Sentinel":     ShipRole.EWAR,
    "Pilgrim":      ShipRole.EWAR,
    "Curse":        ShipRole.EWAR,
    "Arazu":        ShipRole.EWAR,
    "Lachesis":     ShipRole.EWAR,
    "Rapier":       ShipRole.EWAR,
    "Huginn":       ShipRole.EWAR,
    "Hyena":        ShipRole.EWAR,
    "Vigil":        ShipRole.EWAR,
    "Maulus":       ShipRole.EWAR,
    "Celestis":     ShipRole.EWAR,
    "Bellicose":    ShipRole.EWAR,
    "Arbitrator":   ShipRole.EWAR,

    # Capitals - Dreads / Carriers / Supers / Titans
    "Revelation":   ShipRole.CAPITAL,
    "Moros":        ShipRole.CAPITAL,
    "Naglfar":      ShipRole.CAPITAL,
    "Phoenix":      ShipRole.CAPITAL,
    "Thanatos":     ShipRole.CAPITAL,
    "Archon":       ShipRole.CAPITAL,
    "Nidhoggur":    ShipRole.CAPITAL,
    "Chimera":      ShipRole.CAPITAL,
    "Hel":          ShipRole.CAPITAL,
    "Nyx":          ShipRole.CAPITAL,
    "Aeon":         ShipRole.CAPITAL,
    "Wyvern":       ShipRole.CAPITAL,
    "Avatar":       ShipRole.CAPITAL,
    "Erebus":       ShipRole.CAPITAL,
    "Ragnarok":     ShipRole.CAPITAL,
    "Leviathan":    ShipRole.CAPITAL,
    "Rorqual":      ShipRole.CAPITAL,
    "Dreadnought":  ShipRole.CAPITAL,
    "Carrier":      ShipRole.CAPITAL,
    "Supercarrier": ShipRole.CAPITAL,
    "Titan":        ShipRole.CAPITAL,
    "Zirnitra":     ShipRole.CAPITAL,

    # Scout - CovOps / Astero
    "Buzzard":      ShipRole.SCOUT,
    "Helios":       ShipRole.SCOUT,
    "Anathema":     ShipRole.SCOUT,
    "Cheetah":      ShipRole.SCOUT,
    "Astero":       ShipRole.SCOUT,
    "Pacifier":     ShipRole.SCOUT,
    "Stratios":     ShipRole.SCOUT,

    # Support - Command Destroyers / Logistics Frigates / Misc
    "Pontifex":     ShipRole.SUPPORT,
    "Stork":        ShipRole.SUPPORT,
    "Bifrost":      ShipRole.SUPPORT,
    "Magus":        ShipRole.SUPPORT,
    "Porpoise":     ShipRole.SUPPORT,
    "Orca":         ShipRole.SUPPORT,
}
# fmt: on


def classify_ship(ship_name: str) -> ShipRole:
    """Classify a ship by its role.

    Tries exact match first, then case-insensitive match.
    """
    if ship_name in SHIP_CLASSIFICATIONS:
        return SHIP_CLASSIFICATIONS[ship_name]

    # Case-insensitive fallback
    lower = ship_name.lower()
    for known_ship, role in SHIP_CLASSIFICATIONS.items():
        if known_ship.lower() == lower:
            return role

    return ShipRole.UNKNOWN


def parse_fleet_text(text: str) -> dict[str, int]:
    """Parse fleet composition text into ship name -> count mapping.

    Supports two formats:
    1. Tab-separated (EVE fleet window copy):
       CharacterName\\tShipType\\tSystem\\tPosition
    2. Multiplied format:
       2x Loki
       3x Muninn
    3. Simple ship names (one per line):
       Loki
       Muninn
    """
    ships: dict[str, int] = {}

    if not text or not text.strip():
        return ships

    lines = text.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try multiplied format: "2x Loki" or "2 x Loki" or "2 Loki"
        mult_match = re.match(r"^(\d+)\s*x?\s+(.+)$", line, re.IGNORECASE)
        if mult_match:
            count = int(mult_match.group(1))
            ship_name = mult_match.group(2).strip()
            if ship_name:
                ships[ship_name] = ships.get(ship_name, 0) + count
                continue

        # Try tab-separated format: CharacterName\tShipType\tSystem\tPosition
        parts = line.split("\t")
        if len(parts) >= 2:
            # Ship type is the second column
            ship_name = parts[1].strip()
            if ship_name and ship_name != "Ship Type":
                ships[ship_name] = ships.get(ship_name, 0) + 1
            continue

        # Fallback: treat entire line as ship name
        if line and not line.startswith("#"):
            ships[line] = ships.get(line, 0) + 1

    return ships


def _calculate_threat_level(
    total_pilots: int,
    has_capitals: bool,
    has_logistics: bool,
    composition: dict[str, int],
) -> ThreatLevel:
    """Determine overall threat level based on fleet composition."""
    if total_pilots == 0:
        return ThreatLevel.MINIMAL

    capital_count = composition.get("capital", 0)

    # Overwhelming: capitals + large fleet, or supercaps/titans
    if capital_count >= 5 or (has_capitals and total_pilots >= 50):
        return ThreatLevel.OVERWHELMING

    # Critical: capitals present or large organized fleet
    if has_capitals or (total_pilots >= 30 and has_logistics):
        return ThreatLevel.CRITICAL

    # Significant: medium fleet with logistics
    if total_pilots >= 15 or (total_pilots >= 10 and has_logistics):
        return ThreatLevel.SIGNIFICANT

    # Moderate: small gang with some organization
    if total_pilots >= 5:
        return ThreatLevel.MODERATE

    return ThreatLevel.MINIMAL


def _estimate_dps_category(
    composition: dict[str, int],
    total_pilots: int,
) -> DPSCategory:
    """Estimate fleet DPS category based on composition."""
    dps_count = composition.get("dps", 0)
    capital_count = composition.get("capital", 0)

    if capital_count >= 3 or dps_count >= 30:
        return DPSCategory.EXTREME

    if capital_count >= 1 or dps_count >= 15:
        return DPSCategory.HIGH

    if dps_count >= 5:
        return DPSCategory.MEDIUM

    return DPSCategory.LOW


def _generate_advice(
    composition: dict[str, int],
    has_logistics: bool,
    has_tackle: bool,
    has_capitals: bool,
    total_pilots: int,
    threat_level: ThreatLevel,
) -> list[str]:
    """Generate tactical advice based on fleet composition."""
    advice: list[str] = []

    if total_pilots == 0:
        return ["No ships detected in the fleet composition."]

    ewar_count = composition.get("ewar", 0)
    dps_count = composition.get("dps", 0)
    logi_count = composition.get("logistics", 0)
    tackle_count = composition.get("tackle", 0)
    capital_count = composition.get("capital", 0)
    scout_count = composition.get("scout", 0)

    # Capital-specific advice
    if has_capitals:
        advice.append(
            f"Fleet has {capital_count} capital ship(s). "
            "Requires capital-class or subcap blob response."
        )
        if capital_count >= 5:
            advice.append("Multiple capitals detected — likely a structure bash or major op.")

    # Logistics assessment
    if has_logistics:
        logi_ratio = logi_count / total_pilots if total_pilots > 0 else 0
        if logi_ratio >= 0.2:
            advice.append(
                f"Strong logistics wing ({logi_count} logi, "
                f"{logi_ratio:.0%} of fleet). "
                "Alpha damage or neut pressure recommended."
            )
        else:
            advice.append(f"Light logistics ({logi_count} logi). Focus fire may break reps.")
    else:
        if total_pilots >= 5:
            advice.append("No logistics detected — fleet is vulnerable to attrition.")

    # Tackle assessment
    if has_tackle:
        if tackle_count >= 5:
            advice.append(
                f"Heavy tackle presence ({tackle_count} ships). "
                "Difficult to disengage — bring your own tackle killers."
            )
        else:
            advice.append(
                f"Light tackle ({tackle_count} ships). Disengagement possible if tackle is cleared."
            )
    elif total_pilots >= 5:
        advice.append("No dedicated tackle — fleet may struggle to hold targets.")

    # EWAR assessment
    if ewar_count > 0:
        advice.append(
            f"EWAR present ({ewar_count} ships). Bring ECCM/sensor boosters or counter-EWAR."
        )

    # Scout assessment
    if scout_count > 0:
        advice.append(
            f"Scout(s) detected ({scout_count}). "
            "Fleet likely has good intel — element of surprise is reduced."
        )

    # DPS assessment
    if dps_count >= 20:
        advice.append(
            f"Large DPS wing ({dps_count} ships). Expect high alpha — avoid trading at range."
        )

    # General threat advice
    if threat_level == ThreatLevel.OVERWHELMING:
        advice.append(
            "Overwhelming force — avoid engagement unless you have equal or greater numbers."
        )
    elif threat_level == ThreatLevel.CRITICAL:
        advice.append(
            "Critical threat — engage only with a well-organized fleet of comparable size."
        )

    # Composition balance
    if total_pilots >= 10 and logi_count == 0 and tackle_count == 0:
        advice.append(
            "Unbalanced fleet — no logi or tackle. Likely a kitchen-sink or roaming gang."
        )

    return advice


def analyze_fleet(text: str) -> dict:
    """Analyze a fleet composition and return threat assessment.

    Args:
        text: Raw fleet composition text (tab-separated or multiplied format).

    Returns:
        Dict with fleet analysis including threat level, composition, and advice.
    """
    ships = parse_fleet_text(text)

    if not ships:
        return {
            "total_pilots": 0,
            "total_ships": 0,
            "threat_level": ThreatLevel.MINIMAL.value,
            "composition": {},
            "ship_list": [],
            "has_logistics": False,
            "has_capitals": False,
            "has_tackle": False,
            "estimated_dps_category": DPSCategory.LOW.value,
            "advice": ["No ships detected in the fleet composition."],
        }

    # Classify all ships
    composition: dict[str, int] = {}
    ship_list: list[dict[str, str | int]] = []

    for ship_name, count in ships.items():
        role = classify_ship(ship_name)
        role_key = role.value
        composition[role_key] = composition.get(role_key, 0) + count
        ship_list.append(
            {
                "name": ship_name,
                "count": count,
                "role": role_key,
            }
        )

    total_ships = sum(ships.values())
    has_logistics = composition.get("logistics", 0) > 0
    has_capitals = composition.get("capital", 0) > 0
    has_tackle = composition.get("tackle", 0) > 0

    threat_level = _calculate_threat_level(
        total_pilots=total_ships,
        has_capitals=has_capitals,
        has_logistics=has_logistics,
        composition=composition,
    )

    dps_category = _estimate_dps_category(
        composition=composition,
        total_pilots=total_ships,
    )

    advice = _generate_advice(
        composition=composition,
        has_logistics=has_logistics,
        has_tackle=has_tackle,
        has_capitals=has_capitals,
        total_pilots=total_ships,
        threat_level=threat_level,
    )

    return {
        "total_pilots": total_ships,
        "total_ships": total_ships,
        "threat_level": threat_level.value,
        "composition": composition,
        "ship_list": sorted(ship_list, key=lambda s: (-s["count"], s["name"])),
        "has_logistics": has_logistics,
        "has_capitals": has_capitals,
        "has_tackle": has_tackle,
        "estimated_dps_category": dps_category.value,
        "advice": advice,
    }
