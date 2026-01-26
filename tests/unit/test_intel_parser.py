"""Unit tests for intel channel parser."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.intel_parser import (
    IntelReport,
    IntelStore,
    SystemIntel,
    get_intel_risk_modifier,
    get_intel_store,
    parse_intel_line,
    parse_intel_text,
    reset_intel_store,
    submit_intel,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the global intel store before each test."""
    reset_intel_store()
    yield
    reset_intel_store()


@pytest.fixture
def mock_universe():
    """Mock universe with test systems."""
    mock = MagicMock()
    # Systems dict that supports 'in' operator
    mock.systems = {
        "Jita": MagicMock(id=30000142, name="Jita"),
        "Amarr": MagicMock(id=30002187, name="Amarr"),
        "Rancer": MagicMock(id=30003504, name="Rancer"),
        "Tama": MagicMock(id=30002813, name="Tama"),
        "New Caldari": MagicMock(id=30000139, name="New Caldari"),
    }
    return mock


class TestIntelReport:
    """Tests for IntelReport dataclass."""

    def test_basic_creation(self):
        """Test creating a basic report."""
        report = IntelReport(
            system_name="Jita",
            hostile_count=1,
        )
        assert report.system_name == "Jita"
        assert report.hostile_count == 1
        assert report.hostile_names == []
        assert report.is_clear is False

    def test_with_hostile_names(self):
        """Test report with hostile names."""
        report = IntelReport(
            system_name="Jita",
            hostile_count=2,
            hostile_names=["Hostile1", "Hostile2"],
        )
        assert report.hostile_count == 2
        assert len(report.hostile_names) == 2

    def test_clear_report(self):
        """Test clear report."""
        report = IntelReport(
            system_name="Jita",
            hostile_count=0,
            is_clear=True,
        )
        assert report.hostile_count == 0
        assert report.is_clear is True

    def test_with_reporter(self):
        """Test report with reporter name."""
        report = IntelReport(
            system_name="Jita",
            hostile_count=1,
            reporter="TestPilot",
        )
        assert report.reporter == "TestPilot"


class TestIntelStore:
    """Tests for IntelStore class."""

    def test_add_and_get_report(self):
        """Test adding and retrieving a report."""
        store = IntelStore()
        report = IntelReport(system_name="Jita", hostile_count=1)

        store.add_report(report)
        intel = store.get_system_intel("Jita")

        assert intel is not None
        assert intel.system_name == "Jita"
        assert intel.total_hostiles == 1

    def test_multiple_reports_same_system(self):
        """Test multiple reports for same system aggregate."""
        store = IntelStore()
        store.add_report(IntelReport(system_name="Jita", hostile_count=1))
        store.add_report(IntelReport(system_name="Jita", hostile_count=2))

        intel = store.get_system_intel("Jita")
        assert intel.total_hostiles == 3

    def test_clear_report_resets(self):
        """Test that clear report resets hostile count."""
        store = IntelStore()
        store.add_report(IntelReport(system_name="Jita", hostile_count=3))
        store.add_report(IntelReport(system_name="Jita", hostile_count=0, is_clear=True))

        intel = store.get_system_intel("Jita")
        assert intel.total_hostiles == 0
        assert intel.is_clear is True

    def test_get_nonexistent_system(self):
        """Test getting intel for nonexistent system."""
        store = IntelStore()
        intel = store.get_system_intel("NonExistent")
        assert intel is None

    def test_get_all_intel(self):
        """Test getting all intel."""
        store = IntelStore()
        store.add_report(IntelReport(system_name="Jita", hostile_count=1))
        store.add_report(IntelReport(system_name="Amarr", hostile_count=2))

        all_intel = store.get_all_intel()
        assert len(all_intel) == 2
        assert "Jita" in all_intel
        assert "Amarr" in all_intel

    def test_get_hostile_systems(self):
        """Test getting list of hostile systems."""
        store = IntelStore()
        store.add_report(IntelReport(system_name="Jita", hostile_count=1))
        store.add_report(IntelReport(system_name="Amarr", hostile_count=2))
        store.add_report(IntelReport(system_name="Rancer", hostile_count=0, is_clear=True))

        hostile_systems = store.get_hostile_systems()
        assert "Jita" in hostile_systems
        assert "Amarr" in hostile_systems
        assert "Rancer" not in hostile_systems

    def test_clear_system(self):
        """Test clearing a specific system."""
        store = IntelStore()
        store.add_report(IntelReport(system_name="Jita", hostile_count=1))
        store.add_report(IntelReport(system_name="Amarr", hostile_count=2))

        store.clear_system("Jita")

        assert store.get_system_intel("Jita") is None
        assert store.get_system_intel("Amarr") is not None

    def test_clear_all(self):
        """Test clearing all intel."""
        store = IntelStore()
        store.add_report(IntelReport(system_name="Jita", hostile_count=1))
        store.add_report(IntelReport(system_name="Amarr", hostile_count=2))

        store.clear_all()

        assert store.get_system_intel("Jita") is None
        assert store.get_system_intel("Amarr") is None

    def test_old_reports_pruned(self):
        """Test that old reports are automatically pruned."""
        store = IntelStore(max_age_minutes=1)

        old_report = IntelReport(system_name="Jita", hostile_count=1)
        old_report.reported_at = datetime.now(UTC) - timedelta(minutes=5)

        store._reports["Jita"].append(old_report)
        store._prune_old()

        assert store.get_system_intel("Jita") is None

    def test_max_reports_per_system(self):
        """Test that max reports per system is enforced."""
        store = IntelStore(max_reports_per_system=3)

        for _ in range(5):
            store.add_report(IntelReport(system_name="Jita", hostile_count=1))

        intel = store.get_system_intel("Jita")
        assert len(intel.reports) == 3

    def test_subscribe_callback(self):
        """Test subscription callbacks are called."""
        store = IntelStore()
        callback_data = []

        def callback(report):
            callback_data.append(report)

        store.subscribe(callback)
        store.add_report(IntelReport(system_name="Jita", hostile_count=1))

        assert len(callback_data) == 1
        assert callback_data[0].system_name == "Jita"

    def test_unsubscribe_callback(self):
        """Test unsubscription removes callback."""
        store = IntelStore()
        callback_data = []

        def callback(report):
            callback_data.append(report)

        store.subscribe(callback)
        store.unsubscribe(callback)
        store.add_report(IntelReport(system_name="Jita", hostile_count=1))

        assert len(callback_data) == 0


