"""Unit tests for fitting API and service."""

import pytest
from fastapi import HTTPException

from backend.app.api.v1.fitting import (
    AnalyzeFittingResponse,
    CategoryListResponse,
    ParsedFittingResponse,
    ParseFittingRequest,
    ShipInfoResponse,
    ShipListResponse,
    TravelRecommendationResponse,
    analyze_fitting,
    get_ship,
    list_categories,
    list_jump_ships,
    list_ships_in_category,
    parse_fitting,
)
from backend.app.services.fitting import (
    JumpCapability,
    ParsedFitting,
    ShipCategory,
    TravelRecommendation,
    get_ship_info,
    get_travel_recommendation,
    list_jump_capable_ships,
    list_ships_by_category,
    parse_eft_fitting,
)


# Sample EFT fitting strings
SIMPLE_FITTING = """[Caracal, Travel Fit]
Damage Control II
Nanofiber Internal Structure II

50MN Microwarpdrive II
Large Shield Extender II

Rapid Light Missile Launcher II

Medium Core Defense Field Extender I"""

CLOAK_FITTING = """[Astero, Scout]
Damage Control II
Nanofiber Internal Structure II

5MN Microwarpdrive II
Covert Ops Cloaking Device II

Core Probe Launcher II

Small Hyperspatial Velocity Optimizer II"""

CAPITAL_FITTING = """[Archon, Support]
Damage Control II
Capital Armor Repairer I

Capital Cap Battery II

Fighter Support Unit II"""

BLOPS_FITTING = """[Sin, Bridge Fit]
Damage Control II
1600mm Steel Plates II

Jump Drive Economizer II
Covert Ops Cloaking Device II

Heavy Neutron Blaster II"""


