"""Unit tests for character API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import Response

from backend.app.api.v1.character import (
    CharacterLocation,
    CharacterOnlineStatus,
    CharacterShip,
    WaypointRequest,
    WaypointResponse,
    get_character_location,
    get_character_online,
    get_character_ship,
    set_waypoint,
    set_route_destination,
)
from backend.app.api.v1.dependencies import AuthenticatedCharacter


@pytest.fixture
def mock_character():
    """Create a mock authenticated character."""
    return AuthenticatedCharacter(
        character_id=12345,
        character_name="Test Pilot",
        access_token="test_token",
        scopes=["esi-location.read_location.v1", "esi-ui.write_waypoint.v1"],
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


class TestCharacterLocationModels:
    """Tests for character response models."""

    def test_character_location_model(self):
        """Test CharacterLocation model creation."""
        loc = CharacterLocation(
            solar_system_id=30000142,
            solar_system_name="Jita",
            security=0.95,
            region_name="The Forge",
        )
        assert loc.solar_system_id == 30000142
        assert loc.solar_system_name == "Jita"
        assert loc.security == 0.95
        assert loc.station_id is None

    def test_character_location_minimal(self):
        """Test CharacterLocation with minimal fields."""
        loc = CharacterLocation(solar_system_id=30000142)
        assert loc.solar_system_id == 30000142
        assert loc.solar_system_name is None

    def test_character_online_status_model(self):
        """Test CharacterOnlineStatus model."""
        status = CharacterOnlineStatus(
            online=True,
            last_login="2024-01-01T12:00:00Z",
            logins=100,
        )
        assert status.online is True
        assert status.logins == 100

    def test_character_ship_model(self):
        """Test CharacterShip model."""
        ship = CharacterShip(
            ship_type_id=587,  # Rifter
            ship_item_id=1234567890,
            ship_name="My Rifter",
        )
        assert ship.ship_type_id == 587
        assert ship.ship_name == "My Rifter"

    def test_waypoint_request_model(self):
        """Test WaypointRequest model with defaults."""
        req = WaypointRequest(destination_id=30000142)
        assert req.destination_id == 30000142
        assert req.add_to_beginning is False
        assert req.clear_other_waypoints is False

    def test_waypoint_request_custom(self):
        """Test WaypointRequest with custom values."""
        req = WaypointRequest(
            destination_id=30000142,
            add_to_beginning=True,
            clear_other_waypoints=True,
        )
        assert req.add_to_beginning is True
        assert req.clear_other_waypoints is True

    def test_waypoint_response_model(self):
        """Test WaypointResponse model."""
        resp = WaypointResponse(
            success=True,
            destination_id=30000142,
            destination_name="Jita",
        )
        assert resp.success is True
        assert resp.destination_name == "Jita"


class TestGetCharacterLocation:
    """Tests for get_character_location endpoint."""

    @pytest.mark.asyncio
    async def test_location_success(self, mock_character):
        """Test successful location retrieval."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "solar_system_id": 30000142,
            "station_id": 60003760,
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe") as mock_universe:
                mock_sys = MagicMock()
                mock_sys.id = 30000142
                mock_sys.name = "Jita"
                mock_sys.security = 0.95
                mock_sys.region_name = "The Forge"
                mock_universe.return_value.systems.values.return_value = [mock_sys]

                result = await get_character_location(mock_character)

        assert result.solar_system_id == 30000142
        assert result.solar_system_name == "Jita"
        assert result.security == 0.95
        assert result.station_id == 60003760

    @pytest.mark.asyncio
    async def test_location_401_error(self, mock_character):
        """Test location with expired token returns 401."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_character_location(mock_character)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_location_esi_error(self, mock_character):
        """Test location with ESI error."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_character_location(mock_character)

        assert exc_info.value.status_code == 503
        assert "ESI error" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_location_without_universe_enrichment(self, mock_character):
        """Test location works when universe loading fails."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"solar_system_id": 30000142}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", side_effect=Exception("Load failed")):
                result = await get_character_location(mock_character)

        # Should still return the location without enrichment
        assert result.solar_system_id == 30000142
        assert result.solar_system_name is None


class TestGetCharacterOnline:
    """Tests for get_character_online endpoint."""

    @pytest.mark.asyncio
    async def test_online_success(self, mock_character):
        """Test successful online status retrieval."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "online": True,
            "last_login": "2024-01-01T12:00:00Z",
            "logins": 50,
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            result = await get_character_online(mock_character)

        assert result.online is True
        assert result.logins == 50

    @pytest.mark.asyncio
    async def test_online_offline_character(self, mock_character):
        """Test online status for offline character."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "online": False,
            "last_logout": "2024-01-01T10:00:00Z",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            result = await get_character_online(mock_character)

        assert result.online is False
        assert result.last_logout == "2024-01-01T10:00:00Z"

    @pytest.mark.asyncio
    async def test_online_401_error(self, mock_character):
        """Test online with expired token."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_character_online(mock_character)

        assert exc_info.value.status_code == 401


