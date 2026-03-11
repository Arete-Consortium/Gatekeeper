"""Intel chat parser service.

Parses pasted EVE Online local/intel chat text to extract system names
and their status (clear, hostile, unknown). Matches against the known
universe system list for validation.
"""

import re

from ..models.intel import IntelParseResponse, ParsedSystem
from .data_loader import load_universe

# EVE chat timestamp pattern: [2024.01.15 19:30:45]
TIMESTAMP_PATTERN = re.compile(r"^\[[\d.:\s]+\]\s*")

# Count patterns: +N, hostile N, N hostile, N red, N neut
COUNT_PATTERN = re.compile(r"\+(\d+)")
HOSTILE_COUNT_PATTERN = re.compile(
    r"(?:hostile|red|neut|enemy)\s+(\d+)|(\d+)\s+(?:hostile|hostiles|red|reds|neut|neuts|enemy|enemies)",
    re.IGNORECASE,
)

# Status keywords
CLEAR_KEYWORDS = {"clear", "clr", "nv", "empty", "clean", "safe"}
HOSTILE_KEYWORDS = {
    "hostile",
    "hostiles",
    "red",
    "reds",
    "neut",
    "neuts",
    "enemy",
    "enemies",
    "hot",
    "spike",
}

# Chat separator: "CharacterName > message" pattern
CHAT_SEPARATOR = re.compile(r"^([^>]+)>\s*(.*)$")

# Whitespace/tab separator for "CharacterName\tSystemName" format
TAB_SEPARATOR = re.compile(r"\t+|\s{2,}")


def _build_system_lookup() -> dict[str, tuple[str, int]]:
    """Build case-insensitive system name lookup.

    Returns:
        Dict mapping lowercase system name to (canonical_name, system_id).
    """
    universe = load_universe()
    lookup: dict[str, tuple[str, int]] = {}
    for name, system in universe.systems.items():
        lookup[name.lower()] = (name, system.id)
    return lookup


def _strip_timestamp(line: str) -> str:
    """Remove EVE chat timestamp from start of line."""
    return TIMESTAMP_PATTERN.sub("", line).strip()


def _detect_status(text: str) -> tuple[str, int]:
    """Detect status and hostile count from text.

    Returns:
        Tuple of (status, hostile_count).
    """
    text_lower = text.lower().strip()
    words = set(text_lower.split())

    # Check for clear indicators
    if words & CLEAR_KEYWORDS:
        return "clear", 0

    # Check for explicit count: +N
    count_match = COUNT_PATTERN.search(text)
    if count_match:
        return "hostile", int(count_match.group(1))

    # Check for "hostile N" or "N hostile" patterns
    hostile_match = HOSTILE_COUNT_PATTERN.search(text)
    if hostile_match:
        count = int(hostile_match.group(1) or hostile_match.group(2))
        return "hostile", count

    # Check for hostile keywords without count
    if words & HOSTILE_KEYWORDS:
        return "hostile", 1

    # Default: unknown status
    return "unknown", 0


def _find_system_in_text(
    text: str, system_lookup: dict[str, tuple[str, int]]
) -> tuple[str, int, str] | None:
    """Try to find a system name in text.

    Tries multi-word matches first (up to 3 words), then single words.
    System names like "EC-P8R" and "1DQ1-A" contain dashes and numbers.

    Returns:
        Tuple of (system_name, system_id, remaining_text) or None.
    """
    words = text.split()
    if not words:
        return None

    # Try multi-word matches (longest first) from start of text
    for length in range(min(4, len(words)), 0, -1):
        candidate = " ".join(words[:length])
        key = candidate.lower()
        if key in system_lookup:
            canonical, sys_id = system_lookup[key]
            remaining = " ".join(words[length:])
            return canonical, sys_id, remaining

    # Try each individual word (for cases like "SomePlayer > Jita hostile")
    for i, word in enumerate(words):
        key = word.lower()
        if key in system_lookup:
            canonical, sys_id = system_lookup[key]
            remaining = " ".join(words[:i] + words[i + 1 :])
            return canonical, sys_id, remaining

    return None


def parse_intel_text(text: str) -> IntelParseResponse:
    """Parse intel/local chat text and extract system information.

    Handles common EVE intel formats:
    - [timestamp] CharacterName > SystemName status
    - CharacterName  SystemName
    - SystemName clear
    - SystemName  hostile 3
    - SystemName +1
    - SystemName

    Args:
        text: Raw intel/local chat text (multi-line).

    Returns:
        IntelParseResponse with parsed systems and unknown lines.
    """
    system_lookup = _build_system_lookup()
    systems: list[ParsedSystem] = []
    unknown_lines: list[str] = []
    seen_systems: dict[str, int] = {}  # Track index for dedup/update

    lines = text.strip().split("\n")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Strip timestamp
        line = _strip_timestamp(line)
        if not line:
            continue

        # Try chat separator format: "Name > message"
        chat_match = CHAT_SEPARATOR.match(line)
        if chat_match:
            message = chat_match.group(2).strip()
            if not message:
                unknown_lines.append(raw_line.strip())
                continue
            search_text = message
        else:
            # Try tab/multi-space separated format
            parts = TAB_SEPARATOR.split(line)
            if len(parts) >= 2:
                # Could be "CharacterName  SystemName" or "SystemName  status"
                search_text = line
            else:
                search_text = line

        # Find system name in the text
        result = _find_system_in_text(search_text, system_lookup)

        if result:
            system_name, system_id, remaining = result
            status, hostile_count = _detect_status(remaining)

            if system_name in seen_systems:
                # Update existing entry if this one has more info
                idx = seen_systems[system_name]
                existing = systems[idx]
                if status == "hostile" and existing.status != "hostile":
                    systems[idx] = ParsedSystem(
                        system_name=system_name,
                        system_id=system_id,
                        status=status,
                        hostile_count=max(hostile_count, existing.hostile_count),
                        mentioned_at=raw_line.strip(),
                    )
                elif status == "hostile" and hostile_count > existing.hostile_count:
                    systems[idx] = ParsedSystem(
                        system_name=system_name,
                        system_id=system_id,
                        status=status,
                        hostile_count=hostile_count,
                        mentioned_at=raw_line.strip(),
                    )
            else:
                seen_systems[system_name] = len(systems)
                systems.append(
                    ParsedSystem(
                        system_name=system_name,
                        system_id=system_id,
                        status=status,
                        hostile_count=hostile_count,
                        mentioned_at=raw_line.strip(),
                    )
                )
        else:
            unknown_lines.append(raw_line.strip())

    return IntelParseResponse(systems=systems, unknown_lines=unknown_lines)
