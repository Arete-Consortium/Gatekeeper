"""Ship fitting parser and travel analyzer.

Parses EFT format fits and calculates jump capabilities for travel planning.
"""

import re
from dataclasses import dataclass, field
from enum import Enum


class ShipCategory(str, Enum):
    """Ship size/category for travel planning."""

    frigate = "frigate"
    destroyer = "destroyer"
    cruiser = "cruiser"
    battlecruiser = "battlecruiser"
    battleship = "battleship"
    capital = "capital"
    supercapital = "supercapital"
    industrial = "industrial"
    freighter = "freighter"
    unknown = "unknown"


class JumpCapability(str, Enum):
    """Ship jump drive capability."""

    none = "none"  # No jump drive
    jump_drive = "jump_drive"  # Standard jump drive
    jump_portal = "jump_portal"  # Can open jump portals (Titans, Black Ops)
    covert_bridge = "covert_bridge"  # Covert jump portal (Black Ops)
    jump_freighter = "jump_freighter"  # Jump freighter


# Ship data - name to category/jump capability mapping
# This is a subset of common ships for demonstration
SHIP_DATA: dict[str, dict] = {
    # Frigates
    "Rifter": {"category": ShipCategory.frigate, "jump": JumpCapability.none},
    "Punisher": {"category": ShipCategory.frigate, "jump": JumpCapability.none},
    "Merlin": {"category": ShipCategory.frigate, "jump": JumpCapability.none},
    "Incursus": {"category": ShipCategory.frigate, "jump": JumpCapability.none},
    "Astero": {"category": ShipCategory.frigate, "jump": JumpCapability.none},
    "Garmur": {"category": ShipCategory.frigate, "jump": JumpCapability.none},
    # Destroyers
    "Thrasher": {"category": ShipCategory.destroyer, "jump": JumpCapability.none},
    "Catalyst": {"category": ShipCategory.destroyer, "jump": JumpCapability.none},
    "Coercer": {"category": ShipCategory.destroyer, "jump": JumpCapability.none},
    "Cormorant": {"category": ShipCategory.destroyer, "jump": JumpCapability.none},
    "Svipul": {"category": ShipCategory.destroyer, "jump": JumpCapability.none},
    "Confessor": {"category": ShipCategory.destroyer, "jump": JumpCapability.none},
    # Cruisers
    "Caracal": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Stabber": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Omen": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Thorax": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Vexor": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Gila": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Stratios": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    # Heavy Assault Cruisers
    "Cerberus": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Vagabond": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Sacrilege": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Ishtar": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Muninn": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    # Recons
    "Falcon": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Rapier": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Arazu": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Pilgrim": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    # T3 Cruisers
    "Tengu": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Loki": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Proteus": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    "Legion": {"category": ShipCategory.cruiser, "jump": JumpCapability.none},
    # Battlecruisers
    "Drake": {"category": ShipCategory.battlecruiser, "jump": JumpCapability.none},
    "Hurricane": {"category": ShipCategory.battlecruiser, "jump": JumpCapability.none},
    "Harbinger": {"category": ShipCategory.battlecruiser, "jump": JumpCapability.none},
    "Brutix": {"category": ShipCategory.battlecruiser, "jump": JumpCapability.none},
    "Myrmidon": {"category": ShipCategory.battlecruiser, "jump": JumpCapability.none},
    "Gnosis": {"category": ShipCategory.battlecruiser, "jump": JumpCapability.none},
    # Battleships
    "Raven": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Scorpion": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Typhoon": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Tempest": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Armageddon": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Apocalypse": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Megathron": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Dominix": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Machariel": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Nightmare": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Vindicator": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Rattlesnake": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    "Praxis": {"category": ShipCategory.battleship, "jump": JumpCapability.none},
    # Black Ops
    "Sin": {"category": ShipCategory.battleship, "jump": JumpCapability.covert_bridge},
    "Redeemer": {"category": ShipCategory.battleship, "jump": JumpCapability.covert_bridge},
    "Widow": {"category": ShipCategory.battleship, "jump": JumpCapability.covert_bridge},
    "Panther": {"category": ShipCategory.battleship, "jump": JumpCapability.covert_bridge},
    "Marshal": {"category": ShipCategory.battleship, "jump": JumpCapability.covert_bridge},
    # Industrials
    "Tayra": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Mammoth": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Bestower": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Iteron Mark V": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Epithal": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Viator": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Prorator": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Crane": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    "Prowler": {"category": ShipCategory.industrial, "jump": JumpCapability.none},
    # Freighters
    "Charon": {"category": ShipCategory.freighter, "jump": JumpCapability.none},
    "Obelisk": {"category": ShipCategory.freighter, "jump": JumpCapability.none},
    "Providence": {"category": ShipCategory.freighter, "jump": JumpCapability.none},
    "Fenrir": {"category": ShipCategory.freighter, "jump": JumpCapability.none},
    # Jump Freighters
    "Rhea": {"category": ShipCategory.freighter, "jump": JumpCapability.jump_freighter},
    "Nomad": {"category": ShipCategory.freighter, "jump": JumpCapability.jump_freighter},
    "Anshar": {"category": ShipCategory.freighter, "jump": JumpCapability.jump_freighter},
    "Ark": {"category": ShipCategory.freighter, "jump": JumpCapability.jump_freighter},
    # Carriers
    "Archon": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Thanatos": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Chimera": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Nidhoggur": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    # Dreadnoughts
    "Revelation": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Moros": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Naglfar": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Phoenix": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    # Force Auxiliaries
    "Apostle": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Ninazu": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Minokawa": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    "Lif": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
    # Supercarriers
    "Aeon": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_drive},
    "Nyx": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_drive},
    "Wyvern": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_drive},
    "Hel": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_drive},
    # Titans
    "Avatar": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_portal},
    "Erebus": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_portal},
    "Leviathan": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_portal},
    "Ragnarok": {"category": ShipCategory.supercapital, "jump": JumpCapability.jump_portal},
    # Rorqual
    "Rorqual": {"category": ShipCategory.capital, "jump": JumpCapability.jump_drive},
}

