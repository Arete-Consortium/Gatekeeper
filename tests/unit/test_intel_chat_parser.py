"""Unit tests for intel chat parser service."""

from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.intel_chat_parser import (
    _detect_status,
    _find_system_in_text,
    _strip_timestamp,
    parse_intel_text,
)


@pytest.fixture
def mock_universe():
    """Mock universe with test systems."""
    mock = MagicMock()
    mock.systems = {
        "Jita": MagicMock(id=30000142, name="Jita"),
        "Amarr": MagicMock(id=30002187, name="Amarr"),
        "HED-GP": MagicMock(id=30001161, name="HED-GP"),
        "EC-P8R": MagicMock(id=30004608, name="EC-P8R"),
        "1DQ1-A": MagicMock(id=30004759, name="1DQ1-A"),
        "Tama": MagicMock(id=30002813, name="Tama"),
        "Rancer": MagicMock(id=30003504, name="Rancer"),
        "New Caldari": MagicMock(id=30000139, name="New Caldari"),
        "Perimeter": MagicMock(id=30000144, name="Perimeter"),
    }
    return mock


class TestStripTimestamp:
    """Tests for timestamp stripping."""

    def test_strips_eve_timestamp(self):
        """Test removing EVE chat timestamp."""
        result = _strip_timestamp("[2024.01.15 19:30:45] some text")
        assert result == "some text"

    def test_no_timestamp(self):
        """Test line without timestamp passes through."""
        result = _strip_timestamp("some text")
        assert result == "some text"

    def test_empty_after_timestamp(self):
        """Test empty result after stripping timestamp."""
        result = _strip_timestamp("[2024.01.15 19:30:45]")
        assert result == ""


class TestDetectStatus:
    """Tests for status detection from text."""

    def test_clear_keyword(self):
        """Test 'clear' status detection."""
        status, count = _detect_status("clear")
        assert status == "clear"
        assert count == 0

    def test_clr_keyword(self):
        """Test 'clr' abbreviation."""
        status, count = _detect_status("clr")
        assert status == "clear"
        assert count == 0

    def test_nv_keyword(self):
        """Test 'nv' (no visual) status."""
        status, count = _detect_status("nv")
        assert status == "clear"
        assert count == 0

    def test_hostile_plus_count(self):
        """Test '+N' format."""
        status, count = _detect_status("+3")
        assert status == "hostile"
        assert count == 3

    def test_hostile_keyword(self):
        """Test 'hostile' keyword without count."""
        status, count = _detect_status("hostile")
        assert status == "hostile"
        assert count == 1

    def test_hostile_with_count(self):
        """Test 'hostile 5' format."""
        status, count = _detect_status("hostile 5")
        assert status == "hostile"
        assert count == 5

    def test_count_before_hostile(self):
        """Test '3 hostiles' format."""
        status, count = _detect_status("3 hostiles")
        assert status == "hostile"
        assert count == 3

    def test_red_keyword(self):
        """Test 'red' keyword."""
        status, count = _detect_status("red")
        assert status == "hostile"
        assert count == 1

    def test_neut_keyword(self):
        """Test 'neut' keyword."""
        status, count = _detect_status("neut")
        assert status == "hostile"
        assert count == 1

    def test_spike_keyword(self):
        """Test 'spike' keyword."""
        status, count = _detect_status("spike")
        assert status == "hostile"
        assert count == 1

    def test_unknown_text(self):
        """Test unknown status for unrecognized text."""
        status, count = _detect_status("something random")
        assert status == "unknown"
        assert count == 0

    def test_empty_text(self):
        """Test empty text returns unknown."""
        status, count = _detect_status("")
        assert status == "unknown"
        assert count == 0


class TestFindSystemInText:
    """Tests for system name extraction."""

    def test_simple_system(self, mock_universe):
        """Test finding a simple system name."""
        lookup = {"jita": ("Jita", 30000142)}
        result = _find_system_in_text("Jita clear", lookup)
        assert result is not None
        assert result[0] == "Jita"
        assert result[1] == 30000142
        assert result[2] == "clear"

    def test_dashed_system(self, mock_universe):
        """Test finding system with dashes like HED-GP."""
        lookup = {"hed-gp": ("HED-GP", 30001161)}
        result = _find_system_in_text("HED-GP hostile 3", lookup)
        assert result is not None
        assert result[0] == "HED-GP"

    def test_alphanumeric_system(self, mock_universe):
        """Test finding system with numbers like 1DQ1-A."""
        lookup = {"1dq1-a": ("1DQ1-A", 30004759)}
        result = _find_system_in_text("1DQ1-A +5", lookup)
        assert result is not None
        assert result[0] == "1DQ1-A"

    def test_multiword_system(self, mock_universe):
        """Test finding multi-word system name."""
        lookup = {"new caldari": ("New Caldari", 30000139)}
        result = _find_system_in_text("New Caldari clear", lookup)
        assert result is not None
        assert result[0] == "New Caldari"

    def test_system_in_middle(self, mock_universe):
        """Test finding system name in middle of text."""
        lookup = {"jita": ("Jita", 30000142)}
        result = _find_system_in_text("pilot spotted in Jita hostile", lookup)
        assert result is not None
        assert result[0] == "Jita"

    def test_no_system_found(self, mock_universe):
        """Test no system found in text."""
        lookup = {"jita": ("Jita", 30000142)}
        result = _find_system_in_text("random text here", lookup)
        assert result is None

    def test_case_insensitive(self, mock_universe):
        """Test case-insensitive matching."""
        lookup = {"jita": ("Jita", 30000142)}
        result = _find_system_in_text("JITA clear", lookup)
        assert result is not None
        assert result[0] == "Jita"


