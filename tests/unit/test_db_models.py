"""Unit tests for SQLAlchemy database models."""

from datetime import UTC, datetime

from backend.app.db.models import (
    CacheEntry,
    KillRecord,
    Region,
    SolarSystem,
    Stargate,
)


class TestRegionModel:
    """Tests for Region model."""

    def test_region_creation(self):
        """Test creating a Region instance."""
        region = Region(id=10000002, name="The Forge", faction_id=500001)

        assert region.id == 10000002
        assert region.name == "The Forge"
        assert region.faction_id == 500001

    def test_region_repr(self):
        """Test Region string representation."""
        region = Region(id=10000002, name="The Forge")

        result = repr(region)
        assert "Region" in result
        assert "10000002" in result
        assert "The Forge" in result

    def test_region_without_faction(self):
        """Test Region without faction_id."""
        region = Region(id=10000002, name="The Forge")

        assert region.faction_id is None


class TestSolarSystemModel:
    """Tests for SolarSystem model."""

    def test_solar_system_creation(self):
        """Test creating a SolarSystem instance."""
        system = SolarSystem(
            id=30000142,
            name="Jita",
            region_id=10000002,
            constellation_id=20000020,
            security_status=0.945913,
            security_class="highsec",
            position_x=1.0,
            position_y=2.0,
            position_z=3.0,
        )

        assert system.id == 30000142
        assert system.name == "Jita"
        assert system.region_id == 10000002
        assert system.security_status == 0.945913
        assert system.security_class == "highsec"

    def test_solar_system_repr(self):
        """Test SolarSystem string representation."""
        system = SolarSystem(
            id=30000142,
            name="Jita",
            region_id=10000002,
            security_status=0.95,
            security_class="highsec",
            position_x=0.0,
            position_y=0.0,
        )

        result = repr(system)
        assert "SolarSystem" in result
        assert "30000142" in result
        assert "Jita" in result
        assert "0.95" in result

    def test_solar_system_without_optional_fields(self):
        """Test SolarSystem without optional fields."""
        system = SolarSystem(
            id=30000142,
            name="Jita",
            region_id=10000002,
            security_status=0.95,
            security_class="highsec",
            position_x=0.0,
            position_y=0.0,
        )

        assert system.constellation_id is None
        assert system.position_z is None


class TestStargateModel:
    """Tests for Stargate model."""

    def test_stargate_creation(self):
        """Test creating a Stargate instance."""
        gate = Stargate(
            id=1,
            source_system_id=30000142,
            destination_system_id=30000144,
        )

        assert gate.id == 1
        assert gate.source_system_id == 30000142
        assert gate.destination_system_id == 30000144

    def test_stargate_repr(self):
        """Test Stargate string representation."""
        gate = Stargate(
            id=1,
            source_system_id=30000142,
            destination_system_id=30000144,
        )

        result = repr(gate)
        assert "Stargate" in result
        assert "30000142" in result
        assert "30000144" in result


class TestKillRecordModel:
    """Tests for KillRecord model."""

    def test_kill_record_creation(self):
        """Test creating a KillRecord instance."""
        kill = KillRecord(
            id=123456789,
            system_id=30000142,
            kill_time=datetime.now(UTC),
            ship_type_id=17736,
            victim_corporation_id=98000001,
            victim_alliance_id=99000001,
            attacker_count=5,
            is_pod=False,
            total_value=500000000.0,
        )

        assert kill.id == 123456789
        assert kill.system_id == 30000142
        assert kill.ship_type_id == 17736
        assert kill.attacker_count == 5
        assert kill.is_pod is False
        assert kill.total_value == 500000000.0

    def test_kill_record_repr(self):
        """Test KillRecord string representation."""
        kill = KillRecord(
            id=123456789,
            system_id=30000142,
            kill_time=datetime.now(UTC),
        )

        result = repr(kill)
        assert "KillRecord" in result
        assert "123456789" in result
        assert "30000142" in result

    def test_kill_record_optional_fields(self):
        """Test KillRecord optional fields can be None."""
        kill = KillRecord(
            id=123456789,
            system_id=30000142,
            kill_time=datetime.now(UTC),
        )

        # Optional fields are None when not provided (defaults apply on DB insert)
        assert kill.ship_type_id is None
        assert kill.total_value is None
        assert kill.victim_corporation_id is None
        assert kill.victim_alliance_id is None

    def test_kill_record_pod(self):
        """Test KillRecord for pod kill."""
        kill = KillRecord(
            id=123456790,
            system_id=30000142,
            kill_time=datetime.now(UTC),
            ship_type_id=670,  # Capsule
            is_pod=True,
        )

        assert kill.is_pod is True
        assert kill.ship_type_id == 670


class TestCacheEntryModel:
    """Tests for CacheEntry model."""

    def test_cache_entry_creation(self):
        """Test creating a CacheEntry instance."""
        expires = datetime.now(UTC)
        entry = CacheEntry(
            key="route:Jita:Amarr:shortest",
            value='{"path": ["Jita", "Perimeter", "Amarr"]}',
            expires_at=expires,
        )

        assert entry.key == "route:Jita:Amarr:shortest"
        assert "path" in entry.value
        assert entry.expires_at == expires

    def test_cache_entry_repr(self):
        """Test CacheEntry string representation."""
        entry = CacheEntry(
            key="route:Jita:Amarr",
            value="{}",
            expires_at=datetime.now(UTC),
        )

        result = repr(entry)
        assert "CacheEntry" in result
        assert "route:Jita:Amarr" in result