class TestParseFittingService:
    """Tests for fitting parsing service."""

    def test_parse_simple_fitting(self):
        """Test parsing a simple fitting."""
        fitting = parse_eft_fitting(SIMPLE_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Caracal"
        assert fitting.ship_category == ShipCategory.cruiser
        assert fitting.jump_capability == JumpCapability.none
        assert "Damage Control II" in fitting.modules
        assert "Nanofiber Internal Structure II" in fitting.modules
        assert fitting.has_align_mods is True

    def test_parse_cloak_fitting(self):
        """Test parsing a fitting with covert cloak."""
        fitting = parse_eft_fitting(CLOAK_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Astero"
        assert fitting.is_covert_capable is True
        assert fitting.has_warp_speed_mods is True

    def test_parse_capital_fitting(self):
        """Test parsing a capital ship fitting."""
        fitting = parse_eft_fitting(CAPITAL_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Archon"
        assert fitting.ship_category == ShipCategory.capital
        assert fitting.jump_capability == JumpCapability.jump_drive

    def test_parse_blops_fitting(self):
        """Test parsing a Black Ops fitting."""
        fitting = parse_eft_fitting(BLOPS_FITTING)

        assert fitting is not None
        assert fitting.ship_name == "Sin"
        assert fitting.jump_capability == JumpCapability.covert_bridge
        assert fitting.is_covert_capable is True

    def test_parse_invalid_fitting(self):
        """Test parsing invalid fitting."""
        result = parse_eft_fitting("not a valid fitting")
        assert result is None

    def test_parse_empty_fitting(self):
        """Test parsing empty string."""
        result = parse_eft_fitting("")
        assert result is None

    def test_parse_unknown_ship(self):
        """Test parsing unknown ship."""
        fitting = parse_eft_fitting("[UnknownShip, Test]\nSome Module")

        assert fitting is not None
        assert fitting.ship_name == "UnknownShip"
        assert fitting.ship_category == ShipCategory.unknown
        assert fitting.jump_capability == JumpCapability.none


class TestGetShipInfo:
    """Tests for get_ship_info function."""

    def test_known_ship(self):
        """Test getting info for known ship."""
        info = get_ship_info("Caracal")

        assert info is not None
        assert info["category"] == ShipCategory.cruiser
        assert info["jump"] == JumpCapability.none

    def test_capital_ship(self):
        """Test getting info for capital ship."""
        info = get_ship_info("Archon")

        assert info is not None
        assert info["category"] == ShipCategory.capital
        assert info["jump"] == JumpCapability.jump_drive

    def test_unknown_ship(self):
        """Test getting info for unknown ship."""
        info = get_ship_info("NotARealShip")
        assert info is None


class TestTravelRecommendation:
    """Tests for travel recommendation service."""

    def test_subcap_recommendation(self):
        """Test recommendation for subcapital ship."""
        fitting = parse_eft_fitting(SIMPLE_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.ship_name == "Caracal"
        assert rec.can_use_gates is True
        assert rec.can_jump is False

    def test_capital_recommendation(self):
        """Test recommendation for capital ship."""
        fitting = parse_eft_fitting(CAPITAL_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.can_use_gates is False  # Capitals can't use gates
        assert rec.can_jump is True
        assert len(rec.warnings) > 0  # Should warn about no gate usage

    def test_blops_recommendation(self):
        """Test recommendation for Black Ops."""
        fitting = parse_eft_fitting(BLOPS_FITTING)
        rec = get_travel_recommendation(fitting)

        assert rec.can_jump is True
        assert rec.can_covert_bridge is True


class TestListShips:
    """Tests for ship listing functions."""

    def test_list_jump_capable(self):
        """Test listing jump-capable ships."""
        ships = list_jump_capable_ships()

        assert len(ships) > 0
        assert "Archon" in ships
        assert "Rhea" in ships
        assert "Sin" in ships
        # Subcaps should not be in list
        assert "Caracal" not in ships

    def test_list_by_category_cruiser(self):
        """Test listing cruisers."""
        ships = list_ships_by_category(ShipCategory.cruiser)

        assert len(ships) > 0
        assert "Caracal" in ships
        assert "Stabber" in ships

    def test_list_by_category_capital(self):
        """Test listing capitals."""
        ships = list_ships_by_category(ShipCategory.capital)

        assert len(ships) > 0
        assert "Archon" in ships
        assert "Thanatos" in ships
        assert "Revelation" in ships


class TestFittingAPIEndpoints:
    """Tests for fitting API endpoints."""

    @pytest.mark.asyncio
    async def test_parse_fitting_endpoint(self):
        """Test parse fitting endpoint."""
        request = ParseFittingRequest(eft_text=SIMPLE_FITTING)
        response = await parse_fitting(request)

        assert isinstance(response, ParsedFittingResponse)
        assert response.ship_name == "Caracal"
        assert response.ship_category == "cruiser"
        assert response.jump_capability == "none"

    @pytest.mark.asyncio
    async def test_parse_fitting_invalid(self):
        """Test parse fitting endpoint with invalid input."""
        request = ParseFittingRequest(eft_text="invalid fitting")

        with pytest.raises(HTTPException) as exc_info:
            await parse_fitting(request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_analyze_fitting_endpoint(self):
        """Test analyze fitting endpoint."""
        request = ParseFittingRequest(eft_text=SIMPLE_FITTING)
        response = await analyze_fitting(request)

        assert isinstance(response, AnalyzeFittingResponse)
        assert response.fitting.ship_name == "Caracal"
        assert response.travel.can_use_gates is True

    @pytest.mark.asyncio
    async def test_get_ship_endpoint(self):
        """Test get ship info endpoint."""
        response = await get_ship("Caracal")

        assert isinstance(response, ShipInfoResponse)
        assert response.name == "Caracal"
        assert response.category == "cruiser"

    @pytest.mark.asyncio
    async def test_get_ship_not_found(self):
        """Test get ship info for unknown ship."""
        with pytest.raises(HTTPException) as exc_info:
            await get_ship("NotARealShip")

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_list_jump_ships_endpoint(self):
        """Test list jump ships endpoint."""
        response = await list_jump_ships()

        assert isinstance(response, ShipListResponse)
        assert response.total > 0
        assert "Archon" in response.ships

    @pytest.mark.asyncio
    async def test_list_ships_by_category_endpoint(self):
        """Test list ships by category endpoint."""
        response = await list_ships_in_category("cruiser")

        assert isinstance(response, ShipListResponse)
        assert response.total > 0
        assert "Caracal" in response.ships

    @pytest.mark.asyncio
    async def test_list_ships_invalid_category(self):
        """Test list ships with invalid category."""
        with pytest.raises(HTTPException) as exc_info:
            await list_ships_in_category("invalid_category")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_list_categories_endpoint(self):
        """Test list categories endpoint."""
        response = await list_categories()

        assert isinstance(response, CategoryListResponse)
        assert "cruiser" in response.categories
        assert "capital" in response.categories
        assert "frigate" in response.categories


class TestParsedFittingResponse:
    """Tests for ParsedFittingResponse model."""

    def test_from_fitting(self):
        """Test creating response from parsed fitting."""
        fitting = ParsedFitting(
            ship_name="Caracal",
            ship_category=ShipCategory.cruiser,
            jump_capability=JumpCapability.none,
            modules=["Damage Control II"],
            is_covert_capable=False,
            is_cloak_capable=True,
            has_warp_stabs=False,
            is_bubble_immune=False,
            has_align_mods=True,
            has_warp_speed_mods=False,
        )

        response = ParsedFittingResponse.from_fitting(fitting)

        assert response.ship_name == "Caracal"
        assert response.ship_category == "cruiser"
        assert response.jump_capability == "none"
        assert response.is_cloak_capable is True
        assert response.has_align_mods is True


class TestTravelRecommendationResponse:
    """Tests for TravelRecommendationResponse model."""

    def test_from_recommendation(self):
        """Test creating response from travel recommendation."""
        rec = TravelRecommendation(
            ship_name="Sin",
            category=ShipCategory.battleship,
            can_use_gates=True,
            can_jump=True,
            can_covert_bridge=True,
            recommended_profile="safer",
            warnings=["Valuable target"],
            tips=["Use covert ops bridge"],
        )

        response = TravelRecommendationResponse.from_recommendation(rec)

        assert response.ship_name == "Sin"
        assert response.category == "battleship"
        assert response.can_jump is True
        assert response.can_covert_bridge is True
        assert "Valuable target" in response.warnings
        assert "Use covert ops bridge" in response.tips
