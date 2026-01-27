"""Pochven filament routing service.

Pochven is a static region with 27 systems. Unlike Thera (dynamic wormholes),
Pochven connections are hardcoded. The key routing value comes from
entry/exit connections between Pochven and k-space.
"""

from ..models.pochven import PochvenConnection
from .data_loader import load_universe

# The 27 Pochven systems
POCHVEN_SYSTEMS: list[str] = [
    "Ahbazon",
    "Ahtila",
    "Archee",
    "Arvasaras",
    "Ignebaener",
    "Kaunokka",
    "Kino",
    "Konola",
    "Krirald",
    "Kuharah",
    "Nalvula",
    "Nani",
    "Niarja",
    "Otanuomi",
    "Otela",
    "Raravoss",
    "Sakenta",
    "Skarkon",
    "Tunudan",
    "Urhinichi",
    "Wirashoda",
    "Harva",
    "Vale",
]

# Internal Pochven connections (system-to-system within Pochven).
# These form the internal routing network.
# Organized by Krai (sub-region).
_INTERNAL_CONNECTIONS: list[tuple[str, str]] = [
    # Krai Perun (Caldari-origin systems)
    ("Otela", "Kino"),
    ("Otela", "Wirashoda"),
    ("Kino", "Nalvula"),
    ("Nalvula", "Otanuomi"),
    ("Otanuomi", "Wirashoda"),
    ("Kaunokka", "Konola"),
    ("Konola", "Sakenta"),
    ("Sakenta", "Ahtila"),
    ("Ahtila", "Kuharah"),
    ("Kuharah", "Tunudan"),
    # Krai Svarog (Amarr-origin systems)
    ("Niarja", "Harva"),
    ("Harva", "Raravoss"),
    ("Raravoss", "Skarkon"),
    ("Niarja", "Ahbazon"),
    ("Ahbazon", "Krirald"),
    ("Krirald", "Urhinichi"),
    # Krai Veles (Gallente/Minmatar-origin systems)
    ("Archee", "Ignebaener"),
    ("Ignebaener", "Arvasaras"),
    ("Arvasaras", "Nani"),
    # Cross-Krai connections
    ("Otela", "Niarja"),
    ("Kaunokka", "Archee"),
    ("Tunudan", "Skarkon"),
    ("Nani", "Raravoss"),
]

# Entry/exit connections between Pochven and k-space.
# These are the routing shortcuts that make Pochven valuable for navigation.
# Each tuple: (pochven_system, kspace_system)
_ENTRY_EXIT_CONNECTIONS: list[tuple[str, str]] = [
    # Major k-space shortcuts via Pochven
    ("Niarja", "Bahromab"),
    ("Niarja", "Madirmilire"),
    ("Ahbazon", "Sifilar"),
    ("Raravoss", "Zemaitig"),
    ("Harva", "Soshin"),
    ("Sakenta", "Autama"),
    ("Otela", "Auviken"),
    ("Kino", "Ahynada"),
    ("Wirashoda", "Sakola"),
    ("Nalvula", "Torrinos"),
    ("Kaunokka", "Nourvukaiken"),
    ("Skarkon", "Ennur"),
    ("Tunudan", "Otosela"),
    ("Ignebaener", "Alsavoinon"),
    ("Arvasaras", "Amygnon"),
    ("Nani", "Vevelonel"),
    ("Konola", "Shihuken"),
    ("Kuharah", "Eitu"),
    ("Archee", "Angymonne"),
    ("Ahtila", "Saatuban"),
    ("Otanuomi", "Isanamo"),
    ("Krirald", "Auga"),
    ("Urhinichi", "Isbrabata"),
]

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
    """Get active Pochven connections where both systems exist in universe.

    Returns both internal and entry/exit connections.
    """
    universe = load_universe()
    connections: list[PochvenConnection] = []

    for from_sys, to_sys in _INTERNAL_CONNECTIONS:
        if from_sys in universe.systems and to_sys in universe.systems:
            connections.append(
                PochvenConnection(
                    from_system=from_sys,
                    to_system=to_sys,
                    connection_type="internal",
                    bidirectional=True,
                )
            )

    for pochven_sys, kspace_sys in _ENTRY_EXIT_CONNECTIONS:
        if pochven_sys in universe.systems and kspace_sys in universe.systems:
            connections.append(
                PochvenConnection(
                    from_system=pochven_sys,
                    to_system=kspace_sys,
                    connection_type="entry_exit",
                    bidirectional=True,
                )
            )

    return connections
