"""Unit tests for fitting service - additional coverage."""

from backend.app.services.fitting import (
    JumpCapability,
    ShipCategory,
    get_ship_info,
    get_travel_recommendation,
    list_jump_capable_ships,
    list_ships_by_category,
    parse_eft_fitting,
)

# Additional EFT fittings for edge cases
FREIGHTER_FITTING = """[Charon, Hauling]
Reinforced Bulkheads II
Reinforced Bulkheads II
Reinforced Bulkheads II

[Empty Med slot]
[Empty Med slot]
[Empty Med slot]

[Empty High slot]

Large Cargohold Optimization II
Large Cargohold Optimization II
Large Cargohold Optimization II"""

JUMP_FREIGHTER_FITTING = """[Rhea, JF Travel]
Inertial Stabilizers II
Inertial Stabilizers II
Inertial Stabilizers II

[Empty Med slot]

[Empty High slot]

Large Hyperspatial Velocity Optimizer II"""

INDUSTRIAL_NO_CLOAK = """[Tayra, Basic Hauler]
Expanded Cargohold II
Expanded Cargohold II

10MN Afterburner II

[Empty High slot]"""

INDUSTRIAL_WITH_CLOAK = """[Viator, Blockade Runner]
Nanofiber Internal Structure II
Inertial Stabilizers II

50MN Microwarpdrive II
Covert Ops Cloaking Device II

[Empty High slot]"""

BUBBLE_IMMUNE_FITTING = """[Tengu, Nullsec Travel]
Damage Control II
Nanofiber Internal Structure II

50MN Microwarpdrive II
Interdiction Nullifier II

[Empty High slot]"""

WARP_STAB_FITTING = """[Iteron Mark V, Safe Hauler]
Warp Core Stabilizer II
Warp Core Stabilizer II
Expanded Cargohold II

10MN Afterburner II
Medium Shield Extender II

[Empty High slot]"""

TITAN_FITTING = """[Avatar, Bridging]
Capital Armor Repairer II
Damage Control II

Capital Cap Battery II

Doomsday Device I"""

SUPERCARRIER_FITTING = """[Nyx, Ratting]
Damage Control II
Capital Armor Repairer I

Capital Cap Battery II

Fighter Support Unit I"""

FITTING_WITH_CHARGES = """[Drake, PvE]
Ballistic Control System II
Damage Control II

Large Shield Extender II
Adaptive Invulnerability Field II

Heavy Missile Launcher II, Scourge Fury Heavy Missile
Heavy Missile Launcher II, Scourge Fury Heavy Missile"""

FITTING_WITH_CARGO_DRONES = """[Vexor, Ratting]
Damage Control II
Drone Damage Amplifier II

50MN Microwarpdrive II
Large Shield Extender II

Drone Link Augmentor I

[Cargo]
Mobile Depot x1

[Drones]
Hammerhead II x5
Hobgoblin II x5"""

FITTING_EMPTY_SLOTS = """[Merlin, Basic]
[Empty Low slot]
[Empty Low slot]

[Empty Med slot]
[Empty Med slot]

[Empty High slot]
[Empty High slot]

[Empty Rig slot]
[Empty Rig slot]"""


