"""Unit tests for WebSocket endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestKillfeedWebSocket:
    """Tests for kill feed WebSocket endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    def test_websocket_connect(self, client):
        """Test WebSocket connection and welcome message."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws:
            data = ws.receive_json()

            assert data["type"] == "connected"
            assert "client_id" in data
            assert "message" in data
            assert "active_connections" in data

    def test_websocket_ping_pong(self, client):
        """Test ping/pong message."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws:
            # Skip welcome message
            ws.receive_json()

            # Send ping
            ws.send_json({"type": "ping"})
            data = ws.receive_json()

            assert data["type"] == "pong"

    def test_websocket_status(self, client):
        """Test status request."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws:
            # Skip welcome message
            ws.receive_json()

            # Request status
            ws.send_json({"type": "status"})
            data = ws.receive_json()

            assert data["type"] == "status"
            assert "data" in data

    def test_websocket_subscribe(self, client):
        """Test subscription to systems and regions."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws:
            # Skip welcome message
            ws.receive_json()

            # Subscribe
            ws.send_json({
                "type": "subscribe",
                "systems": [30000142, 30002187],
                "regions": [10000002],
                "min_value": 1000000,
                "include_pods": False,
            })
            data = ws.receive_json()

            assert data["type"] == "subscribed"
            assert "filters" in data
            assert data["filters"]["systems"] == [30000142, 30002187]
            assert data["filters"]["regions"] == [10000002]
            assert data["filters"]["min_value"] == 1000000
            assert data["filters"]["include_pods"] is False

    def test_websocket_subscribe_partial(self, client):
        """Test partial subscription (only some filters)."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws:
            # Skip welcome message
            ws.receive_json()

            # Subscribe with only systems
            ws.send_json({
                "type": "subscribe",
                "systems": [30000142],
            })
            data = ws.receive_json()

            assert data["type"] == "subscribed"
            assert data["filters"]["systems"] == [30000142]
            assert data["filters"]["regions"] is None
            assert data["filters"]["min_value"] is None

    def test_websocket_unknown_message_type(self, client):
        """Test handling of unknown message type."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws:
            # Skip welcome message
            ws.receive_json()

            # Send unknown type
            ws.send_json({"type": "invalid_type"})
            data = ws.receive_json()

            assert data["type"] == "error"
            assert "Unknown message type" in data["message"]
            assert "valid_types" in data

    def test_websocket_invalid_json(self, client):
        """Test handling of invalid JSON."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws:
            # Skip welcome message
            ws.receive_json()

            # Send invalid JSON (as text, not json)
            ws.send_text("not valid json")
            data = ws.receive_json()

            assert data["type"] == "error"
            assert "Invalid JSON" in data["message"]

    def test_multiple_connections(self, client):
        """Test multiple simultaneous WebSocket connections."""
        with client.websocket_connect("/api/v1/ws/killfeed") as ws1:
            data1 = ws1.receive_json()
            client_id_1 = data1["client_id"]

            with client.websocket_connect("/api/v1/ws/killfeed") as ws2:
                data2 = ws2.receive_json()
                client_id_2 = data2["client_id"]

                # Each connection should have unique ID
                assert client_id_1 != client_id_2

                # Connection count should increase
                assert data2["active_connections"] >= data1["active_connections"]
