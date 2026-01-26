"""Tests for starmap SDE models."""

from datetime import datetime

from backend.starmap.sde.models import (
    Constellation,
    CynoChain,
    CynoChainMidpoint,
    HeatmapData,
    Incursion,
    JumpRangeSphere,
    PilotProfile,
    Region,
    RouteResult,
    SavedRoute,
    ShipConfig,
    SolarSystem,
    Sovereignty,
    SovereigntyCampaign,
    Stargate,
    SystemConnection,
    SystemSearchResult,
    SystemStats,
)


class TestRegion:
    """Tests for Region model."""

    def test_create_region(self):
        """Should create region with required fields."""
        region = Region(region_id=10000001, name="Derelik")

        assert region.region_id == 10000001
        assert region.name == "Derelik"
        assert region.description is None
        assert region.x == 0.0
        assert region.faction_id is None

    def test_create_region_with_all_fields(self):
        """Should create region with all fields."""
        region = Region(
            region_id=10000001,
            name="Derelik",
            description="A region in the Amarr Empire",
            x=1.0,
            y=2.0,
            z=3.0,
            faction_id=500003,
        )

        assert region.description == "A region in the Amarr Empire"
        assert region.x == 1.0
        assert region.faction_id == 500003


class TestConstellation:
    """Tests for Constellation model."""

    def test_create_constellation(self):
        """Should create constellation with required fields."""
        const = Constellation(
            constellation_id=20000001,
            region_id=10000001,
            name="San Matar",
        )

        assert const.constellation_id == 20000001
        assert const.region_id == 10000001
        assert const.name == "San Matar"


class TestSolarSystem:
    """Tests for SolarSystem model."""

    def test_create_solar_system(self):
        """Should create solar system with required fields."""
        system = SolarSystem(
            system_id=30000142,
            constellation_id=20000020,
            region_id=10000002,
            name="Jita",
            x=0.0,
            y=0.0,
            z=0.0,
            security_status=0.9459,
        )

        assert system.system_id == 30000142
        assert system.name == "Jita"
        assert system.security_status == 0.9459

    def test_display_security(self):
        """Should format security status for display."""
        system = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Test",
            x=0,
            y=0,
            z=0,
            security_status=0.9459,
        )

        assert system.display_security == "0.9"

    def test_sec_class_highsec(self):
        """Should compute highsec class."""
        system = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Test",
            x=0,
            y=0,
            z=0,
            security_status=0.5,
        )

        assert system.sec_class == "highsec"

    def test_sec_class_lowsec(self):
        """Should compute lowsec class."""
        system = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Test",
            x=0,
            y=0,
            z=0,
            security_status=0.4,
        )

        assert system.sec_class == "lowsec"

    def test_sec_class_nullsec(self):
        """Should compute nullsec class."""
        system = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Test",
            x=0,
            y=0,
            z=0,
            security_status=0.0,
        )

        assert system.sec_class == "nullsec"

    def test_sec_class_wormhole(self):
        """Should return wormhole class for wormhole systems."""
        system = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="J123456",
            x=0,
            y=0,
            z=0,
            security_status=-1.0,
            is_wormhole=True,
        )

        assert system.sec_class == "wormhole"

    def test_sec_class_uses_explicit_value(self):
        """Should use explicit security_class if set."""
        system = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Test",
            x=0,
            y=0,
            z=0,
            security_status=0.9,
            security_class="pochven",
        )

        assert system.sec_class == "pochven"


class TestStargate:
    """Tests for Stargate model."""

    def test_create_stargate(self):
        """Should create stargate with required fields."""
        gate = Stargate(
            stargate_id=50001234,
            system_id=30000142,
            destination_stargate_id=50001235,
            destination_system_id=30000143,
        )

        assert gate.stargate_id == 50001234
        assert gate.system_id == 30000142
        assert gate.destination_system_id == 30000143


class TestSystemConnection:
    """Tests for SystemConnection model."""

    def test_create_connection(self):
        """Should create connection with defaults."""
        conn = SystemConnection(from_system_id=1, to_system_id=2)

        assert conn.from_system_id == 1
        assert conn.to_system_id == 2
        assert conn.base_weight == 1.0
        assert conn.security_weight == 0.0
        assert conn.connection_type == "stargate"

    def test_total_weight(self):
        """Should compute total weight."""
        conn = SystemConnection(
            from_system_id=1,
            to_system_id=2,
            base_weight=1.0,
            security_weight=5.0,
        )

        assert conn.total_weight == 6.0


