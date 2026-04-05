"""Unit tests for fleet tracker API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.app.api.v1.dependencies import AuthenticatedCharacter
from backend.app.api.v1.fleet_tracker import (
    FleetCreateResponse,
    FleetJoinResponse,
    FleetLeaveResponse,
    FleetMember,
    FleetMembersResponse,
    _cleanup_expired,
    _fleet_sessions,
    _generate_share_code,
    create_fleet,
    get_fleet_members,
    join_fleet,
    leave_fleet,
)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear fleet sessions before and after each test."""
    _fleet_sessions.clear()
    yield
    _fleet_sessions.clear()


@pytest.fixture
def mock_character():
    """Create a mock authenticated character."""
    return AuthenticatedCharacter(
        character_id=12345,
        character_name="Test Pilot",
        access_token="test_token_abc",
        scopes=["esi-location.read_location.v1"],
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


@pytest.fixture
def mock_character_2():
    """Create a second mock authenticated character."""
    return AuthenticatedCharacter(
        character_id=67890,
        character_name="Alt Pilot",
        access_token="test_token_def",
        scopes=["esi-location.read_location.v1"],
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


@pytest.fixture
def mock_character_3():
    """Create a third mock authenticated character."""
    return AuthenticatedCharacter(
        character_id=11111,
        character_name="Third Pilot",
        access_token="test_token_ghi",
        scopes=["esi-location.read_location.v1"],
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


# =============================================================================
# Model Tests
# =============================================================================


class TestFleetModels:
    """Tests for fleet tracker response models."""

    def test_fleet_create_response(self):
        resp = FleetCreateResponse(
            code="ABC123",
            created_at="2026-01-01T00:00:00Z",
            expires_at="2026-01-01T04:00:00Z",
            owner_character_id=12345,
        )
        assert resp.code == "ABC123"
        assert resp.owner_character_id == 12345

    def test_fleet_join_response(self):
        resp = FleetJoinResponse(
            code="ABC123",
            character_id=67890,
            character_name="Alt Pilot",
            member_count=2,
        )
        assert resp.member_count == 2

    def test_fleet_member_defaults(self):
        member = FleetMember(
            character_id=12345,
            character_name="Test Pilot",
        )
        assert member.system_id is None
        assert member.ship_type_id is None
        assert member.online is False

    def test_fleet_member_with_location(self):
        member = FleetMember(
            character_id=12345,
            character_name="Test Pilot",
            system_id=30000142,
            system_name="Jita",
            ship_type_id=587,
            ship_type_name="Rifter",
            online=True,
            last_updated="2026-01-01T00:00:00Z",
        )
        assert member.system_name == "Jita"
        assert member.online is True

    def test_fleet_members_response(self):
        resp = FleetMembersResponse(
            code="ABC123",
            member_count=1,
            members=[
                FleetMember(character_id=12345, character_name="Test Pilot"),
            ],
        )
        assert len(resp.members) == 1

    def test_fleet_leave_response(self):
        resp = FleetLeaveResponse(
            code="ABC123",
            character_id=12345,
            remaining_members=0,
        )
        assert resp.remaining_members == 0


# =============================================================================
# Share Code Generation
# =============================================================================


class TestShareCode:
    """Tests for share code generation."""

    def test_share_code_length(self):
        code = _generate_share_code()
        assert len(code) == 6

    def test_share_code_uppercase(self):
        code = _generate_share_code()
        assert code == code.upper()

    def test_share_codes_unique(self):
        codes = {_generate_share_code() for _ in range(100)}
        # Should have high uniqueness (allow a few collisions)
        assert len(codes) > 90


# =============================================================================
# Session Cleanup
# =============================================================================


class TestSessionCleanup:
    """Tests for expired session cleanup."""

    def test_cleanup_expired_sessions(self):
        _fleet_sessions["OLD"] = {
            "owner_character_id": 1,
            "created_at": datetime.now(UTC) - timedelta(hours=5),
            "expires_at": datetime.now(UTC) - timedelta(hours=1),
            "members": {},
        }
        _fleet_sessions["NEW"] = {
            "owner_character_id": 2,
            "created_at": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + timedelta(hours=3),
            "members": {},
        }
        _cleanup_expired()
        assert "OLD" not in _fleet_sessions
        assert "NEW" in _fleet_sessions

    def test_cleanup_no_expired(self):
        _fleet_sessions["ACTIVE"] = {
            "owner_character_id": 1,
            "created_at": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + timedelta(hours=4),
            "members": {},
        }
        _cleanup_expired()
        assert "ACTIVE" in _fleet_sessions


# =============================================================================
# Create Fleet
# =============================================================================


class TestCreateFleet:
    """Tests for fleet creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_fleet_success(self, mock_character):
        result = await create_fleet(mock_character)
        assert isinstance(result, FleetCreateResponse)
        assert len(result.code) == 6
        assert result.owner_character_id == 12345
        assert result.code in _fleet_sessions

    @pytest.mark.asyncio
    async def test_create_fleet_adds_creator(self, mock_character):
        result = await create_fleet(mock_character)
        session = _fleet_sessions[result.code]
        assert 12345 in session["members"]
        assert session["members"][12345]["character_name"] == "Test Pilot"

    @pytest.mark.asyncio
    async def test_create_fleet_expiry(self, mock_character):
        result = await create_fleet(mock_character)
        session = _fleet_sessions[result.code]
        assert session["expires_at"] > datetime.now(UTC)
        assert session["expires_at"] < datetime.now(UTC) + timedelta(hours=5)

    @pytest.mark.asyncio
    async def test_create_multiple_fleets(self, mock_character, mock_character_2):
        r1 = await create_fleet(mock_character)
        r2 = await create_fleet(mock_character_2)
        assert r1.code != r2.code
        assert len(_fleet_sessions) == 2


# =============================================================================
# Join Fleet
# =============================================================================


class TestJoinFleet:
    """Tests for fleet join endpoint."""

    @pytest.mark.asyncio
    async def test_join_fleet_success(self, mock_character, mock_character_2):
        created = await create_fleet(mock_character)
        result = await join_fleet(created.code, mock_character_2)
        assert isinstance(result, FleetJoinResponse)
        assert result.character_id == 67890
        assert result.member_count == 2

    @pytest.mark.asyncio
    async def test_join_fleet_case_insensitive(self, mock_character, mock_character_2):
        created = await create_fleet(mock_character)
        # Join with lowercase
        result = await join_fleet(created.code.lower(), mock_character_2)
        assert result.member_count == 2

    @pytest.mark.asyncio
    async def test_join_nonexistent_fleet(self, mock_character):
        with pytest.raises(HTTPException) as exc:
            await join_fleet("XXXXXX", mock_character)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rejoin_fleet_updates(self, mock_character, mock_character_2):
        """Rejoining a fleet updates the member entry, doesn't duplicate."""
        created = await create_fleet(mock_character)
        await join_fleet(created.code, mock_character_2)
        await join_fleet(created.code, mock_character_2)
        session = _fleet_sessions[created.code]
        assert len(session["members"]) == 2  # Still 2, not 3


# =============================================================================
# Get Fleet Members
# =============================================================================


class TestGetFleetMembers:
    """Tests for fleet member locations endpoint."""

    @pytest.mark.asyncio
    async def test_get_members_non_member(self, mock_character, mock_character_2, mock_character_3):
        """Non-members cannot see fleet member locations."""
        created = await create_fleet(mock_character)
        with pytest.raises(HTTPException) as exc:
            await get_fleet_members(created.code, mock_character_3)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_members_nonexistent(self, mock_character):
        with pytest.raises(HTTPException) as exc:
            await get_fleet_members("XXXXXX", mock_character)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.fleet_tracker.get_token_store")
    @patch("backend.app.api.v1.fleet_tracker._fetch_member_location")
    async def test_get_members_success(
        self, mock_fetch, mock_store_fn, mock_character, mock_character_2
    ):
        """Get members returns location data for all members."""
        # Setup
        created = await create_fleet(mock_character)
        await join_fleet(created.code, mock_character_2)

        mock_store = MagicMock()
        mock_store.get_token = AsyncMock(
            return_value={
                "access_token": "token",
                "expires_at": datetime.now(UTC) + timedelta(hours=1),
            }
        )
        mock_store_fn.return_value = mock_store

        mock_fetch.return_value = FleetMember(
            character_id=12345,
            character_name="Test Pilot",
            system_id=30000142,
            system_name="Jita",
            online=True,
        )

        result = await get_fleet_members(created.code, mock_character)
        assert isinstance(result, FleetMembersResponse)
        assert result.member_count == 2

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.fleet_tracker.get_token_store")
    async def test_get_members_expired_token(self, mock_store_fn, mock_character):
        """Members with expired tokens return offline with no location."""
        created = await create_fleet(mock_character)

        mock_store = MagicMock()
        mock_store.get_token = AsyncMock(
            return_value={
                "access_token": "expired_token",
                "expires_at": datetime.now(UTC) - timedelta(hours=1),
            }
        )
        mock_store_fn.return_value = mock_store

        result = await get_fleet_members(created.code, mock_character)
        assert result.member_count == 1
        assert result.members[0].online is False
        assert result.members[0].system_id is None

    @pytest.mark.asyncio
    @patch("backend.app.api.v1.fleet_tracker.get_token_store")
    async def test_get_members_no_stored_token(self, mock_store_fn, mock_character):
        """Members with no stored token return offline."""
        created = await create_fleet(mock_character)

        mock_store = MagicMock()
        mock_store.get_token = AsyncMock(return_value=None)
        mock_store_fn.return_value = mock_store

        result = await get_fleet_members(created.code, mock_character)
        assert result.member_count == 1
        assert result.members[0].online is False


# =============================================================================
# Leave Fleet
# =============================================================================


class TestLeaveFleet:
    """Tests for fleet leave endpoint."""

    @pytest.mark.asyncio
    async def test_leave_fleet_success(self, mock_character, mock_character_2):
        created = await create_fleet(mock_character)
        await join_fleet(created.code, mock_character_2)
        result = await leave_fleet(created.code, mock_character_2)
        assert isinstance(result, FleetLeaveResponse)
        assert result.remaining_members == 1

    @pytest.mark.asyncio
    async def test_leave_fleet_last_member_cleans_up(self, mock_character):
        created = await create_fleet(mock_character)
        result = await leave_fleet(created.code, mock_character)
        assert result.remaining_members == 0
        assert created.code not in _fleet_sessions

    @pytest.mark.asyncio
    async def test_leave_nonexistent_fleet(self, mock_character):
        with pytest.raises(HTTPException) as exc:
            await leave_fleet("XXXXXX", mock_character)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_leave_fleet_not_member(self, mock_character, mock_character_2):
        created = await create_fleet(mock_character)
        with pytest.raises(HTTPException) as exc:
            await leave_fleet(created.code, mock_character_2)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_leave_fleet_case_insensitive(self, mock_character):
        created = await create_fleet(mock_character)
        result = await leave_fleet(created.code.lower(), mock_character)
        assert result.remaining_members == 0


# =============================================================================
# Integration: Full Flow
# =============================================================================


class TestFleetTrackerFlow:
    """End-to-end flow tests for fleet tracking."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_character, mock_character_2):
        """Create → join → verify membership → leave → cleanup."""
        # Create
        created = await create_fleet(mock_character)
        assert len(_fleet_sessions) == 1

        # Join
        joined = await join_fleet(created.code, mock_character_2)
        assert joined.member_count == 2

        # Leave (second member)
        left = await leave_fleet(created.code, mock_character_2)
        assert left.remaining_members == 1

        # Leave (creator) — session cleaned up
        left2 = await leave_fleet(created.code, mock_character)
        assert left2.remaining_members == 0
        assert len(_fleet_sessions) == 0

    @pytest.mark.asyncio
    async def test_expired_session_rejected(self, mock_character, mock_character_2):
        """Joining an expired session fails with 404."""
        created = await create_fleet(mock_character)
        # Manually expire the session
        _fleet_sessions[created.code]["expires_at"] = datetime.now(UTC) - timedelta(hours=1)

        with pytest.raises(HTTPException) as exc:
            await join_fleet(created.code, mock_character_2)
        assert exc.value.status_code == 404