class TestGetCharacterShip:
    """Tests for get_character_ship endpoint."""

    @pytest.mark.asyncio
    async def test_ship_success(self, mock_character):
        """Test successful ship retrieval."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ship_type_id": 587,  # Rifter
            "ship_item_id": 1234567890,
            "ship_name": "Combat Rifter",
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            result = await get_character_ship(mock_character)

        assert result.ship_type_id == 587
        assert result.ship_item_id == 1234567890
        assert result.ship_name == "Combat Rifter"

    @pytest.mark.asyncio
    async def test_ship_without_name(self, mock_character):
        """Test ship retrieval when ship has no custom name."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ship_type_id": 587,
            "ship_item_id": 1234567890,
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            result = await get_character_ship(mock_character)

        assert result.ship_type_id == 587
        assert result.ship_name is None

    @pytest.mark.asyncio
    async def test_ship_esi_error(self, mock_character):
        """Test ship with ESI error."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_character_ship(mock_character)

        assert exc_info.value.status_code == 500


class TestSetWaypoint:
    """Tests for set_waypoint endpoint."""

    @pytest.mark.asyncio
    async def test_waypoint_success(self, mock_character):
        """Test successful waypoint setting."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 204  # No content

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        waypoint = WaypointRequest(destination_id=30000142)

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe") as mock_universe:
                mock_sys = MagicMock()
                mock_sys.id = 30000142
                mock_sys.name = "Jita"
                mock_universe.return_value.systems.values.return_value = [mock_sys]

                result = await set_waypoint(waypoint, mock_character)

        assert result.success is True
        assert result.destination_id == 30000142
        assert result.destination_name == "Jita"

    @pytest.mark.asyncio
    async def test_waypoint_200_response(self, mock_character):
        """Test waypoint with 200 response (also valid)."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        waypoint = WaypointRequest(destination_id=30000142)

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", side_effect=Exception):
                result = await set_waypoint(waypoint, mock_character)

        assert result.success is True
        assert result.destination_name is None

    @pytest.mark.asyncio
    async def test_waypoint_with_options(self, mock_character):
        """Test waypoint with add_to_beginning and clear options."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        waypoint = WaypointRequest(
            destination_id=30000142,
            add_to_beginning=True,
            clear_other_waypoints=True,
        )

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", side_effect=Exception):
                result = await set_waypoint(waypoint, mock_character)

        assert result.success is True
        # Verify the POST was called with correct params
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["params"]["add_to_beginning"] == "true"
        assert call_kwargs.kwargs["params"]["clear_other_waypoints"] == "true"

    @pytest.mark.asyncio
    async def test_waypoint_401_error(self, mock_character):
        """Test waypoint with expired token."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        waypoint = WaypointRequest(destination_id=30000142)

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await set_waypoint(waypoint, mock_character)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_waypoint_esi_error(self, mock_character):
        """Test waypoint with ESI error."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 403
        mock_response.text = "Character not online"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        waypoint = WaypointRequest(destination_id=30000142)

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await set_waypoint(waypoint, mock_character)

        assert exc_info.value.status_code == 403
        assert "ESI error" in exc_info.value.detail


class TestSetRouteDestination:
    """Tests for set_route_destination endpoint."""

    @pytest.mark.asyncio
    async def test_route_destination_success(self, mock_character):
        """Test successful route destination setting."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", side_effect=Exception):
                result = await set_route_destination(30000142, mock_character)

        assert result.success is True
        assert result.destination_id == 30000142

        # Verify it clears other waypoints
        call_kwargs = mock_client.post.call_args
        assert call_kwargs.kwargs["params"]["clear_other_waypoints"] == "true"
        assert call_kwargs.kwargs["params"]["add_to_beginning"] == "false"

    @pytest.mark.asyncio
    async def test_route_destination_delegates_to_waypoint(self, mock_character):
        """Test that route destination uses set_waypoint internally."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe") as mock_universe:
                mock_sys = MagicMock()
                mock_sys.id = 30000142
                mock_sys.name = "Jita"
                mock_universe.return_value.systems.values.return_value = [mock_sys]

                result = await set_route_destination(30000142, mock_character)

        assert result.destination_name == "Jita"
