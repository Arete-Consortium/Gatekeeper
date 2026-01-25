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
    RouteFromHereRequest,
    RouteFromHereResponse,
    SetRouteWaypointsRequest,
    SetRouteWaypointsResponse,
    get_character_location,
    get_character_online,
    get_character_ship,
    set_waypoint,
    set_route_destination,
    get_route_from_current_location,
    set_route_waypoints,
)
from backend.app.api.v1.dependencies import AuthenticatedCharacter
from backend.app.models.route import RouteResponse, RouteHop


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


class TestRouteFromHereModels:
    """Tests for route from here request/response models."""

    def test_route_from_here_request_defaults(self):
        """Test RouteFromHereRequest with defaults."""
        req = RouteFromHereRequest(destination="Amarr")
        assert req.destination == "Amarr"
        assert req.profile == "safer"
        assert req.avoid == []
        assert req.use_bridges is False

    def test_route_from_here_request_custom(self):
        """Test RouteFromHereRequest with custom values."""
        req = RouteFromHereRequest(
            destination="Amarr",
            profile="paranoid",
            avoid=["Rancer", "Uedama"],
            use_bridges=True,
        )
        assert req.profile == "paranoid"
        assert "Rancer" in req.avoid
        assert req.use_bridges is True

    def test_set_waypoints_request_model(self):
        """Test SetRouteWaypointsRequest model."""
        req = SetRouteWaypointsRequest(systems=["Jita", "Perimeter", "Urlen"])
        assert len(req.systems) == 3
        assert req.clear_existing is True

    def test_set_waypoints_request_no_clear(self):
        """Test SetRouteWaypointsRequest without clearing."""
        req = SetRouteWaypointsRequest(
            systems=["Amarr"],
            clear_existing=False,
        )
        assert req.clear_existing is False

    def test_set_waypoints_response_model(self):
        """Test SetRouteWaypointsResponse model."""
        resp = SetRouteWaypointsResponse(
            success=True,
            waypoints_set=3,
            systems=["Jita", "Perimeter", "Urlen"],
        )
        assert resp.success is True
        assert resp.waypoints_set == 3


class TestGetRouteFromCurrentLocation:
    """Tests for get_route_from_current_location endpoint."""

    @pytest.mark.asyncio
    async def test_route_from_here_success(self, mock_character):
        """Test successful route from current location."""
        # Mock ESI response for location
        mock_location_response = MagicMock(spec=Response)
        mock_location_response.status_code = 200
        mock_location_response.json.return_value = {"solar_system_id": 30000142}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_location_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        # Mock universe with systems
        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.name = "Jita"
        mock_jita.security = 0.95
        mock_jita.region_name = "The Forge"

        mock_amarr = MagicMock()
        mock_amarr.id = 30002187
        mock_amarr.name = "Amarr"
        mock_amarr.security = 1.0

        # Use MagicMock for systems to support both __contains__ and .values()
        mock_systems = MagicMock()
        mock_systems.__contains__ = MagicMock(side_effect=lambda key: key in ["Jita", "Amarr"])
        mock_systems.values.return_value = [mock_jita, mock_amarr]

        mock_universe = MagicMock()
        mock_universe.systems = mock_systems

        # Mock route computation
        mock_route = RouteResponse(
            from_system="Jita",
            to_system="Amarr",
            profile="safer",
            total_jumps=10,
            total_cost=10.0,
            max_risk=20.0,
            avg_risk=10.0,
            path=[
                RouteHop(system_name="Jita", system_id=30000142, cumulative_jumps=0, cumulative_cost=0, risk_score=5.0),
                RouteHop(system_name="Amarr", system_id=30002187, cumulative_jumps=10, cumulative_cost=10.0, risk_score=3.0),
            ],
        )

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", return_value=mock_universe):
                with patch("backend.app.api.v1.character.compute_route", return_value=mock_route):
                    result = await get_route_from_current_location(
                        destination="Amarr",
                        profile="safer",
                        avoid=None,
                        bridges=False,
                        character=mock_character,
                    )

        assert result.current_system == "Jita"
        assert result.destination == "Amarr"
        assert result.route.total_jumps == 10

    @pytest.mark.asyncio
    async def test_route_from_here_unknown_destination(self, mock_character):
        """Test route from here with unknown destination."""
        mock_location_response = MagicMock(spec=Response)
        mock_location_response.status_code = 200
        mock_location_response.json.return_value = {"solar_system_id": 30000142}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_location_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.name = "Jita"
        mock_jita.security = 0.95
        mock_jita.region_name = "The Forge"

        # Use MagicMock for systems to support both __contains__ and .values()
        mock_systems = MagicMock()
        mock_systems.__contains__ = MagicMock(side_effect=lambda key: key in ["Jita"])
        mock_systems.values.return_value = [mock_jita]

        mock_universe = MagicMock()
        mock_universe.systems = mock_systems

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", return_value=mock_universe):
                with pytest.raises(HTTPException) as exc_info:
                    await get_route_from_current_location(
                        destination="NonExistent",
                        profile="safer",
                        avoid=None,
                        bridges=False,
                        character=mock_character,
                    )

        assert exc_info.value.status_code == 404
        assert "Unknown destination" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_route_from_here_no_route_found(self, mock_character):
        """Test route from here when no route exists."""
        mock_location_response = MagicMock(spec=Response)
        mock_location_response.status_code = 200
        mock_location_response.json.return_value = {"solar_system_id": 30000142}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_location_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.name = "Jita"
        mock_jita.security = 0.95
        mock_jita.region_name = "The Forge"

        mock_amarr = MagicMock()
        mock_amarr.id = 30002187
        mock_amarr.name = "Amarr"

        # Use MagicMock for systems to support both __contains__ and .values()
        mock_systems = MagicMock()
        mock_systems.__contains__ = MagicMock(side_effect=lambda key: key in ["Jita", "Amarr"])
        mock_systems.values.return_value = [mock_jita, mock_amarr]

        mock_universe = MagicMock()
        mock_universe.systems = mock_systems

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", return_value=mock_universe):
                with patch("backend.app.api.v1.character.compute_route", return_value=None):
                    with pytest.raises(HTTPException) as exc_info:
                        await get_route_from_current_location(
                            destination="Amarr",
                            profile="safer",
                            avoid=None,
                            bridges=False,
                            character=mock_character,
                        )

        assert exc_info.value.status_code == 404
        assert "No route found" in exc_info.value.detail


