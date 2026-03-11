"""Tests for user-submitted jump bridge connection service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.models.jumpbridge_connection import (
    JumpBridgeConnection,
    JumpBridgeConnectionCreate,
    JumpBridgeConnectionUpdate,
    JumpBridgeListResponse,
    JumpBridgeStatus,
)
from backend.app.services.jumpbridge_connections import (
    _SEP_PATTERNS,
    JumpBridgeConnectionService,
)


def make_system(name, security, category, region_id, region_name):
    """Create a mock system."""
    sys = MagicMock()
    sys.name = name
    sys.id = hash(name) & 0x7FFFFFFF  # deterministic positive int
    sys.security = security
    sys.category = category
    sys.region_id = region_id
    sys.region_name = region_name
    return sys


@pytest.fixture
def mock_universe():
    """Create a mock universe with known systems."""
    mock = MagicMock()
    mock.systems = {
        # Highsec systems
        "Jita": make_system("Jita", 0.9, "highsec", 10000002, "The Forge"),
        "Amarr": make_system("Amarr", 1.0, "highsec", 10000043, "Domain"),
        # Nullsec systems
        "HED-GP": make_system("HED-GP", -0.4, "nullsec", 10000014, "Catch"),
        "1DQ1-A": make_system("1DQ1-A", -0.5, "nullsec", 10000060, "Delve"),
        "8QT-H4": make_system("8QT-H4", -0.3, "nullsec", 10000060, "Delve"),
        "49-U6U": make_system("49-U6U", -0.2, "nullsec", 10000060, "Delve"),
        "PUIG-F": make_system("PUIG-F", -0.1, "nullsec", 10000060, "Delve"),
        # Lowsec systems
        "Amamake": make_system("Amamake", 0.4, "lowsec", 10000042, "Metropolis"),
        "Tama": make_system("Tama", 0.3, "lowsec", 10000016, "Lonetrek"),
        # Wormhole system
        "J123456": make_system("J123456", -1.0, "wh", 11000001, "A-R00001"),
    }
    return mock


@pytest.fixture
def service(mock_universe):
    """Create a JumpBridgeConnectionService with mocked DB + universe."""
    with patch(
        "backend.app.services.jumpbridge_connections.load_universe",
        return_value=mock_universe,
    ):
        svc = JumpBridgeConnectionService()
        yield svc


@pytest.fixture
def mock_db_session():
    """Create a mock async DB session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# ==================== Model Tests ====================


class TestModels:
    """Test Pydantic model validation."""

    def test_jumpbridge_connection_defaults(self):
        """JumpBridgeConnection should have sensible defaults."""
        conn = JumpBridgeConnection(
            id="jb-test123",
            from_system="1DQ1-A",
            from_system_id=30004759,
            to_system="8QT-H4",
            to_system_id=30004760,
        )
        assert conn.status == JumpBridgeStatus.UNKNOWN
        assert conn.owner_alliance is None
        assert conn.notes == ""

    def test_jumpbridge_status_enum(self):
        """Status enum should have online/offline/unknown values."""
        assert JumpBridgeStatus.ONLINE == "online"
        assert JumpBridgeStatus.OFFLINE == "offline"
        assert JumpBridgeStatus.UNKNOWN == "unknown"

    def test_jumpbridge_list_response(self):
        """JumpBridgeListResponse should serialize correctly."""
        resp = JumpBridgeListResponse(bridges=[], total=0)
        assert resp.total == 0
        assert resp.bridges == []

    def test_create_request_minimal(self):
        """Create request with minimal fields."""
        create = JumpBridgeConnectionCreate(
            from_system="1DQ1-A",
            to_system="8QT-H4",
        )
        assert create.owner_alliance is None
        assert create.notes == ""

    def test_update_request_partial(self):
        """Update request allows partial updates."""
        update = JumpBridgeConnectionUpdate(status=JumpBridgeStatus.ONLINE)
        assert update.status == JumpBridgeStatus.ONLINE
        assert update.notes is None


# ==================== Service Tests ====================


