"""Intel channel parser for hostile reports.

Parses EVE Online intel channel chat formats to extract hostile reports.
Common formats supported:
- "System +1" - one hostile in system
- "System +3" - three hostiles
- "System clear" or "System clr" - system cleared
- "System HostileName" - hostile by name
- "System HostileName Another" - multiple hostiles by name
- "System camp" - gate camp reported
- "System Sabre bubble" - ship type with action
- "System -> Destination" - direction of travel
"""

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from threading import RLock

from .data_loader import load_universe


class ThreatType(str, Enum):
    """Type of threat reported."""

    hostile = "hostile"
    gate_camp = "gate_camp"
    bubble = "bubble"
    fleet = "fleet"
    unknown = "unknown"


@dataclass
class IntelReport:
    """A single intel report."""

    system_name: str
    hostile_count: int
    hostile_names: list[str] = field(default_factory=list)
    reported_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    reporter: str | None = None
    raw_text: str = ""
    is_clear: bool = False
    threat_type: ThreatType = ThreatType.hostile
    ship_types: list[str] = field(default_factory=list)
    direction: str | None = None  # e.g., "toward Amarr", "from Jita"


@dataclass
class SystemIntel:
    """Aggregated intel for a system."""

    system_name: str
    total_hostiles: int
    reports: list[IntelReport]
    last_updated: datetime
    is_clear: bool = False

    @property
    def age_seconds(self) -> float:
        """Get age of intel in seconds."""
        return (datetime.now(UTC) - self.last_updated).total_seconds()


class IntelStore:
    """Thread-safe in-memory storage for intel reports."""

    def __init__(
        self,
        max_age_minutes: int = 15,
        max_reports_per_system: int = 10,
    ):
        self._reports: dict[str, list[IntelReport]] = defaultdict(list)
        self._lock = RLock()  # Reentrant lock to allow nested calls
        self.max_age_minutes = max_age_minutes
        self.max_reports_per_system = max_reports_per_system
        self._subscribers: list[Callable[[IntelReport], None]] = []

    def add_report(self, report: IntelReport) -> None:
        """Add an intel report."""
        with self._lock:
            system = report.system_name
            self._reports[system].append(report)

            # Keep only recent reports
            if len(self._reports[system]) > self.max_reports_per_system:
                self._reports[system] = self._reports[system][-self.max_reports_per_system :]

        # Notify subscribers outside the lock
        for callback in self._subscribers:
            try:
                callback(report)
            except Exception:
                pass  # Don't let subscriber errors break the store

    def get_system_intel(self, system_name: str) -> SystemIntel | None:
        """Get current intel for a system."""
        self._prune_old()

        with self._lock:
            if system_name not in self._reports or not self._reports[system_name]:
                return None

            reports = self._reports[system_name]
            latest = reports[-1]

            # If latest report is a clear, return cleared state
            if latest.is_clear:
                return SystemIntel(
                    system_name=system_name,
                    total_hostiles=0,
                    reports=list(reports),
                    last_updated=latest.reported_at,
                    is_clear=True,
                )

            # Sum up hostiles from non-clear reports
            total = sum(r.hostile_count for r in reports if not r.is_clear)
            all_names = []
            for r in reports:
                if not r.is_clear:
                    all_names.extend(r.hostile_names)

            return SystemIntel(
                system_name=system_name,
                total_hostiles=max(total, len(set(all_names))),
                reports=list(reports),
                last_updated=latest.reported_at,
            )

    def get_all_intel(self) -> dict[str, SystemIntel]:
        """Get all current intel."""
        self._prune_old()

        result = {}
        with self._lock:
            for system_name in list(self._reports.keys()):
                intel = self.get_system_intel(system_name)
                if intel and intel.total_hostiles > 0:
                    result[system_name] = intel

        return result

    def get_hostile_systems(self) -> set[str]:
        """Get set of systems with reported hostiles."""
        self._prune_old()

        result = set()
        with self._lock:
            for system_name, reports in self._reports.items():
                if reports and not reports[-1].is_clear:
                    result.add(system_name)

        return result

    def clear_system(self, system_name: str) -> None:
        """Clear intel for a system."""
        with self._lock:
            if system_name in self._reports:
                del self._reports[system_name]

    def clear_all(self) -> None:
        """Clear all intel."""
        with self._lock:
            self._reports.clear()

    def subscribe(self, callback: Callable[[IntelReport], None]) -> None:
        """Subscribe to intel updates."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[IntelReport], None]) -> None:
        """Unsubscribe from intel updates."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _prune_old(self) -> None:
        """Remove reports older than max_age_minutes."""
        cutoff = datetime.now(UTC) - timedelta(minutes=self.max_age_minutes)

        with self._lock:
            for system_name in list(self._reports.keys()):
                self._reports[system_name] = [
                    r for r in self._reports[system_name] if r.reported_at > cutoff
                ]
                if not self._reports[system_name]:
                    del self._reports[system_name]


