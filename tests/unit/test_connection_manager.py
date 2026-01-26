"""Unit tests for WebSocket connection manager."""

from unittest.mock import AsyncMock

import pytest

from backend.app.services.connection_manager import (
    ClientSubscription,
    ConnectionManager,
)


class TestClientSubscription:
    """Tests for ClientSubscription dataclass."""

    def test_default_values(self):
        """Test default subscription values."""
        sub = ClientSubscription()
        assert sub.systems == set()
        assert sub.regions == set()
        assert sub.min_value == 0
        assert sub.include_pods is True

    def test_custom_values(self):
        """Test custom subscription values."""
        sub = ClientSubscription(
            systems={30000142},
            regions={10000002},
            min_value=1000000,
            include_pods=False,
        )
        assert 30000142 in sub.systems
        assert 10000002 in sub.regions
        assert sub.min_value == 1000000
        assert sub.include_pods is False


class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a client."""
        await manager.connect("client1", mock_websocket)
        assert manager.connection_count == 1
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a client."""
        await manager.connect("client1", mock_websocket)
        assert manager.connection_count == 1

        await manager.disconnect("client1")
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent(self, manager):
        """Test disconnecting a nonexistent client."""
        await manager.disconnect("nonexistent")
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_update_subscription(self, manager, mock_websocket):
        """Test updating client subscription."""
        await manager.connect("client1", mock_websocket)

        result = await manager.update_subscription(
            "client1",
            systems=[30000142, 30000144],
            regions=[10000002],
            min_value=1000000,
            include_pods=False,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_subscription_nonexistent(self, manager):
        """Test updating subscription for nonexistent client."""
        result = await manager.update_subscription("nonexistent", systems=[30000142])
        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_client(self, manager, mock_websocket):
        """Test sending message to specific client."""
        await manager.connect("client1", mock_websocket)

        result = await manager.send_to_client("client1", {"type": "test"})
        assert result is True
        mock_websocket.send_json.assert_called_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_client(self, manager):
        """Test sending to nonexistent client."""
        result = await manager.send_to_client("nonexistent", {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast(self, manager):
        """Test broadcasting to all clients."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await manager.connect("client1", ws1)
        await manager.connect("client2", ws2)

        sent_count = await manager.broadcast({"type": "broadcast"})
        assert sent_count == 2
        ws1.send_json.assert_called_with({"type": "broadcast"})
        ws2.send_json.assert_called_with({"type": "broadcast"})

    @pytest.mark.asyncio
    async def test_broadcast_kill_no_filters(self, manager, mock_websocket, sample_kill_data):
        """Test broadcasting kill with no filters (should match)."""
        await manager.connect("client1", mock_websocket)

        sent_count = await manager.broadcast_kill(sample_kill_data)
        assert sent_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_kill_system_filter_match(
        self, manager, mock_websocket, sample_kill_data
    ):
        """Test broadcasting kill that matches system filter."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", systems=[30000142])  # Jita

        sent_count = await manager.broadcast_kill(sample_kill_data)
        assert sent_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_kill_system_filter_no_match(
        self, manager, mock_websocket, sample_kill_data
    ):
        """Test broadcasting kill that doesn't match system filter."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", systems=[30002187])  # Amarr

        sent_count = await manager.broadcast_kill(sample_kill_data)
        assert sent_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_kill_pod_filter(self, manager, mock_websocket, sample_pod_kill_data):
        """Test pod filter excludes pod kills when disabled."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", include_pods=False)

        sent_count = await manager.broadcast_kill(sample_pod_kill_data)
        assert sent_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_kill_value_filter(self, manager, mock_websocket, sample_kill_data):
        """Test minimum value filter."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", min_value=1000000000)  # 1B ISK

        sent_count = await manager.broadcast_kill(sample_kill_data)
        assert sent_count == 0  # Kill is only 500M

    @pytest.mark.asyncio
    async def test_get_stats(self, manager, mock_websocket):
        """Test connection statistics."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", systems=[30000142, 30000144])

        stats = manager.get_stats()
        assert stats["active_connections"] == 1
        assert len(stats["clients"]) == 1
        assert stats["clients"][0]["systems_filter_count"] == 2

    @pytest.mark.asyncio
    async def test_broadcast_kill_region_filter_match(
        self, manager, mock_websocket, sample_kill_data
    ):
        """Test broadcasting kill that matches region filter."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", regions=[10000002])  # The Forge

        sent_count = await manager.broadcast_kill(sample_kill_data)
        assert sent_count == 1

    @pytest.mark.asyncio
    async def test_broadcast_kill_region_filter_no_match(
        self, manager, mock_websocket, sample_kill_data
    ):
        """Test broadcasting kill that doesn't match region filter."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", regions=[10000043])  # Domain

        sent_count = await manager.broadcast_kill(sample_kill_data)
        assert sent_count == 0

    @pytest.mark.asyncio
    async def test_send_to_client_error_disconnects(self, manager, mock_websocket):
        """Test that send_to_client disconnects client on error."""
        await manager.connect("client1", mock_websocket)
        mock_websocket.send_json.side_effect = Exception("Connection closed")

        result = await manager.send_to_client("client1", {"type": "test"})

        assert result is False
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_error_disconnects_client(self, manager):
        """Test broadcast disconnects failing clients."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await manager.connect("client1", ws1)
        await manager.connect("client2", ws2)

        sent_count = await manager.broadcast({"type": "test"})

        assert sent_count == 1  # Only client1 succeeded
        assert manager.connection_count == 1  # client2 disconnected

    @pytest.mark.asyncio
    async def test_broadcast_kill_error_disconnects_client(self, manager, sample_kill_data):
        """Test broadcast_kill disconnects failing clients."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await manager.connect("client1", ws1)
        await manager.connect("client2", ws2)

        sent_count = await manager.broadcast_kill(sample_kill_data)

        assert sent_count == 1  # Only client1 succeeded
        assert manager.connection_count == 1  # client2 disconnected

    @pytest.mark.asyncio
    async def test_broadcast_kill_null_value(self, manager, mock_websocket):
        """Test broadcast_kill handles None total_value gracefully."""
        await manager.connect("client1", mock_websocket)
        await manager.update_subscription("client1", min_value=1000000)

        kill_data = {
            "solar_system_id": 30000142,
            "region_id": 10000002,
            "total_value": None,
        }
        sent_count = await manager.broadcast_kill(kill_data)
        assert sent_count == 0  # None treated as 0, below min_value