class TestParseIntelLine:
    """Tests for parse_intel_line function."""

    def test_system_plus_one(self, mock_universe):
        """Test parsing 'System +1' format."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita +1")

        assert report is not None
        assert report.system_name == "Jita"
        assert report.hostile_count == 1

    def test_system_plus_many(self, mock_universe):
        """Test parsing 'System +N' format."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Rancer +5")

        assert report is not None
        assert report.hostile_count == 5

    def test_system_clear(self, mock_universe):
        """Test parsing 'System clear' format."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita clear")

        assert report is not None
        assert report.hostile_count == 0
        assert report.is_clear is True

    def test_system_clr(self, mock_universe):
        """Test parsing 'System clr' format."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita clr")

        assert report is not None
        assert report.is_clear is True

    def test_system_nv(self, mock_universe):
        """Test parsing 'System nv' (no visual) format."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita nv")

        assert report is not None
        assert report.is_clear is True

    def test_system_with_hostile_name(self, mock_universe):
        """Test parsing 'System HostileName' format."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita EvilPilot")

        assert report is not None
        assert report.hostile_count == 1
        assert "EvilPilot" in report.hostile_names

    def test_system_with_multiple_names(self, mock_universe):
        """Test parsing 'System Name1 Name2' format."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita Hostile1 Hostile2")

        assert report is not None
        assert report.hostile_count == 2
        assert len(report.hostile_names) == 2

    def test_system_alone_implies_one(self, mock_universe):
        """Test that system name alone implies +1 hostile."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita")

        assert report is not None
        assert report.hostile_count == 1

    def test_multiword_system_name(self, mock_universe):
        """Test parsing multi-word system names."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("New Caldari +2")

        assert report is not None
        assert report.system_name == "New Caldari"
        assert report.hostile_count == 2

    def test_invalid_system_returns_none(self, mock_universe):
        """Test that invalid system names return None."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("InvalidSystem +1")

        assert report is None

    def test_empty_line_returns_none(self, mock_universe):
        """Test that empty lines return None."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("")

        assert report is None

    def test_with_reporter(self, mock_universe):
        """Test parsing with reporter name."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita +1", reporter="TestPilot")

        assert report is not None
        assert report.reporter == "TestPilot"

    def test_raw_text_preserved(self, mock_universe):
        """Test that raw text is preserved."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita +1")

        assert report.raw_text == "Jita +1"

    def test_skips_common_words(self, mock_universe):
        """Test that common words are not treated as hostile names."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita gate spike")

        assert report is not None
        # "gate" and "spike" should be filtered out
        assert "gate" not in report.hostile_names
        assert "spike" not in report.hostile_names