class TestParseIntelText:
    """Tests for full intel text parsing."""

    def test_simple_system_clear(self, mock_universe):
        """Test parsing 'System clear'."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("Jita clear")

        assert len(result.systems) == 1
        assert result.systems[0].system_name == "Jita"
        assert result.systems[0].status == "clear"
        assert result.systems[0].hostile_count == 0
        assert len(result.unknown_lines) == 0

    def test_system_hostile_count(self, mock_universe):
        """Test parsing 'System +N' hostile count."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("HED-GP +5")

        assert len(result.systems) == 1
        assert result.systems[0].system_name == "HED-GP"
        assert result.systems[0].status == "hostile"
        assert result.systems[0].hostile_count == 5

    def test_system_hostile_keyword(self, mock_universe):
        """Test parsing 'System hostile' without count."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("EC-P8R hostile")

        assert len(result.systems) == 1
        assert result.systems[0].status == "hostile"
        assert result.systems[0].hostile_count == 1

    def test_multiline_parsing(self, mock_universe):
        """Test parsing multiple lines of intel."""
        text = """Jita clear
HED-GP +3
1DQ1-A hostile
Amarr nv"""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        assert len(result.systems) == 4
        assert result.systems[0].status == "clear"
        assert result.systems[1].status == "hostile"
        assert result.systems[1].hostile_count == 3
        assert result.systems[2].status == "hostile"
        assert result.systems[3].status == "clear"

    def test_chat_format_with_timestamp(self, mock_universe):
        """Test parsing EVE chat format with timestamps."""
        text = "[2024.01.15 19:30:45] PilotName > Jita clear"
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        assert len(result.systems) == 1
        assert result.systems[0].system_name == "Jita"
        assert result.systems[0].status == "clear"

    def test_chat_format_name_separator(self, mock_universe):
        """Test parsing 'Name > SystemName status' format."""
        text = "SomePilot > Rancer hostile 3"
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        assert len(result.systems) == 1
        assert result.systems[0].system_name == "Rancer"
        assert result.systems[0].status == "hostile"
        assert result.systems[0].hostile_count == 3

    def test_unknown_lines_tracked(self, mock_universe):
        """Test that unrecognized lines are tracked."""
        text = """Jita clear
this is random gibberish
another unknown line"""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        assert len(result.systems) == 1
        assert len(result.unknown_lines) == 2

    def test_empty_text(self, mock_universe):
        """Test parsing empty text."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("")

        assert len(result.systems) == 0
        assert len(result.unknown_lines) == 0

    def test_system_dedup(self, mock_universe):
        """Test that duplicate system mentions are deduplicated."""
        text = """Jita clear
Jita hostile"""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        # Should have only one entry for Jita, updated to hostile
        assert len(result.systems) == 1
        assert result.systems[0].system_name == "Jita"
        assert result.systems[0].status == "hostile"

    def test_system_id_populated(self, mock_universe):
        """Test that system_id is correctly populated."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("Jita clear")

        assert result.systems[0].system_id == 30000142

    def test_mentioned_at_preserves_raw(self, mock_universe):
        """Test that mentioned_at preserves the raw input line."""
        raw = "  [2024.01.15 19:30:45] PilotName > Jita +2  "
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(raw)

        assert result.systems[0].mentioned_at == raw.strip()

    def test_red_keyword(self, mock_universe):
        """Test 'red' keyword triggers hostile status."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("Tama red")

        assert result.systems[0].status == "hostile"

    def test_neut_with_count(self, mock_universe):
        """Test '3 neuts' format."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("Rancer 3 neuts")

        assert result.systems[0].status == "hostile"
        assert result.systems[0].hostile_count == 3

    def test_system_name_only_unknown_status(self, mock_universe):
        """Test that system name alone gives unknown status."""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text("Perimeter")

        assert len(result.systems) == 1
        assert result.systems[0].status == "unknown"
        assert result.systems[0].hostile_count == 0

    def test_tab_separated_format(self, mock_universe):
        """Test tab-separated local chat format."""
        text = "SomePilot\tJita"
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        assert len(result.systems) == 1
        assert result.systems[0].system_name == "Jita"

    def test_multiple_systems_different_status(self, mock_universe):
        """Test parsing multiple systems with different statuses."""
        text = """Jita clear
Tama +2
Rancer hostile
Amarr nv
EC-P8R spike"""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        assert len(result.systems) == 5
        statuses = {s.system_name: s.status for s in result.systems}
        assert statuses["Jita"] == "clear"
        assert statuses["Tama"] == "hostile"
        assert statuses["Rancer"] == "hostile"
        assert statuses["Amarr"] == "clear"
        assert statuses["EC-P8R"] == "hostile"

    def test_hostile_count_updated_on_dedup(self, mock_universe):
        """Test that dedup keeps the higher hostile count."""
        text = """Jita +2
Jita +5"""
        with patch(
            "backend.app.services.intel_chat_parser.load_universe",
            return_value=mock_universe,
        ):
            result = parse_intel_text(text)

        assert len(result.systems) == 1
        assert result.systems[0].hostile_count == 5