class TestSetRouteWaypoints:
    """Tests for set_route_waypoints endpoint."""

    @pytest.mark.asyncio
    async def test_set_waypoints_success(self, mock_character):
        """Test successful setting of multiple waypoints."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.name = "Jita"

        mock_perimeter = MagicMock()
        mock_perimeter.id = 30000144
        mock_perimeter.name = "Perimeter"

        mock_universe = MagicMock()
        mock_universe.systems.values.return_value = [mock_jita, mock_perimeter]

        request = SetRouteWaypointsRequest(systems=["Jita", "Perimeter"])

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", return_value=mock_universe):
                result = await set_route_waypoints(request, mock_character)

        assert result.success is True
        assert result.waypoints_set == 2
        assert result.systems == ["Jita", "Perimeter"]

        # Should have been called twice
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_set_waypoints_clears_first(self, mock_character):
        """Test that first waypoint clears existing ones."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.name = "Jita"

        mock_perimeter = MagicMock()
        mock_perimeter.id = 30000144
        mock_perimeter.name = "Perimeter"

        mock_universe = MagicMock()
        mock_universe.systems.values.return_value = [mock_jita, mock_perimeter]

        request = SetRouteWaypointsRequest(systems=["Jita", "Perimeter"], clear_existing=True)

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", return_value=mock_universe):
                await set_route_waypoints(request, mock_character)

        # Check first call clears, second doesn't
        calls = mock_client.post.call_args_list
        assert calls[0].kwargs["params"]["clear_other_waypoints"] == "true"
        assert calls[1].kwargs["params"]["clear_other_waypoints"] == "false"

    @pytest.mark.asyncio
    async def test_set_waypoints_unknown_system(self, mock_character):
        """Test setting waypoints with unknown system."""
        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.name = "Jita"

        mock_universe = MagicMock()
        mock_universe.systems.values.return_value = [mock_jita]

        request = SetRouteWaypointsRequest(systems=["Jita", "NonExistent"])

        with patch("backend.app.api.v1.character.load_universe", return_value=mock_universe):
            with pytest.raises(HTTPException) as exc_info:
                await set_route_waypoints(request, mock_character)

        assert exc_info.value.status_code == 404
        assert "Unknown system" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_set_waypoints_esi_error(self, mock_character):
        """Test setting waypoints with ESI error."""
        mock_response = MagicMock(spec=Response)
        mock_response.status_code = 403
        mock_response.text = "Character not online"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_jita = MagicMock()
        mock_jita.id = 30000142
        mock_jita.name = "Jita"

        mock_universe = MagicMock()
        mock_universe.systems.values.return_value = [mock_jita]

        request = SetRouteWaypointsRequest(systems=["Jita"])

        with patch("backend.app.api.v1.character.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.app.api.v1.character.load_universe", return_value=mock_universe):
                with pytest.raises(HTTPException) as exc_info:
                    await set_route_waypoints(request, mock_character)

        assert exc_info.value.status_code == 403
        assert "ESI error" in exc_info.value.detail
