"""Tests for starmap ship data module."""

import sys
from pathlib import Path

# Direct import to avoid circular dependency through planner
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

# Import directly from the module file to avoid __init__ imports
import importlib.util

ship_data_path = (
    Path(__file__).parent.parent.parent / "backend" / "starmap" / "jump_planner" / "ship_data.py"
)
spec = importlib.util.spec_from_file_location("ship_data", ship_data_path)
ship_data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ship_data)

CAPITAL_SHIPS = ship_data.CAPITAL_SHIPS
CapitalShipData = ship_data.CapitalShipData
FuelType = ship_data.FuelType
calculate_effective_range = ship_data.calculate_effective_range
calculate_fuel_consumption = ship_data.calculate_fuel_consumption
get_ship_base_range = ship_data.get_ship_base_range
get_ship_fuel_need = ship_data.get_ship_fuel_need


class TestFuelType:
    """Tests for FuelType enum."""

    def test_all_fuel_types_defined(self):
        """All four isotope types should be defined."""
        assert hasattr(FuelType, "HELIUM")
        assert hasattr(FuelType, "HYDROGEN")
        assert hasattr(FuelType, "NITROGEN")
        assert hasattr(FuelType, "OXYGEN")

    def test_fuel_type_ids(self):
        """Fuel types should have correct type IDs."""
        assert FuelType.HELIUM.value == 16274
        assert FuelType.HYDROGEN.value == 17889
        assert FuelType.NITROGEN.value == 17888
        assert FuelType.OXYGEN.value == 17887


class TestCapitalShipData:
    """Tests for CapitalShipData dataclass."""

    def test_create_ship_data(self):
        """Should create ship data with required fields."""
        ship = CapitalShipData(
            type_id=12345,
            name="Test Ship",
            base_range_ly=5.0,
            base_fuel_need=1000,
            fuel_type=FuelType.HELIUM,
        )

        assert ship.type_id == 12345
        assert ship.name == "Test Ship"
        assert ship.base_range_ly == 5.0
        assert ship.base_fuel_need == 1000
        assert ship.fuel_type == FuelType.HELIUM

    def test_default_flags(self):
        """Optional flags should default to False."""
        ship = CapitalShipData(
            type_id=12345,
            name="Test Ship",
            base_range_ly=5.0,
            base_fuel_need=1000,
            fuel_type=FuelType.HELIUM,
        )

        assert ship.is_jump_freighter is False
        assert ship.is_black_ops is False

    def test_jump_freighter_flag(self):
        """Should set jump freighter flag."""
        ship = CapitalShipData(
            type_id=12345,
            name="Test JF",
            base_range_ly=5.0,
            base_fuel_need=3000,
            fuel_type=FuelType.HELIUM,
            is_jump_freighter=True,
        )

        assert ship.is_jump_freighter is True

    def test_black_ops_flag(self):
        """Should set black ops flag."""
        ship = CapitalShipData(
            type_id=12345,
            name="Test Blops",
            base_range_ly=3.5,
            base_fuel_need=400,
            fuel_type=FuelType.OXYGEN,
            is_black_ops=True,
        )

        assert ship.is_black_ops is True


class TestCapitalShipsData:
    """Tests for CAPITAL_SHIPS dictionary."""

    def test_has_dreadnoughts(self):
        """Should have all four dreadnoughts."""
        dreads = ["Revelation", "Moros", "Naglfar", "Phoenix"]
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        for dread in dreads:
            assert dread in ship_names

    def test_has_carriers(self):
        """Should have all four carriers."""
        carriers = ["Archon", "Thanatos", "Nidhoggur", "Chimera"]
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        for carrier in carriers:
            assert carrier in ship_names

    def test_has_force_auxiliaries(self):
        """Should have all four FAXes."""
        faxes = ["Apostle", "Ninazu", "Lif", "Minokawa"]
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        for fax in faxes:
            assert fax in ship_names

    def test_has_supercarriers(self):
        """Should have all four supercarriers."""
        supers = ["Aeon", "Nyx", "Hel", "Wyvern"]
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        for super_ in supers:
            assert super_ in ship_names

    def test_has_titans(self):
        """Should have all four titans."""
        titans = ["Avatar", "Erebus", "Ragnarok", "Leviathan"]
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        for titan in titans:
            assert titan in ship_names

    def test_has_jump_freighters(self):
        """Should have all four jump freighters."""
        jfs = ["Ark", "Anshar", "Nomad", "Rhea"]
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        for jf in jfs:
            assert jf in ship_names

    def test_has_black_ops(self):
        """Should have all four black ops."""
        blops = ["Sin", "Widow", "Panther", "Redeemer"]
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        for blop in blops:
            assert blop in ship_names

    def test_has_rorqual(self):
        """Should have Rorqual."""
        ship_names = [s.name for s in CAPITAL_SHIPS.values()]
        assert "Rorqual" in ship_names

    def test_capitals_have_5ly_base_range(self):
        """Standard capitals should have 5 LY base range."""
        non_blops = [s for s in CAPITAL_SHIPS.values() if not s.is_black_ops]
        for ship in non_blops:
            assert ship.base_range_ly == 5.0

    def test_blops_have_3_5ly_base_range(self):
        """Black ops should have 3.5 LY base range."""
        blops = [s for s in CAPITAL_SHIPS.values() if s.is_black_ops]
        for ship in blops:
            assert ship.base_range_ly == 3.5

    def test_unique_type_ids(self):
        """All type IDs should be unique."""
        type_ids = list(CAPITAL_SHIPS.keys())
        assert len(type_ids) == len(set(type_ids))

    def test_jump_freighters_flagged(self):
        """Jump freighters should have is_jump_freighter=True."""
        jf_names = ["Ark", "Anshar", "Nomad", "Rhea"]
        for ship in CAPITAL_SHIPS.values():
            if ship.name in jf_names:
                assert ship.is_jump_freighter is True
            else:
                assert ship.is_jump_freighter is False

    def test_black_ops_flagged(self):
        """Black ops should have is_black_ops=True."""
        blops_names = ["Sin", "Widow", "Panther", "Redeemer"]
        for ship in CAPITAL_SHIPS.values():
            if ship.name in blops_names:
                assert ship.is_black_ops is True
            else:
                assert ship.is_black_ops is False