# Global intel store instance
_intel_store: IntelStore | None = None


def get_intel_store() -> IntelStore:
    """Get the global intel store instance."""
    global _intel_store
    if _intel_store is None:
        _intel_store = IntelStore()
    return _intel_store


def reset_intel_store() -> None:
    """Reset the global intel store (for testing)."""
    global _intel_store
    _intel_store = None


# Regex patterns for intel parsing
CLEAR_PATTERNS = [
    re.compile(r"\bclear\b", re.IGNORECASE),
    re.compile(r"\bclr\b", re.IGNORECASE),
    re.compile(r"\bnv\b", re.IGNORECASE),  # "no visual"
    re.compile(r"\bno\s*vis\b", re.IGNORECASE),
]

COUNT_PATTERN = re.compile(r"\+(\d+)")  # +1, +2, etc.

# Gate camp patterns
CAMP_PATTERNS = [
    re.compile(r"\bcamp\b", re.IGNORECASE),
    re.compile(r"\bcamping\b", re.IGNORECASE),
    re.compile(r"\bcamped\b", re.IGNORECASE),
    re.compile(r"\bgate\s*camp\b", re.IGNORECASE),
]

# Bubble patterns
BUBBLE_PATTERNS = [
    re.compile(r"\bbubble\b", re.IGNORECASE),
    re.compile(r"\bbubbled\b", re.IGNORECASE),
    re.compile(r"\bdictor\b", re.IGNORECASE),
    re.compile(r"\bhic\b", re.IGNORECASE),
]

# Fleet patterns
FLEET_PATTERNS = [
    re.compile(r"\bfleet\b", re.IGNORECASE),
    re.compile(r"\bgang\b", re.IGNORECASE),
    re.compile(r"\bgroup\b", re.IGNORECASE),
    re.compile(r"\broam\b", re.IGNORECASE),
]

# Direction patterns
DIRECTION_PATTERN = re.compile(
    r"(?:->|-->|to|toward|towards|from|inbound|outbound)\s+(\w+)",
    re.IGNORECASE,
)

