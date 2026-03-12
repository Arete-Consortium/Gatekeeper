"""Pochven internal gate routing service.

Pochven is a static region with 27 systems in 3 Krais (constellations),
connected by Triglavian conduit gates. The internal gate network is fixed
and predictable — unlike filament entry/exit which is random.

Gate data sourced from SDE (universe.json).
"""

from ..models.pochven import PochvenConnection
from .data_loader import load_universe

# Krai assignments (9 systems each, verified against SDE region data)
KRAI_PERUN: set[str] = {
    "Ignebaener",
    "Kino",
    "Komo",
    "Konola",
    "Krirald",
    "Nalvula",
    "Otanuomi",
    "Otela",
    "Sakenta",
}
KRAI_SVAROG: set[str] = {
    "Ahtila",
    "Harva",
    "Kuharah",
    "Nani",
    "Niarja",
    "Raravoss",
    "Skarkon",
    "Tunudan",
    "Urhinichi",
}
KRAI_VELES: set[str] = {
    "Ala",
    "Angymonne",
    "Archee",
    "Arvasaras",
    "Ichoriya",
    "Kaunokka",
    "Senda",
    "Vale",
    "Wirashoda",
}

# All 27 Pochven systems
POCHVEN_SYSTEMS: list[str] = sorted(KRAI_PERUN | KRAI_SVAROG | KRAI_VELES)

# Home systems (require 7.0 Trig standing to enter)
HOME_SYSTEMS: set[str] = {"Kino", "Niarja", "Archee"}

# Border systems (between two Krais, require 1.0 standing)
BORDER_SYSTEMS: set[str] = {
    "Ahtila",
    "Senda",  # Veles ↔ Svarog
    "Arvasaras",
    "Sakenta",  # Veles ↔ Perun
    "Otanuomi",
    "Urhinichi",  # Perun ↔ Svarog
}

# Internal conduit gate connections (from SDE gate data).
# All bidirectional. 30 total connections.
_INTERNAL_CONNECTIONS: list[tuple[str, str]] = [
    # Krai Perun internal
    ("Otela", "Kino"),
    ("Otela", "Nalvula"),
    ("Otela", "Ignebaener"),
    ("Kino", "Nalvula"),
    ("Nalvula", "Konola"),
    ("Konola", "Krirald"),
    ("Krirald", "Otanuomi"),
    ("Ignebaener", "Komo"),
    ("Komo", "Sakenta"),
    # Krai Svarog internal
    ("Niarja", "Raravoss"),
    ("Niarja", "Harva"),
    ("Raravoss", "Harva"),
    ("Raravoss", "Skarkon"),
    ("Skarkon", "Nani"),
    ("Nani", "Urhinichi"),
    ("Harva", "Tunudan"),
    ("Tunudan", "Kuharah"),
    ("Kuharah", "Ahtila"),
    # Krai Veles internal
    ("Archee", "Angymonne"),
    ("Archee", "Vale"),
    ("Angymonne", "Vale"),
    ("Angymonne", "Ichoriya"),
    ("Ichoriya", "Kaunokka"),
    ("Kaunokka", "Arvasaras"),
    ("Arvasaras", "Sakenta"),  # cross-Krai: Veles ↔ Perun
    ("Wirashoda", "Ala"),
    ("Wirashoda", "Senda"),
    ("Ala", "Vale"),
    # Cross-Krai connections
    ("Senda", "Ahtila"),  # Veles ↔ Svarog
    ("Otanuomi", "Urhinichi"),  # Perun ↔ Svarog
]


def get_system_krai(system_name: str) -> str | None:
    """Return the Krai for a Pochven system, or None if not Pochven."""
    if system_name in KRAI_PERUN:
        return "perun"
    if system_name in KRAI_SVAROG:
        return "svarog"
    if system_name in KRAI_VELES:
        return "veles"
    return None


def get_system_type(system_name: str) -> str | None:
    """Return 'home', 'border', or 'internal' for a Pochven system."""
    if system_name in HOME_SYSTEMS:
        return "home"
    if system_name in BORDER_SYSTEMS:
        return "border"
    if system_name in KRAI_PERUN | KRAI_SVAROG | KRAI_VELES:
        return "internal"
    return None


# In-memory state
_state: dict[str, object] = {
    "enabled": True,
}


def is_pochven_enabled() -> bool:
    """Check if Pochven routing is enabled."""
    return bool(_state["enabled"])


def toggle_pochven(enabled: bool) -> bool:
    """Toggle Pochven routing on/off. Returns new state."""
    _state["enabled"] = enabled
    return enabled


def get_pochven_systems() -> list[str]:
    """Return list of Pochven system names that exist in the universe."""
    universe = load_universe()
    return [s for s in POCHVEN_SYSTEMS if s in universe.systems]


def get_active_pochven() -> list[PochvenConnection]:
    """Get active Pochven internal gate connections.

    Returns only internal conduit gate connections (not filament entry/exit,
    which is random and unpredictable).
    """
    universe = load_universe()
    connections: list[PochvenConnection] = []

    for from_sys, to_sys in _INTERNAL_CONNECTIONS:
        if from_sys in universe.systems and to_sys in universe.systems:
            from_krai = get_system_krai(from_sys)
            to_krai = get_system_krai(to_sys)
            conn_type = "cross_krai" if from_krai != to_krai else "internal"
            connections.append(
                PochvenConnection(
                    from_system=from_sys,
                    to_system=to_sys,
                    connection_type=conn_type,
                    bidirectional=True,
                )
            )

    return connections