class TestParseIntelText:
    """Tests for parse_intel_text function (multiline)."""

    def test_multiline_parsing(self, mock_universe):
        """Test parsing multiple lines."""
        text = """Jita +1
Amarr +2
Rancer clear"""

        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            reports = parse_intel_text(text)

        assert len(reports) == 3
        assert reports[0].system_name == "Jita"
        assert reports[1].system_name == "Amarr"
        assert reports[2].is_clear is True

    def test_skips_invalid_lines(self, mock_universe):
        """Test that invalid lines are skipped."""
        text = """Jita +1
InvalidSystem +1
Amarr +2"""

        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            reports = parse_intel_text(text)

        assert len(reports) == 2

    def test_empty_text(self, mock_universe):
        """Test parsing empty text."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            reports = parse_intel_text("")

        assert len(reports) == 0


class TestSubmitIntel:
    """Tests for submit_intel function."""

    def test_submit_stores_reports(self, mock_universe):
        """Test that submit_intel stores reports in the global store."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            reports = submit_intel("Jita +1")

        assert len(reports) == 1

        store = get_intel_store()
        intel = store.get_system_intel("Jita")
        assert intel is not None
        assert intel.total_hostiles == 1

    def test_submit_multiple_lines(self, mock_universe):
        """Test submitting multiple lines at once."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita +1\nAmarr +2")

        store = get_intel_store()
        assert store.get_system_intel("Jita") is not None
        assert store.get_system_intel("Amarr") is not None


class TestGetIntelRiskModifier:
    """Tests for get_intel_risk_modifier function."""

    def test_no_intel_returns_one(self):
        """Test that no intel returns modifier of 1.0."""
        modifier = get_intel_risk_modifier("NonExistent")
        assert modifier == 1.0

    def test_one_hostile(self, mock_universe):
        """Test modifier for one hostile."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita +1")

        modifier = get_intel_risk_modifier("Jita")
        assert modifier == 1.5

    def test_two_hostiles(self, mock_universe):
        """Test modifier for 2-3 hostiles."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita +2")

        modifier = get_intel_risk_modifier("Jita")
        assert modifier == 2.0

    def test_three_hostiles(self, mock_universe):
        """Test modifier for 2-3 hostiles."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita +3")

        modifier = get_intel_risk_modifier("Jita")
        assert modifier == 2.0

    def test_many_hostiles(self, mock_universe):
        """Test modifier for 4+ hostiles."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita +5")

        modifier = get_intel_risk_modifier("Jita")
        assert modifier == 2.5

    def test_cleared_system(self, mock_universe):
        """Test modifier for cleared system."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita +3")
            submit_intel("Jita clear")

        modifier = get_intel_risk_modifier("Jita")
        assert modifier == 1.0


class TestSystemIntel:
    """Tests for SystemIntel dataclass."""

    def test_age_seconds(self):
        """Test age_seconds property."""
        past_time = datetime.now(UTC) - timedelta(seconds=30)
        intel = SystemIntel(
            system_name="Jita",
            total_hostiles=1,
            reports=[],
            last_updated=past_time,
        )

        # Age should be approximately 30 seconds
        assert 29 <= intel.age_seconds <= 35


class TestGetIntelStore:
    """Tests for get_intel_store singleton."""

    def test_returns_same_instance(self):
        """Test that get_intel_store returns same instance."""
        store1 = get_intel_store()
        store2 = get_intel_store()
        assert store1 is store2

    def test_reset_creates_new_instance(self):
        """Test that reset creates new instance."""
        store1 = get_intel_store()
        reset_intel_store()
        store2 = get_intel_store()
        assert store1 is not store2