# Common ship types (case-insensitive matching)
SHIP_TYPES = {
    # Frigates
    "sabre",
    "flycatcher",
    "stiletto",
    "malediction",
    "ares",
    "crow",
    "raptor",
    "crusader",
    "claw",
    "taranis",
    "atron",
    "executioner",
    "slasher",
    "condor",
    "rifter",
    "punisher",
    "merlin",
    "incursus",
    "kestrel",
    "breacher",
    "tristan",
    "hookbill",
    "firetail",
    "comet",
    "slicer",
    "dramiel",
    "daredevil",
    "worm",
    "garmur",
    "astero",
    # Destroyers
    "thrasher",
    "catalyst",
    "coercer",
    "cormorant",
    "talwar",
    "corax",
    "algos",
    "dragoon",
    "sunesis",
    # Cruisers
    "caracal",
    "stabber",
    "moa",
    "thorax",
    "vexor",
    "omen",
    "rupture",
    "bellicose",
    "arbitrator",
    "blackbird",
    "celestis",
    "scythe",
    "augoror",
    "osprey",
    "exequror",
    # Heavy Assault Cruisers
    "cerberus",
    "sacrilege",
    "vagabond",
    "ishtar",
    "deimos",
    "muninn",
    "zealot",
    "eagle",
    # Battlecruisers
    "drake",
    "hurricane",
    "harbinger",
    "brutix",
    "myrmidon",
    "prophecy",
    "ferox",
    "cyclone",
    "gnosis",
    # Command Ships
    "claymore",
    "sleipnir",
    "vulture",
    "astarte",
    "absolution",
    "damnation",
    "eos",
    "nighthawk",
    # Battleships
    "megathron",
    "hyperion",
    "dominix",
    "armageddon",
    "apocalypse",
    "abaddon",
    "raven",
    "scorpion",
    "rokh",
    "tempest",
    "typhoon",
    "maelstrom",
    "machariel",
    "nightmare",
    "bhaal",
    "vindi",
    "vindicator",
    "rattlesnake",
    "praxis",
    # Recons
    "falcon",
    "rook",
    "rapier",
    "huginn",
    "arazu",
    "lachesis",
    "pilgrim",
    "curse",
    # Interdictors
    "heretic",
    "eris",
    # Heavy Interdictors
    "onyx",
    "phobos",
    "devoter",
    "broadsword",
    # Logistics
    "scimitar",
    "basilisk",
    "guardian",
    "oneiros",
    # Carriers
    "archon",
    "thanatos",
    "chimera",
    "nidhoggur",
    # Supercarriers
    "aeon",
    "nyx",
    "wyvern",
    "hel",
    # Titans
    "avatar",
    "erebus",
    "leviathan",
    "ragnarok",
    # Other notable ships
    "tengu",
    "loki",
    "proteus",
    "legion",
    "svipul",
    "confessor",
    "jackdaw",
    "hecate",
}


def _is_valid_system(name: str) -> bool:
    """Check if a name is a valid EVE system."""
    try:
        universe = load_universe()
        return name in universe.systems
    except Exception:
        return False


def _is_hostile_name(word: str) -> bool:
    """Check if a word looks like a hostile character name."""
    # Skip common non-name words
    skip_words = {
        "in",
        "at",
        "to",
        "from",
        "with",
        "the",
        "and",
        "or",
        "a",
        "an",
        "is",
        "was",
        "gate",
        "station",
        "docked",
        "undocked",
        "local",
        "spike",
        "neutral",
        "neut",
        "red",
        "blue",
        "green",
    }

    if word.lower() in skip_words:
        return False

    # Skip if it looks like a system name
    if _is_valid_system(word):
        return False

    # Skip numbers and very short words
    if len(word) < 2 or word.isdigit():
        return False

    return True


def _detect_threat_type(text: str) -> ThreatType:
    """Detect the type of threat from intel text."""
    # Check for bubble first (most specific)
    for pattern in BUBBLE_PATTERNS:
        if pattern.search(text):
            return ThreatType.bubble

    # Check for gate camp
    for pattern in CAMP_PATTERNS:
        if pattern.search(text):
            return ThreatType.gate_camp

    # Check for fleet
    for pattern in FLEET_PATTERNS:
        if pattern.search(text):
            return ThreatType.fleet

    return ThreatType.hostile


def _detect_ship_types(text: str) -> list[str]:
    """Detect ship types mentioned in intel text."""
    words = text.lower().split()
    found = []
    for word in words:
        # Strip common suffixes/punctuation
        clean_word = word.rstrip(".,!?'\"")
        if clean_word in SHIP_TYPES:
            # Return original casing if possible
            for orig in text.split():
                if orig.lower().rstrip(".,!?'\"") == clean_word:
                    found.append(orig.rstrip(".,!?'\""))
                    break
    return found