class TestGetShipBaseRange:
    """Tests for get_ship_base_range function."""

    def test_known_ship(self):
        """Should return base range for known ship."""
        # Archon carrier
        range_ly = get_ship_base_range(23757)
        assert range_ly == 5.0

    def test_unknown_ship(self):
        """Should return None for unknown ship."""
        range_ly = get_ship_base_range(99999999)
        assert range_ly is None

    def test_blops_range(self):
        """Should return 3.5 LY for black ops."""
        # Sin
        range_ly = get_ship_base_range(22428)
        assert range_ly == 3.5


class TestGetShipFuelNeed:
    """Tests for get_ship_fuel_need function."""

    def test_known_ship(self):
        """Should return fuel need for known ship."""
        # Archon carrier
        fuel = get_ship_fuel_need(23757)
        assert fuel == 1000

    def test_unknown_ship(self):
        """Should return None for unknown ship."""
        fuel = get_ship_fuel_need(99999999)
        assert fuel is None

    def test_titan_fuel(self):
        """Titans should have high fuel need."""
        # Avatar
        fuel = get_ship_fuel_need(671)
        assert fuel == 10000

    def test_blops_fuel(self):
        """Black ops should have low fuel need."""
        # Sin
        fuel = get_ship_fuel_need(22428)
        assert fuel == 400


class TestCalculateEffectiveRange:
    """Tests for calculate_effective_range function."""

    def test_no_skill(self):
        """With no JDC skill, range should equal base."""
        effective = calculate_effective_range(5.0, jdc_level=0)
        assert effective == 5.0

    def test_jdc_1(self):
        """JDC 1 should give 25% bonus."""
        effective = calculate_effective_range(5.0, jdc_level=1)
        assert effective == 6.25

    def test_jdc_5(self):
        """JDC 5 should give 125% bonus."""
        effective = calculate_effective_range(5.0, jdc_level=5)
        assert effective == 11.25

    def test_different_base_range(self):
        """Should work with different base ranges."""
        effective = calculate_effective_range(3.5, jdc_level=5)
        assert effective == 7.875  # 3.5 * 2.25


class TestCalculateFuelConsumption:
    """Tests for calculate_fuel_consumption function."""

    def test_no_skills(self):
        """With no skills, fuel should be base * distance."""
        fuel = calculate_fuel_consumption(
            base_fuel=1000,
            distance_ly=5.0,
            jfc_level=0,
            jf_level=0,
        )
        assert fuel == 5000

    def test_jfc_reduces_fuel(self):
        """JFC should reduce fuel consumption."""
        fuel_no_skill = calculate_fuel_consumption(1000, 5.0, jfc_level=0)
        fuel_jfc_5 = calculate_fuel_consumption(1000, 5.0, jfc_level=5)

        assert fuel_jfc_5 < fuel_no_skill
        assert fuel_jfc_5 == 2500  # 50% reduction

    def test_jf_skill_for_jump_freighters(self):
        """JF skill should reduce fuel for jump freighters only."""
        fuel_regular = calculate_fuel_consumption(
            3000, 5.0, jfc_level=0, jf_level=5, is_jump_freighter=False
        )
        fuel_jf = calculate_fuel_consumption(
            3000, 5.0, jfc_level=0, jf_level=5, is_jump_freighter=True
        )

        assert fuel_jf < fuel_regular

    def test_rounds_up(self):
        """Should round up to nearest whole isotope."""
        fuel = calculate_fuel_consumption(1000, 1.1, jfc_level=0)
        # 1000 * 1.1 = 1100, should round up
        assert fuel == 1100

    def test_combined_skills(self):
        """JFC and JF skills should stack."""
        fuel = calculate_fuel_consumption(
            3000, 5.0, jfc_level=5, jf_level=5, is_jump_freighter=True
        )
        # 3000 * 5.0 * 0.5 (JFC5) * 0.5 (JF5) = 3750
        assert fuel == 3750

    def test_fractional_distance(self):
        """Should handle fractional distances."""
        fuel = calculate_fuel_consumption(1000, 2.5, jfc_level=0)
        assert fuel == 2500

    def test_very_small_distance(self):
        """Should handle very small distances."""
        fuel = calculate_fuel_consumption(1000, 0.01, jfc_level=0)
        assert fuel >= 1  # Should round up to at least 1