class TestThreatTypeDetection:
    """Tests for threat type detection."""

    def test_gate_camp_detection(self, mock_universe):
        """Test gate camp detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita camp")

        from backend.app.services.intel_parser import ThreatType

        assert report.threat_type == ThreatType.gate_camp

    def test_gate_camp_with_gatecamp(self, mock_universe):
        """Test gatecamp keyword."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita gatecamp")

        from backend.app.services.intel_parser import ThreatType

        assert report.threat_type == ThreatType.gate_camp

    def test_bubble_detection(self, mock_universe):
        """Test bubble detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita bubble")

        from backend.app.services.intel_parser import ThreatType

        assert report.threat_type == ThreatType.bubble

    def test_dictor_bubble(self, mock_universe):
        """Test dictor implies bubble."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita dictor")

        from backend.app.services.intel_parser import ThreatType

        assert report.threat_type == ThreatType.bubble

    def test_fleet_detection(self, mock_universe):
        """Test fleet detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita fleet")

        from backend.app.services.intel_parser import ThreatType

        assert report.threat_type == ThreatType.fleet

    def test_gang_detection(self, mock_universe):
        """Test gang as fleet."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita gang")

        from backend.app.services.intel_parser import ThreatType

        assert report.threat_type == ThreatType.fleet

    def test_default_hostile(self, mock_universe):
        """Test default threat type is hostile."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita +1")

        from backend.app.services.intel_parser import ThreatType

        assert report.threat_type == ThreatType.hostile


class TestShipTypeDetection:
    """Tests for ship type detection."""

    def test_sabre_detection(self, mock_universe):
        """Test Sabre detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita Sabre")

        assert "Sabre" in report.ship_types

    def test_multiple_ships(self, mock_universe):
        """Test multiple ship types."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita Sabre Cerberus")

        assert "Sabre" in report.ship_types
        assert "Cerberus" in report.ship_types

    def test_case_insensitive(self, mock_universe):
        """Test case insensitive ship detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita sabre CERBERUS")

        # Should preserve original casing
        assert len(report.ship_types) == 2

    def test_no_ships(self, mock_universe):
        """Test no ship types detected."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita +3")

        assert report.ship_types == []


class TestDirectionDetection:
    """Tests for direction detection."""

    def test_direction_toward(self, mock_universe):
        """Test 'toward' direction detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita toward Amarr")

        assert report.direction == "toward Amarr"

    def test_direction_to(self, mock_universe):
        """Test 'to' direction detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita to Amarr")

        assert report.direction == "toward Amarr"

    def test_direction_arrow(self, mock_universe):
        """Test '->' direction detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita -> Amarr")

        assert report.direction == "toward Amarr"

    def test_direction_from(self, mock_universe):
        """Test 'from' direction detection."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita from Amarr")

        assert report.direction == "from Amarr"

    def test_no_direction(self, mock_universe):
        """Test no direction detected."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita +3")

        assert report.direction is None

    def test_invalid_destination(self, mock_universe):
        """Test invalid destination system."""
        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            report = parse_intel_line("Jita toward InvalidSystem")

        assert report.direction is None


class TestGetIntelStats:
    """Tests for get_intel_stats function."""

    def test_empty_stats(self):
        """Test stats with no intel."""
        from backend.app.services.intel_parser import get_intel_stats

        stats = get_intel_stats()
        assert stats.total_systems == 0
        assert stats.total_hostiles == 0
        assert stats.total_reports == 0

    def test_stats_with_reports(self, mock_universe):
        """Test stats with multiple reports."""
        from backend.app.services.intel_parser import get_intel_stats

        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita +3")
            submit_intel("Amarr +2")
            submit_intel("Rancer camp")
            submit_intel("Tama bubble")

        stats = get_intel_stats()
        assert stats.total_systems == 4
        assert stats.total_hostiles >= 6
        assert stats.total_reports == 4
        assert stats.gate_camps == 1
        assert stats.bubbles == 1

    def test_stats_fleet_count(self, mock_universe):
        """Test fleet count in stats."""
        from backend.app.services.intel_parser import get_intel_stats

        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Jita fleet")
            submit_intel("Amarr gang")

        stats = get_intel_stats()
        assert stats.fleets == 2


class TestGetNearbyIntel:
    """Tests for get_nearby_intel function."""

    def test_nearby_intel_empty(self):
        """Test nearby intel with no intel."""
        from backend.app.services.intel_parser import get_nearby_intel

        with patch("backend.app.services.intel_parser.load_universe") as mock_load:
            mock = MagicMock()
            jita = MagicMock()
            jita.stargates = {"gate1": "Perimeter"}
            mock.systems = {"Jita": jita, "Perimeter": MagicMock(stargates={})}
            mock_load.return_value = mock

            result = get_nearby_intel("Jita", max_jumps=2)

        assert result == {}

    def test_nearby_intel_invalid_system(self):
        """Test nearby intel with invalid center system."""
        from backend.app.services.intel_parser import get_nearby_intel

        with patch("backend.app.services.intel_parser.load_universe") as mock_load:
            mock = MagicMock()
            mock.systems = {}
            mock_load.return_value = mock

            result = get_nearby_intel("InvalidSystem", max_jumps=2)

        assert result == {}

    def test_nearby_intel_finds_hostiles(self, mock_universe):
        """Test nearby intel finds hostiles in range."""
        from backend.app.services.intel_parser import get_nearby_intel

        # Set up mock universe with stargates
        jita = MagicMock(stargates={"gate1": "Amarr"})
        amarr = MagicMock(stargates={"gate1": "Jita"})
        mock_universe.systems = {"Jita": jita, "Amarr": amarr}

        with patch("backend.app.services.intel_parser.load_universe", return_value=mock_universe):
            submit_intel("Amarr +3")

            result = get_nearby_intel("Jita", max_jumps=1)

        assert "Amarr" in result
        assert result["Amarr"].total_hostiles == 3