# Module patterns that affect travel
TRAVEL_MODULES = {
    "Covert Ops Cloaking Device": {"covert_capable": True},
    "Covert Ops Cloaking Device II": {"covert_capable": True},
    "Improved Cloaking Device": {"cloak_capable": True},
    "Improved Cloaking Device II": {"cloak_capable": True},
    "Prototype Cloaking Device": {"cloak_capable": True},
    "Jump Drive Economizer": {"fuel_reduction": True},
    "Jump Drive Economizer I": {"fuel_reduction": True},
    "Jump Drive Economizer II": {"fuel_reduction": True},
    "Hyperspatial Velocity Optimizer": {"warp_speed": True},
    "Hyperspatial Velocity Optimizer I": {"warp_speed": True},
    "Hyperspatial Velocity Optimizer II": {"warp_speed": True},
    "Inertial Stabilizers": {"align_time": True},
    "Inertial Stabilizers I": {"align_time": True},
    "Inertial Stabilizers II": {"align_time": True},
    "Nanofiber Internal Structure": {"align_time": True},
    "Nanofiber Internal Structure I": {"align_time": True},
    "Nanofiber Internal Structure II": {"align_time": True},
    "Warp Core Stabilizer": {"warp_stability": True},
    "Warp Core Stabilizer I": {"warp_stability": True},
    "Warp Core Stabilizer II": {"warp_stability": True},
    "Interdiction Nullifier": {"bubble_immune": True},
    "Interdiction Nullifier I": {"bubble_immune": True},
    "Interdiction Nullifier II": {"bubble_immune": True},
}


@dataclass
class ParsedFitting:
    """A parsed ship fitting."""

    ship_name: str
    ship_category: ShipCategory
    jump_capability: JumpCapability
    modules: list[str] = field(default_factory=list)
    cargo: list[str] = field(default_factory=list)
    drones: list[str] = field(default_factory=list)
    charges: list[str] = field(default_factory=list)
    raw_text: str = ""

    # Travel properties
    is_covert_capable: bool = False
    is_cloak_capable: bool = False
    has_warp_stabs: bool = False
    is_bubble_immune: bool = False
    has_align_mods: bool = False
    has_warp_speed_mods: bool = False


@dataclass
class TravelRecommendation:
    """Travel recommendation based on fitting."""

    ship_name: str
    category: ShipCategory
    can_use_gates: bool = True
    can_use_jump_bridges: bool = True
    can_jump: bool = False
    can_bridge_others: bool = False
    can_covert_bridge: bool = False
    recommended_profile: str = "shortest"
    warnings: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)