class TestJumpBridgeConnectionService:
    """Tests for JumpBridgeConnectionService."""

    @pytest.mark.asyncio
    async def test_add_connection_nullsec(self, service, mock_db_session):
        """Should add a bridge between two nullsec systems."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn = await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="1DQ1-A",
                    to_system="8QT-H4",
                ),
                created_by="TestPilot",
            )

        assert conn.from_system == "1DQ1-A"
        assert conn.to_system == "8QT-H4"
        assert conn.id.startswith("jb-")
        assert conn.created_by == "TestPilot"
        assert conn.status == JumpBridgeStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_add_connection_lowsec(self, service, mock_db_session):
        """Should allow bridges in lowsec systems."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn = await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="Amamake",
                    to_system="Tama",
                ),
            )

        assert conn.from_system == "Amamake"
        assert conn.to_system == "Tama"

    @pytest.mark.asyncio
    async def test_reject_highsec_system(self, service, mock_db_session):
        """Should reject bridges in highsec."""
        with (
            patch.object(service, "_get_session", return_value=mock_db_session),
            pytest.raises(ValueError, match="highsec"),
        ):
            await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="Jita",
                    to_system="1DQ1-A",
                ),
            )

    @pytest.mark.asyncio
    async def test_reject_wormhole_system(self, service, mock_db_session):
        """Should reject bridges in wormhole space."""
        with (
            patch.object(service, "_get_session", return_value=mock_db_session),
            pytest.raises(ValueError, match="wormhole space"),
        ):
            await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="J123456",
                    to_system="1DQ1-A",
                ),
            )

    @pytest.mark.asyncio
    async def test_reject_self_connection(self, service, mock_db_session):
        """Should reject connecting a system to itself."""
        with (
            patch.object(service, "_get_session", return_value=mock_db_session),
            pytest.raises(ValueError, match="Cannot connect system to itself"),
        ):
            await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="1DQ1-A",
                    to_system="1DQ1-A",
                ),
            )

    @pytest.mark.asyncio
    async def test_reject_unknown_system(self, service, mock_db_session):
        """Should reject unknown system names."""
        with (
            patch.object(service, "_get_session", return_value=mock_db_session),
            pytest.raises(ValueError, match="Unknown system"),
        ):
            await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="FakeSystem",
                    to_system="1DQ1-A",
                ),
            )

    @pytest.mark.asyncio
    async def test_reject_duplicate_bridge(self, service, mock_db_session):
        """Should reject duplicate bridge connections (including reverse direction)."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="1DQ1-A",
                    to_system="8QT-H4",
                ),
            )

            # Same direction
            with pytest.raises(ValueError, match="already exists"):
                await service.add_connection(
                    JumpBridgeConnectionCreate(
                        from_system="1DQ1-A",
                        to_system="8QT-H4",
                    ),
                )

            # Reverse direction
            with pytest.raises(ValueError, match="already exists"):
                await service.add_connection(
                    JumpBridgeConnectionCreate(
                        from_system="8QT-H4",
                        to_system="1DQ1-A",
                    ),
                )

    @pytest.mark.asyncio
    async def test_get_connection(self, service, mock_db_session):
        """Should retrieve a connection by ID."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn = await service.add_connection(
                JumpBridgeConnectionCreate(
                    from_system="1DQ1-A",
                    to_system="8QT-H4",
                ),
            )

        result = service.get_connection(conn.id)
        assert result is not None
        assert result.id == conn.id

    def test_get_connection_not_found(self, service):
        """Should return None for unknown ID."""
        assert service.get_connection("jb-nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_all_connections(self, service, mock_db_session):
        """Should return all connections."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            await service.add_connection(
                JumpBridgeConnectionCreate(from_system="1DQ1-A", to_system="8QT-H4"),
            )
            await service.add_connection(
                JumpBridgeConnectionCreate(from_system="49-U6U", to_system="PUIG-F"),
            )

        connections = service.get_all_connections()
        assert len(connections) == 2

    @pytest.mark.asyncio
    async def test_update_connection_status(self, service, mock_db_session):
        """Should update connection status."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn = await service.add_connection(
                JumpBridgeConnectionCreate(from_system="1DQ1-A", to_system="8QT-H4"),
            )

            updated = await service.update_connection(
                conn.id,
                JumpBridgeConnectionUpdate(status=JumpBridgeStatus.ONLINE),
            )

        assert updated is not None
        assert updated.status == JumpBridgeStatus.ONLINE

    @pytest.mark.asyncio
    async def test_update_connection_notes(self, service, mock_db_session):
        """Should update connection notes."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn = await service.add_connection(
                JumpBridgeConnectionCreate(from_system="1DQ1-A", to_system="8QT-H4"),
            )

            updated = await service.update_connection(
                conn.id,
                JumpBridgeConnectionUpdate(notes="Goons bridge"),
            )

        assert updated is not None
        assert updated.notes == "Goons bridge"

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, service, mock_db_session):
        """Should return None for updating nonexistent connection."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            result = await service.update_connection(
                "jb-nonexistent",
                JumpBridgeConnectionUpdate(status=JumpBridgeStatus.ONLINE),
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_connection(self, service, mock_db_session):
        """Should delete a connection."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn = await service.add_connection(
                JumpBridgeConnectionCreate(from_system="1DQ1-A", to_system="8QT-H4"),
            )

            result = await service.delete_connection(conn.id)

        assert result is True
        assert service.get_connection(conn.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, service, mock_db_session):
        """Should return False for deleting nonexistent connection."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            result = await service.delete_connection("jb-nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_active_bridges_excludes_offline(self, service, mock_db_session):
        """get_active_bridges should exclude offline bridges."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn1 = await service.add_connection(
                JumpBridgeConnectionCreate(from_system="1DQ1-A", to_system="8QT-H4"),
            )
            await service.add_connection(
                JumpBridgeConnectionCreate(from_system="49-U6U", to_system="PUIG-F"),
            )

            # Set first one offline
            await service.update_connection(
                conn1.id,
                JumpBridgeConnectionUpdate(status=JumpBridgeStatus.OFFLINE),
            )

        active = service.get_active_bridges()
        assert len(active) == 1
        assert active[0].from_system == "49-U6U"

    @pytest.mark.asyncio
    async def test_system_index(self, service, mock_db_session):
        """Should index connections by system name."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            await service.add_connection(
                JumpBridgeConnectionCreate(from_system="1DQ1-A", to_system="8QT-H4"),
            )

        # Both systems should be indexed
        conns = service.get_connections_for_system("1DQ1-A")
        assert len(conns) == 1
        conns = service.get_connections_for_system("8QT-H4")
        assert len(conns) == 1

    @pytest.mark.asyncio
    async def test_system_index_after_delete(self, service, mock_db_session):
        """System index should be cleaned up after deletion."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            conn = await service.add_connection(
                JumpBridgeConnectionCreate(from_system="1DQ1-A", to_system="8QT-H4"),
            )
            await service.delete_connection(conn.id)

        conns = service.get_connections_for_system("1DQ1-A")
        assert len(conns) == 0

    def test_get_stats_empty(self, service):
        """Stats should work with no connections."""
        stats = service.get_stats()
        assert stats["active_connections"] == 0
        assert stats["systems_with_bridges"] == 0


# ==================== Import Tests ====================


class TestImportParsing:
    """Tests for bulk import text parsing."""

    def test_parse_guillemet_format(self, service):
        """Should parse 'System A \u00bb System B' format."""
        creates, errors = service.parse_import_text("1DQ1-A \u00bb 8QT-H4")
        assert len(creates) == 1
        assert len(errors) == 0
        assert creates[0].from_system == "1DQ1-A"
        assert creates[0].to_system == "8QT-H4"

    def test_parse_arrow_format(self, service):
        """Should parse 'System A <-> System B' format."""
        creates, errors = service.parse_import_text("1DQ1-A <-> 8QT-H4")
        assert len(creates) == 1

    def test_parse_double_arrow_format(self, service):
        """Should parse 'System A --> System B' format."""
        creates, errors = service.parse_import_text("1DQ1-A --> 8QT-H4")
        assert len(creates) == 1

    def test_parse_multiple_lines(self, service):
        """Should parse multiple bridges."""
        text = "1DQ1-A \u00bb 8QT-H4\n49-U6U \u00bb PUIG-F"
        creates, errors = service.parse_import_text(text)
        assert len(creates) == 2
        assert len(errors) == 0

    def test_skip_comments(self, service):
        """Should skip comment lines starting with #."""
        text = "# Delve bridges\n1DQ1-A \u00bb 8QT-H4"
        creates, errors = service.parse_import_text(text)
        assert len(creates) == 1

    def test_skip_blank_lines(self, service):
        """Should skip blank lines."""
        text = "1DQ1-A \u00bb 8QT-H4\n\n49-U6U \u00bb PUIG-F"
        creates, errors = service.parse_import_text(text)
        assert len(creates) == 2

    def test_skip_duplicates(self, service):
        """Should silently skip duplicate entries."""
        text = "1DQ1-A \u00bb 8QT-H4\n8QT-H4 \u00bb 1DQ1-A"
        creates, errors = service.parse_import_text(text)
        assert len(creates) == 1

    def test_error_on_unknown_system(self, service):
        """Should report error for unknown systems."""
        creates, errors = service.parse_import_text("FakeSystem \u00bb 1DQ1-A")
        assert len(creates) == 0
        assert len(errors) == 1
        assert "Unknown system" in errors[0]

    def test_error_on_highsec_system(self, service):
        """Should report error for highsec systems."""
        creates, errors = service.parse_import_text("Jita \u00bb 1DQ1-A")
        assert len(creates) == 0
        assert len(errors) == 1
        assert "highsec" in errors[0]

    def test_error_on_unparseable_line(self, service):
        """Should report error for unparseable lines."""
        creates, errors = service.parse_import_text("this is not a bridge")
        assert len(creates) == 0
        assert len(errors) == 1
        assert "Could not parse" in errors[0]

    @pytest.mark.asyncio
    async def test_import_bridges(self, service, mock_db_session):
        """Should import bridges from text and persist them."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            result = await service.import_bridges(
                "1DQ1-A \u00bb 8QT-H4\n49-U6U \u00bb PUIG-F",
                created_by="TestPilot",
            )

        assert result.imported == 2
        assert result.skipped == 0
        assert len(result.errors) == 0
        assert len(result.bridges) == 2
        assert service.get_all_connections().__len__() == 2

    @pytest.mark.asyncio
    async def test_import_mixed_valid_invalid(self, service, mock_db_session):
        """Should import valid lines and report errors for invalid."""
        with patch.object(service, "_get_session", return_value=mock_db_session):
            result = await service.import_bridges(
                "1DQ1-A \u00bb 8QT-H4\nJita \u00bb Amarr",
                created_by="TestPilot",
            )

        assert result.imported == 1
        assert len(result.errors) == 1


# ==================== Separator Pattern Tests ====================


class TestSeparatorPatterns:
    """Test that the separator patterns match all expected formats."""

    def _match(self, text: str) -> tuple[str, str] | None:
        for pattern in _SEP_PATTERNS:
            m = pattern.match(text)
            if m:
                return m.group(1).strip(), m.group(2).strip()
        return None

    def test_guillemet(self):
        """Should match \u00bb separator."""
        result = self._match("1DQ1-A \u00bb 8QT-H4")
        assert result == ("1DQ1-A", "8QT-H4")

    def test_bidirectional_arrow(self):
        """Should match <-> separator."""
        result = self._match("1DQ1-A <-> 8QT-H4")
        assert result == ("1DQ1-A", "8QT-H4")

    def test_angle_brackets(self):
        """Should match <> separator."""
        result = self._match("1DQ1-A <> 8QT-H4")
        assert result == ("1DQ1-A", "8QT-H4")

    def test_single_arrow(self):
        """Should match --> separator."""
        result = self._match("1DQ1-A --> 8QT-H4")
        assert result == ("1DQ1-A", "8QT-H4")

    def test_no_false_match_on_hyphenated_name(self):
        """Should not split on hyphens within system names."""
        # "1DQ1-A" should NOT be split as "1DQ1" + "A"
        result = self._match("1DQ1-A")
        assert result is None