class TestSystemStats:
    """Tests for SystemStats model."""

    def test_create_stats(self):
        """Should create stats with defaults."""
        stats = SystemStats(system_id=30000142)

        assert stats.system_id == 30000142
        assert stats.ship_kills == 0
        assert stats.npc_kills == 0
        assert stats.pod_kills == 0
        assert stats.ship_jumps == 0

    def test_total_kills(self):
        """Should compute total PvP kills."""
        stats = SystemStats(system_id=1, ship_kills=10, pod_kills=5)

        assert stats.total_kills == 15

    def test_danger_level_safe(self):
        """Should return safe for no kills."""
        stats = SystemStats(system_id=1, ship_kills=0)
        assert stats.danger_level == "safe"

    def test_danger_level_low(self):
        """Should return low for 1-4 kills."""
        stats = SystemStats(system_id=1, ship_kills=3)
        assert stats.danger_level == "low"

    def test_danger_level_moderate(self):
        """Should return moderate for 5-19 kills."""
        stats = SystemStats(system_id=1, ship_kills=10)
        assert stats.danger_level == "moderate"

    def test_danger_level_high(self):
        """Should return high for 20-49 kills."""
        stats = SystemStats(system_id=1, ship_kills=30)
        assert stats.danger_level == "high"

    def test_danger_level_extreme(self):
        """Should return extreme for 50+ kills."""
        stats = SystemStats(system_id=1, ship_kills=100)
        assert stats.danger_level == "extreme"


class TestIncursion:
    """Tests for Incursion model."""

    def test_create_incursion(self):
        """Should create incursion with required fields."""
        incursion = Incursion(
            constellation_id=20000001,
            state="established",
        )

        assert incursion.constellation_id == 20000001
        assert incursion.state == "established"
        assert incursion.influence == 0.0


class TestSovereignty:
    """Tests for Sovereignty model."""

    def test_create_sovereignty(self):
        """Should create sovereignty with required fields."""
        sov = Sovereignty(system_id=30000001)

        assert sov.system_id == 30000001
        assert sov.alliance_id is None


class TestSovereigntyCampaign:
    """Tests for SovereigntyCampaign model."""

    def test_create_campaign(self):
        """Should create campaign with required fields."""
        campaign = SovereigntyCampaign(
            campaign_id=1,
            system_id=30000001,
            constellation_id=20000001,
            event_type="tcu_defense",
        )

        assert campaign.campaign_id == 1
        assert campaign.event_type == "tcu_defense"


class TestShipConfig:
    """Tests for ShipConfig model."""

    def test_create_ship_config(self):
        """Should create ship config with defaults."""
        config = ShipConfig(name="My Archon", ship_type_id=23757)

        assert config.name == "My Archon"
        assert config.ship_type_id == 23757
        assert config.fuel_conservation_level == 0
        assert config.jump_drive_calibration_level == 0

    def test_computed_range_no_skills(self):
        """Should compute range without skills."""
        config = ShipConfig(
            name="Test",
            ship_type_id=1,
            jump_drive_range=5.0,
            jump_drive_calibration_level=0,
        )

        assert config.computed_range == 5.0

    def test_computed_range_with_jdc5(self):
        """Should compute range with JDC 5."""
        config = ShipConfig(
            name="Test",
            ship_type_id=1,
            jump_drive_range=5.0,
            jump_drive_calibration_level=5,
        )

        # 5.0 * (1 + 5*0.25) = 5.0 * 2.25 = 11.25
        assert config.computed_range == 11.25

    def test_computed_range_none(self):
        """Should return 0 when no base range."""
        config = ShipConfig(name="Test", ship_type_id=1)

        assert config.computed_range == 0.0

    def test_fuel_per_ly_no_skills(self):
        """Should compute fuel without skills."""
        config = ShipConfig(
            name="Test",
            ship_type_id=1,
            jump_drive_fuel_need=1000.0,
            fuel_conservation_level=0,
            jump_freighter_level=0,
        )

        assert config.fuel_per_ly == 1000.0

    def test_fuel_per_ly_with_jfc5(self):
        """Should compute fuel with JFC 5."""
        config = ShipConfig(
            name="Test",
            ship_type_id=1,
            jump_drive_fuel_need=1000.0,
            fuel_conservation_level=5,
        )

        # 1000 * (1 - 5*0.10) * 1.0 = 1000 * 0.5 = 500
        assert config.fuel_per_ly == 500.0

    def test_fuel_per_ly_with_jf5(self):
        """Should compute fuel with JF 5."""
        config = ShipConfig(
            name="Test",
            ship_type_id=1,
            jump_drive_fuel_need=1000.0,
            jump_freighter_level=5,
        )

        # 1000 * 1.0 * (1 - 5*0.10) = 1000 * 0.5 = 500
        assert config.fuel_per_ly == 500.0

    def test_fuel_per_ly_combined_skills(self):
        """Should compute fuel with both skills."""
        config = ShipConfig(
            name="Test",
            ship_type_id=1,
            jump_drive_fuel_need=1000.0,
            fuel_conservation_level=5,
            jump_freighter_level=5,
        )

        # 1000 * 0.5 * 0.5 = 250
        assert config.fuel_per_ly == 250.0

    def test_fuel_per_ly_none(self):
        """Should return 0 when no base fuel need."""
        config = ShipConfig(name="Test", ship_type_id=1)

        assert config.fuel_per_ly == 0.0