def _detect_direction(text: str) -> str | None:
    """Detect direction of travel from intel text."""
    match = DIRECTION_PATTERN.search(text)
    if match:
        target = match.group(1)
        # Validate it's a system name
        if _is_valid_system(target):
            # Determine direction type
            full_match = match.group(0).lower()
            if "from" in full_match or "outbound" in full_match:
                return f"from {target}"
            return f"toward {target}"
    return None


def parse_intel_line(line: str, reporter: str | None = None) -> IntelReport | None:
    """
    Parse a single line of intel chat.

    Args:
        line: Raw intel channel text
        reporter: Optional reporter name

    Returns:
        IntelReport if valid intel found, None otherwise
    """
    line = line.strip()
    if not line:
        return None

    # Split into words
    words = line.split()
    if not words:
        return None

    # First word should be a system name
    system_name = None
    remaining_words = []

    # Try to find system name (may be multi-word like "New Caldari")
    for i in range(min(3, len(words)), 0, -1):
        candidate = " ".join(words[:i])
        if _is_valid_system(candidate):
            system_name = candidate
            remaining_words = words[i:]
            break

    if not system_name:
        # Try first word alone
        if _is_valid_system(words[0]):
            system_name = words[0]
            remaining_words = words[1:]
        else:
            return None

    # Check for clear report
    remaining_text = " ".join(remaining_words)
    for pattern in CLEAR_PATTERNS:
        if pattern.search(remaining_text):
            return IntelReport(
                system_name=system_name,
                hostile_count=0,
                reported_at=datetime.now(UTC),
                reporter=reporter,
                raw_text=line,
                is_clear=True,
            )

    # Detect threat type, ship types, and direction
    threat_type = _detect_threat_type(remaining_text)
    ship_types = _detect_ship_types(remaining_text)
    direction = _detect_direction(remaining_text)

    # Check for count (+1, +2, etc.)
    hostile_count = 0
    count_match = COUNT_PATTERN.search(remaining_text)
    if count_match:
        hostile_count = int(count_match.group(1))
        # Remove count from remaining for name parsing
        remaining_text = COUNT_PATTERN.sub("", remaining_text).strip()
        remaining_words = remaining_text.split()

    # Parse hostile names from remaining words
    hostile_names = [w for w in remaining_words if _is_hostile_name(w)]

    # If we have names but no count, count the names
    if hostile_names and hostile_count == 0:
        hostile_count = len(hostile_names)

    # If no count and no names, assume +1
    if hostile_count == 0 and not hostile_names:
        hostile_count = 1

    return IntelReport(
        system_name=system_name,
        hostile_count=hostile_count,
        hostile_names=hostile_names,
        reported_at=datetime.now(UTC),
        reporter=reporter,
        raw_text=line,
        threat_type=threat_type,
        ship_types=ship_types,
        direction=direction,
    )


def parse_intel_text(text: str, reporter: str | None = None) -> list[IntelReport]:
    """
    Parse multiple lines of intel text.

    Args:
        text: Multi-line intel text (e.g., from chat log)
        reporter: Optional reporter name

    Returns:
        List of parsed IntelReport objects
    """
    reports = []
    for line in text.strip().split("\n"):
        report = parse_intel_line(line, reporter)
        if report:
            reports.append(report)
    return reports


def submit_intel(text: str, reporter: str | None = None) -> list[IntelReport]:
    """
    Parse and store intel reports.

    Args:
        text: Intel text (single or multi-line)
        reporter: Optional reporter name

    Returns:
        List of successfully parsed and stored reports
    """
    reports = parse_intel_text(text, reporter)
    store = get_intel_store()
    for report in reports:
        store.add_report(report)
    return reports