class TestParseFittingEdgeCases:
    """Additional tests for fitting parsing edge cases."""

    def test_parse_fitting_with_charges(self):
        """Test parsing fitting with module charges."""
        fitting = parse_eft_fitting(FITTING_WITH_CHARGES)

        assert fitting is not None
        assert fitting.ship_name == "Drake"
        # Modules should be extracted without charges
        assert any("Heavy Missile Launcher II" in m for m in fitting.modules)
        # Charges should be captured
        assert len(fitting.charges) == 2
        assert "Scourge Fury Heavy Missile" in fitting.charges

    def test_parse_fitting_with_cargo_drones(self):
        """Test parsing fitting with cargo and drones sections."""
        fitting = parse_eft_fitting(FITTING_WITH_CARGO_DRONES)

        assert fitting is not None
        assert fitting.ship_name == "Vexor"
        assert len(fitting.cargo) > 0
        assert len(fitting.drones) > 0
        assert "Mobile Depot" in fitting.cargo[0]

    def test_parse_fitting_empty_slots(self):
        """Test parsing fitting with empty slot markers."""
        fitting = parse_eft_fitting(FITTING_EMPTY_SLOTS)

        assert fitting is not None
        assert fitting.ship_name == "Merlin"
        # Empty slots should be ignored
        assert len(fitting.modules) == 0

    def test_parse_freighter_fitting(self):
        """Test parsing freighter fitting."""
        fitting = parse_eft_fitting(FREIGHTER_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Charon"
        assert fitting.ship_category == ShipCategory.freighter
        assert fitting.jump_capability == JumpCapability.none

    def test_parse_jump_freighter_fitting(self):
        """Test parsing jump freighter fitting."""
        fitting = parse_eft_fitting(JUMP_FREIGHTER_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Rhea"
        assert fitting.ship_category == ShipCategory.freighter
        assert fitting.jump_capability == JumpCapability.jump_freighter
        assert fitting.has_align_mods is True
        assert fitting.has_warp_speed_mods is True

    def test_parse_bubble_immune_fitting(self):
        """Test parsing fitting with interdiction nullifier."""
        fitting = parse_eft_fitting(BUBBLE_IMMUNE_FITTING)

        assert fitting is not None
        assert fitting.is_bubble_immune is True
        assert fitting.has_align_mods is True

    def test_parse_warp_stab_fitting(self):
        """Test parsing fitting with warp core stabilizers."""
        fitting = parse_eft_fitting(WARP_STAB_FITTING)

        assert fitting is not None
        assert fitting.has_warp_stabs is True

    def test_parse_titan_fitting(self):
        """Test parsing titan fitting."""
        fitting = parse_eft_fitting(TITAN_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Avatar"
        assert fitting.ship_category == ShipCategory.supercapital
        assert fitting.jump_capability == JumpCapability.jump_portal

    def test_parse_supercarrier_fitting(self):
        """Test parsing supercarrier fitting."""
        fitting = parse_eft_fitting(SUPERCARRIER_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Nyx"
        assert fitting.ship_category == ShipCategory.supercapital
        assert fitting.jump_capability == JumpCapability.jump_drive

    def test_parse_fitting_preserves_raw_text(self):
        """Test that parsed fitting preserves raw text."""
        fitting = parse_eft_fitting(FREIGHTER_FITTING)

        assert fitting is not None
        assert fitting.raw_text == FREIGHTER_FITTING


class TestTravelRecommendationEdgeCases:
    """Additional tests for travel recommendation edge cases."""

    def test_freighter_recommendation(self):
        """Test recommendation for regular freighter."""
        fitting = parse_eft_fitting(FREIGHTER_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.ship_name == "Charon"
        assert rec.can_use_gates is True
        assert rec.can_jump is False
        assert rec.recommended_profile == "safer"
        assert any("escort" in w.lower() for w in rec.warnings)

    def test_jump_freighter_recommendation(self):
        """Test recommendation for jump freighter."""
        fitting = parse_eft_fitting(JUMP_FREIGHTER_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.can_use_gates is True
        assert rec.can_jump is True
        assert rec.recommended_profile == "safest"
        assert any("jump" in t.lower() for t in rec.tips)

    def test_industrial_no_cloak_recommendation(self):
        """Test recommendation for industrial without cloak."""
        fitting = parse_eft_fitting(INDUSTRIAL_NO_CLOAK)
        rec = get_travel_recommendation(fitting)

        assert rec.can_use_gates is True
        assert any("cloak" in w.lower() for w in rec.warnings)

    def test_industrial_with_cloak_recommendation(self):
        """Test recommendation for blockade runner with cloak."""
        fitting = parse_eft_fitting(INDUSTRIAL_WITH_CLOAK)
        rec = get_travel_recommendation(fitting)

        assert fitting.is_covert_capable is True
        assert rec.recommended_profile == "shortest"

    def test_bubble_immune_recommendation(self):
        """Test recommendation for bubble immune ship."""
        fitting = parse_eft_fitting(BUBBLE_IMMUNE_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.recommended_profile == "shorter"
        assert any("bubble" in t.lower() or "nullifier" in t.lower() for t in rec.tips)

    def test_warp_stab_recommendation(self):
        """Test recommendation with warp stabs."""
        fitting = parse_eft_fitting(WARP_STAB_FITTING)
        rec = get_travel_recommendation(fitting)

        assert any("stab" in t.lower() or "scram" in t.lower() for t in rec.tips)

    def test_titan_recommendation(self):
        """Test recommendation for titan."""
        fitting = parse_eft_fitting(TITAN_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.can_use_gates is False
        assert rec.can_jump is True
        assert rec.can_bridge_others is True
        assert rec.recommended_profile == "safest"

    def test_supercarrier_recommendation(self):
        """Test recommendation for supercarrier."""
        fitting = parse_eft_fitting(SUPERCARRIER_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.can_use_gates is False
        assert rec.can_jump is True
        assert rec.can_bridge_others is False  # Supers can't bridge
        assert rec.recommended_profile == "safest"

    def test_cloak_but_not_covert_recommendation(self):
        """Test recommendation for ship with regular cloak (not covert)."""
        # Create a fitting with improved cloak but not covert
        fitting_text = """[Vexor, Scout]
Damage Control II

50MN Microwarpdrive II
Improved Cloaking Device II

[Empty High slot]"""
        fitting = parse_eft_fitting(fitting_text)
        rec = get_travel_recommendation(fitting)

        assert fitting.is_cloak_capable is True
        assert fitting.is_covert_capable is False
        # Should recommend MWD+cloak trick
        assert any("mwd" in t.lower() and "cloak" in t.lower() for t in rec.tips)

    def test_small_ship_recommendation(self):
        """Test recommendation for small fast ship."""
        fitting_text = """[Rifter, Fast Tackle]
Nanofiber Internal Structure II

5MN Microwarpdrive II

[Empty High slot]"""
        fitting = parse_eft_fitting(fitting_text)
        rec = get_travel_recommendation(fitting)

        assert rec.recommended_profile == "shortest"
        assert any(
            "evade" in t.lower() or "fast" in t.lower() or "small" in t.lower() for t in rec.tips
        )


class TestListShipsEdgeCases:
    """Additional tests for ship listing functions."""

    def test_list_by_category_frigate(self):
        """Test listing frigates."""
        ships = list_ships_by_category(ShipCategory.frigate)

        assert len(ships) > 0
        assert "Rifter" in ships
        assert "Merlin" in ships
        assert "Astero" in ships

    def test_list_by_category_destroyer(self):
        """Test listing destroyers."""
        ships = list_ships_by_category(ShipCategory.destroyer)

        assert len(ships) > 0
        assert "Thrasher" in ships
        assert "Catalyst" in ships

    def test_list_by_category_battlecruiser(self):
        """Test listing battlecruisers."""
        ships = list_ships_by_category(ShipCategory.battlecruiser)

        assert len(ships) > 0
        assert "Drake" in ships
        assert "Hurricane" in ships

    def test_list_by_category_battleship(self):
        """Test listing battleships."""
        ships = list_ships_by_category(ShipCategory.battleship)

        assert len(ships) > 0
        assert "Raven" in ships
        assert "Machariel" in ships
        # Black Ops are battleships too
        assert "Sin" in ships

    def test_list_by_category_industrial(self):
        """Test listing industrials."""
        ships = list_ships_by_category(ShipCategory.industrial)

        assert len(ships) > 0
        assert "Tayra" in ships
        assert "Viator" in ships  # Blockade runners

    def test_list_by_category_freighter(self):
        """Test listing freighters."""
        ships = list_ships_by_category(ShipCategory.freighter)

        assert len(ships) > 0
        assert "Charon" in ships
        assert "Rhea" in ships  # Jump freighters

    def test_list_by_category_supercapital(self):
        """Test listing supercapitals."""
        ships = list_ships_by_category(ShipCategory.supercapital)

        assert len(ships) > 0
        # Supercarriers
        assert "Nyx" in ships
        assert "Aeon" in ships
        # Titans
        assert "Avatar" in ships
        assert "Erebus" in ships

    def test_list_by_category_unknown(self):
        """Test listing unknown category returns empty."""
        ships = list_ships_by_category(ShipCategory.unknown)

        assert isinstance(ships, list)
        # Unknown ships aren't stored in SHIP_DATA

    def test_list_jump_capable_includes_all_types(self):
        """Test jump capable list includes all jump types."""
        ships = list_jump_capable_ships()

        # Capitals
        assert "Archon" in ships
        assert "Revelation" in ships
        # Jump freighters
        assert "Rhea" in ships
        assert "Anshar" in ships
        # Black Ops
        assert "Sin" in ships
        assert "Panther" in ships
        # Titans
        assert "Avatar" in ships
        # Supercarriers
        assert "Nyx" in ships


class TestGetShipInfoEdgeCases:
    """Additional tests for get_ship_info function."""

    def test_get_black_ops_info(self):
        """Test getting Black Ops ship info."""
        info = get_ship_info("Sin")

        assert info is not None
        assert info["category"] == ShipCategory.battleship
        assert info["jump"] == JumpCapability.covert_bridge

    def test_get_titan_info(self):
        """Test getting titan info."""
        info = get_ship_info("Avatar")

        assert info is not None
        assert info["category"] == ShipCategory.supercapital
        assert info["jump"] == JumpCapability.jump_portal

    def test_get_jump_freighter_info(self):
        """Test getting jump freighter info."""
        info = get_ship_info("Rhea")

        assert info is not None
        assert info["category"] == ShipCategory.freighter
        assert info["jump"] == JumpCapability.jump_freighter

    def test_get_supercarrier_info(self):
        """Test getting supercarrier info."""
        info = get_ship_info("Nyx")

        assert info is not None
        assert info["category"] == ShipCategory.supercapital
        assert info["jump"] == JumpCapability.jump_drive

    def test_get_fax_info(self):
        """Test getting Force Auxiliary info."""
        info = get_ship_info("Apostle")

        assert info is not None
        assert info["category"] == ShipCategory.capital
        assert info["jump"] == JumpCapability.jump_drive

    def test_get_rorqual_info(self):
        """Test getting Rorqual info."""
        info = get_ship_info("Rorqual")

        assert info is not None
        assert info["category"] == ShipCategory.capital
        assert info["jump"] == JumpCapability.jump_drive