class TestPilotProfile:
    """Tests for PilotProfile model."""

    def test_create_pilot_profile(self):
        """Should create pilot profile with defaults."""
        profile = PilotProfile()

        assert profile.jump_drive_calibration == 0
        assert profile.jump_fuel_conservation == 0
        assert profile.avoid_faction_ids == []

    def test_pilot_profile_with_avoid_lists(self):
        """Should create profile with avoid lists."""
        profile = PilotProfile(
            character_name="Test Pilot",
            avoid_faction_ids=[500001, 500002],
            avoid_corporation_ids=[98000001],
        )

        assert profile.avoid_faction_ids == [500001, 500002]
        assert profile.avoid_corporation_ids == [98000001]


class TestSavedRoute:
    """Tests for SavedRoute model."""

    def test_create_saved_route(self):
        """Should create saved route with required fields."""
        route = SavedRoute(
            origin_system_id=30000142,
            destination_system_id=30002187,
        )

        assert route.origin_system_id == 30000142
        assert route.destination_system_id == 30002187
        assert route.route_type == "shortest"
        assert route.avoid_systems == []
        assert route.waypoints == []


class TestCynoChainModels:
    """Tests for cyno chain models."""

    def test_create_midpoint(self):
        """Should create cyno midpoint."""
        mid = CynoChainMidpoint(system_id=30000001, is_cyno_beacon=True)

        assert mid.system_id == 30000001
        assert mid.is_cyno_beacon is True

    def test_create_cyno_chain(self):
        """Should create cyno chain."""
        chain = CynoChain(
            origin_system_id=30000001,
            destination_system_id=30000002,
            midpoints=[
                CynoChainMidpoint(system_id=30000003),
            ],
        )

        assert chain.origin_system_id == 30000001
        assert len(chain.midpoints) == 1


class TestApiResponseModels:
    """Tests for API response models."""

    def test_system_search_result(self):
        """Should create search result."""
        result = SystemSearchResult(
            system_id=30000142,
            name="Jita",
            region_name="The Forge",
            security_status=0.9459,
            security_class="highsec",
        )

        assert result.system_id == 30000142
        assert result.name == "Jita"

    def test_route_result(self):
        """Should create route result."""
        origin = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=0,
            y=0,
            z=0,
        )
        dest = SolarSystem(
            system_id=2,
            constellation_id=1,
            region_id=1,
            name="Dest",
            x=0,
            y=0,
            z=0,
        )

        result = RouteResult(
            origin=origin,
            destination=dest,
            waypoints=[origin, dest],
            total_jumps=1,
            route_type="shortest",
            security_summary={"highsec": 2},
        )

        assert result.total_jumps == 1

    def test_jump_range_sphere(self):
        """Should create jump range sphere."""
        origin = SolarSystem(
            system_id=1,
            constellation_id=1,
            region_id=1,
            name="Origin",
            x=0,
            y=0,
            z=0,
        )

        sphere = JumpRangeSphere(
            origin_system=origin,
            max_range_ly=5.0,
            systems_in_range=[],
        )

        assert sphere.max_range_ly == 5.0

    def test_heatmap_data(self):
        """Should create heatmap data."""
        heatmap = HeatmapData(
            data_type="kills",
            min_value=0.0,
            max_value=100.0,
            systems=[(1, 0.5), (2, 0.8)],
            updated_at=datetime.now(),
        )

        assert heatmap.data_type == "kills"
        assert len(heatmap.systems) == 2