def get_intel_risk_modifier(system_name: str) -> float:
    """
    Get risk modifier based on intel for a system.

    Returns a multiplier to apply to the base risk score:
    - 0 hostiles: 1.0 (no change)
    - 1 hostile: 1.5
    - 2-3 hostiles: 2.0
    - 4+ hostiles: 2.5

    Returns:
        Risk multiplier for the system
    """
    store = get_intel_store()
    intel = store.get_system_intel(system_name)

    if not intel or intel.total_hostiles == 0:
        return 1.0

    if intel.total_hostiles == 1:
        return 1.5
    elif intel.total_hostiles <= 3:
        return 2.0
    else:
        return 2.5


@dataclass
class IntelStats:
    """Statistics about current intel state."""

    total_systems: int
    total_hostiles: int
    total_reports: int
    gate_camps: int
    bubbles: int
    fleets: int
    oldest_report_seconds: float
    newest_report_seconds: float


def get_intel_stats() -> IntelStats:
    """
    Get statistics about current intel state.

    Returns:
        IntelStats with summary information
    """
    store = get_intel_store()
    all_intel = store.get_all_intel()

    if not all_intel:
        return IntelStats(
            total_systems=0,
            total_hostiles=0,
            total_reports=0,
            gate_camps=0,
            bubbles=0,
            fleets=0,
            oldest_report_seconds=0,
            newest_report_seconds=0,
        )

    total_reports = 0
    gate_camps = 0
    bubbles = 0
    fleets = 0
    oldest_time = datetime.now(UTC)
    newest_time = datetime.min.replace(tzinfo=UTC)

    for intel in all_intel.values():
        for report in intel.reports:
            total_reports += 1
            if report.threat_type == ThreatType.gate_camp:
                gate_camps += 1
            elif report.threat_type == ThreatType.bubble:
                bubbles += 1
            elif report.threat_type == ThreatType.fleet:
                fleets += 1

            if report.reported_at < oldest_time:
                oldest_time = report.reported_at
            if report.reported_at > newest_time:
                newest_time = report.reported_at

    now = datetime.now(UTC)
    return IntelStats(
        total_systems=len(all_intel),
        total_hostiles=sum(intel.total_hostiles for intel in all_intel.values()),
        total_reports=total_reports,
        gate_camps=gate_camps,
        bubbles=bubbles,
        fleets=fleets,
        oldest_report_seconds=(now - oldest_time).total_seconds() if total_reports else 0,
        newest_report_seconds=(now - newest_time).total_seconds() if total_reports else 0,
    )


def get_nearby_intel(system_name: str, max_jumps: int = 3) -> dict[str, SystemIntel]:
    """
    Get intel for systems within a certain number of jumps.

    Args:
        system_name: Center system to search from
        max_jumps: Maximum jumps to search (default 3)

    Returns:
        Dict mapping system names to their intel
    """
    universe = load_universe()

    if system_name not in universe.systems:
        return {}

    # Build adjacency map from gates
    adjacency: dict[str, set[str]] = {}
    for gate in universe.gates:
        if gate.from_system not in adjacency:
            adjacency[gate.from_system] = set()
        if gate.to_system not in adjacency:
            adjacency[gate.to_system] = set()
        adjacency[gate.from_system].add(gate.to_system)
        adjacency[gate.to_system].add(gate.from_system)

    # BFS to find nearby systems
    visited = {system_name}
    frontier = [system_name]
    current_jump = 0

    while frontier and current_jump < max_jumps:
        next_frontier = []
        for sys_name in frontier:
            neighbors = adjacency.get(sys_name, set())
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier
        current_jump += 1

    # Get intel for all visited systems
    store = get_intel_store()
    result = {}
    for sys_name in visited:
        intel = store.get_system_intel(sys_name)
        if intel and intel.total_hostiles > 0:
            result[sys_name] = intel

    return result