def parse_eft_fitting(eft_text: str) -> ParsedFitting | None:
    """
    Parse an EFT (EVE Fitting Tool) format fitting.

    EFT format example:
    [Caracal, Travel Fit]
    Damage Control II
    Nanofiber Internal Structure II

    50MN Microwarpdrive II
    Large Shield Extender II

    Rapid Light Missile Launcher II

    Medium Core Defense Field Extender I

    Returns:
        ParsedFitting or None if parsing fails
    """
    lines = eft_text.strip().split("\n")
    if not lines:
        return None

    # First line should be [ShipName, FitName] or [ShipName]
    first_line = lines[0].strip()
    if not first_line.startswith("[") or "]" not in first_line:
        return None

    # Extract ship name
    bracket_content = first_line[1 : first_line.index("]")]
    parts = bracket_content.split(",")
    ship_name = parts[0].strip()

    # Look up ship data
    ship_info = SHIP_DATA.get(ship_name, {})
    category = ship_info.get("category", ShipCategory.unknown)
    jump_capability = ship_info.get("jump", JumpCapability.none)

    # Parse modules and items
    modules: list[str] = []
    cargo: list[str] = []
    drones: list[str] = []
    charges: list[str] = []

    current_section = "modules"  # Default section

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # Check for section markers
        if line.lower().startswith("[cargo"):
            current_section = "cargo"
            continue
        elif line.lower().startswith("[drone"):
            current_section = "drones"
            continue
        elif line.lower() == "[empty high slot]":
            continue
        elif line.lower() == "[empty med slot]":
            continue
        elif line.lower() == "[empty low slot]":
            continue
        elif line.lower() == "[empty rig slot]":
            continue
        elif line.startswith("["):
            continue

        # Remove quantity suffix like "x5"
        item_name = re.sub(r"\s*x\d+$", "", line).strip()

        if current_section == "cargo":
            cargo.append(item_name)
        elif current_section == "drones":
            drones.append(item_name)
        else:
            # Check if it's ammo/charge (in module slot format "Module, Charge")
            if "," in item_name:
                module_part, charge_part = item_name.split(",", 1)
                modules.append(module_part.strip())
                charges.append(charge_part.strip())
            else:
                modules.append(item_name)

    # Analyze travel capabilities from modules
    is_covert = False
    is_cloak = False
    has_stabs = False
    is_bubble_immune = False
    has_align = False
    has_warp_speed = False

    for module in modules:
        for travel_mod, props in TRAVEL_MODULES.items():
            if travel_mod.lower() in module.lower():
                if props.get("covert_capable"):
                    is_covert = True
                if props.get("cloak_capable"):
                    is_cloak = True
                if props.get("warp_stability"):
                    has_stabs = True
                if props.get("bubble_immune"):
                    is_bubble_immune = True
                if props.get("align_time"):
                    has_align = True
                if props.get("warp_speed"):
                    has_warp_speed = True

    return ParsedFitting(
        ship_name=ship_name,
        ship_category=category,
        jump_capability=jump_capability,
        modules=modules,
        cargo=cargo,
        drones=drones,
        charges=charges,
        raw_text=eft_text,
        is_covert_capable=is_covert,
        is_cloak_capable=is_cloak,
        has_warp_stabs=has_stabs,
        is_bubble_immune=is_bubble_immune,
        has_align_mods=has_align,
        has_warp_speed_mods=has_warp_speed,
    )


def get_travel_recommendation(fitting: ParsedFitting) -> TravelRecommendation:
    """
    Get travel recommendations based on fitting analysis.

    Args:
        fitting: Parsed ship fitting

    Returns:
        TravelRecommendation with advice for this ship
    """
    warnings: list[str] = []
    tips: list[str] = []

    can_jump = fitting.jump_capability != JumpCapability.none
    can_bridge = fitting.jump_capability in (
        JumpCapability.jump_portal,
        JumpCapability.covert_bridge,
    )
    can_covert_bridge = fitting.jump_capability == JumpCapability.covert_bridge

    # Gate restrictions
    can_use_gates = fitting.ship_category not in (
        ShipCategory.capital,
        ShipCategory.supercapital,
    )

    # Determine recommended profile
    if fitting.ship_category in (ShipCategory.capital, ShipCategory.supercapital):
        recommended = "safest"
        warnings.append("Capital ships cannot use stargates")
        if can_jump:
            tips.append("Use jump drive for travel")
    elif fitting.ship_category == ShipCategory.freighter:
        if can_jump:
            recommended = "safest"
            tips.append("Jump freighter can use jump drive or gates")
        else:
            recommended = "safer"
            warnings.append("Freighter is slow and vulnerable - consider escort")
    elif fitting.is_covert_capable:
        recommended = "shortest"
        tips.append("Covert cloak allows safer travel through hostile space")
    elif fitting.is_bubble_immune:
        recommended = "shorter"
        tips.append("Interdiction nullifier provides bubble immunity")
    elif fitting.ship_category in (ShipCategory.frigate, ShipCategory.destroyer):
        recommended = "shortest"
        tips.append("Small fast ships can often evade camps")
    else:
        recommended = "safer"

    # Additional tips
    if fitting.is_cloak_capable and not fitting.is_covert_capable:
        tips.append("Use MWD+cloak trick for gate camps")

    if fitting.has_warp_stabs:
        tips.append("Warp stabs provide some protection from scrams")

    if fitting.has_align_mods:
        tips.append("Good align time helps escape gate camps")

    if not fitting.is_cloak_capable and fitting.ship_category in (
        ShipCategory.industrial,
        ShipCategory.freighter,
    ):
        warnings.append("No cloak fitted - consider adding one")

    return TravelRecommendation(
        ship_name=fitting.ship_name,
        category=fitting.ship_category,
        can_use_gates=can_use_gates,
        can_use_jump_bridges=True,  # All ships can use jump bridges
        can_jump=can_jump,
        can_bridge_others=can_bridge,
        can_covert_bridge=can_covert_bridge,
        recommended_profile=recommended,
        warnings=warnings,
        tips=tips,
    )


def get_ship_info(ship_name: str) -> dict | None:
    """Get ship info by name."""
    return SHIP_DATA.get(ship_name)


def list_ships_by_category(category: ShipCategory) -> list[str]:
    """List all ships in a category."""
    return [name for name, data in SHIP_DATA.items() if data.get("category") == category]


def list_jump_capable_ships() -> list[str]:
    """List all ships with jump drive capability."""
    return [name for name, data in SHIP_DATA.items() if data.get("jump") != JumpCapability.none]
