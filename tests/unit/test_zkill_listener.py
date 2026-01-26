"""Unit tests for zKillboard listener."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.zkill_listener import ZKillListener


class TestZKillListenerInit:
    """Tests for ZKillListener initialization."""

    def test_default_queue_id(self):
        """Test default queue ID is set."""
        listener = ZKillListener()
        assert listener.queue_id == "eve-gatekeeper"

    def test_custom_queue_id(self):
        """Test custom queue ID."""
        listener = ZKillListener(queue_id="custom-queue")
        assert listener.queue_id == "custom-queue"

    def test_on_kill_callback(self):
        """Test on_kill callback is set."""
        callback = MagicMock()
        listener = ZKillListener(on_kill=callback)
        assert listener.on_kill is callback

    def test_initial_state(self):
        """Test initial state is not running."""
        listener = ZKillListener()
        assert listener.is_running is False
        assert listener._task is None
        assert listener._client is None


class TestZKillListenerLifecycle:
    """Tests for listener start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running(self):
        """Test that start sets running state."""
        listener = ZKillListener()

        # Mock the listen loop to avoid actual network calls
        with patch.object(listener, "_listen_loop", new_callable=AsyncMock):
            await listener.start()

            assert listener.is_running is True
            assert listener._client is not None
            assert listener._task is not None

            # Clean up
            await listener.stop()

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test that starting twice logs warning."""
        listener = ZKillListener()

        with patch.object(listener, "_listen_loop", new_callable=AsyncMock):
            await listener.start()

            # Start again should not create new task
            with patch("backend.app.services.zkill_listener.logger") as mock_logger:
                await listener.start()
                mock_logger.warning.assert_called()

            await listener.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_state(self):
        """Test that stop clears running state."""
        listener = ZKillListener()

        with patch.object(listener, "_listen_loop", new_callable=AsyncMock):
            await listener.start()
            await listener.stop()

            assert listener.is_running is False
            assert listener._task is None
            assert listener._client is None

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test stopping when not running is safe."""
        listener = ZKillListener()

        # Should not raise
        await listener.stop()

        assert listener.is_running is False


class TestZKillListenerReconnect:
    """Tests for reconnection logic."""

    def test_initial_reconnect_delay(self):
        """Test initial reconnect delay is 1 second."""
        listener = ZKillListener()
        assert listener._reconnect_delay == 1

    def test_max_reconnect_delay(self):
        """Test max reconnect delay is set."""
        listener = ZKillListener()
        assert listener._max_reconnect_delay == 60


class TestZKillListenerCallback:
    """Tests for kill callback handling."""

    @pytest.mark.asyncio
    async def test_callback_receives_kill_data(self):
        """Test that callback receives kill data."""
        received_kills = []

        def on_kill(kill_data):
            received_kills.append(kill_data)

        listener = ZKillListener(on_kill=on_kill)

        # Simulate calling the callback
        test_kill = {"killmail_id": 12345, "solar_system_id": 30000142}
        if listener.on_kill:
            listener.on_kill(test_kill)

        assert len(received_kills) == 1
        assert received_kills[0]["killmail_id"] == 12345

    def test_no_callback_does_not_crash(self):
        """Test that listener works without callback."""
        listener = ZKillListener()
        assert listener.on_kill is None
        # Should not crash if we check the callback
        if listener.on_kill:
            listener.on_kill({})


class TestHandleReconnect:
    """Tests for reconnection backoff logic."""

    @pytest.mark.asyncio
    async def test_reconnect_exponential_backoff(self):
        """Test that reconnect delay doubles each time."""
        listener = ZKillListener()
        listener._running = True

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # First reconnect: 1s delay, then doubles to 2
            await listener._handle_reconnect()
            mock_sleep.assert_called_with(1)
            assert listener._reconnect_delay == 2

            # Second reconnect: 2s delay, then doubles to 4
            await listener._handle_reconnect()
            mock_sleep.assert_called_with(2)
            assert listener._reconnect_delay == 4

            # Third reconnect: 4s delay, then doubles to 8
            await listener._handle_reconnect()
            mock_sleep.assert_called_with(4)
            assert listener._reconnect_delay == 8

    @pytest.mark.asyncio
    async def test_reconnect_max_delay(self):
        """Test that reconnect delay caps at max."""
        listener = ZKillListener()
        listener._running = True
        listener._reconnect_delay = 32

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await listener._handle_reconnect()
            assert listener._reconnect_delay == 60  # Max is 60

            # Should stay at max
            await listener._handle_reconnect()
            assert listener._reconnect_delay == 60

    @pytest.mark.asyncio
    async def test_reconnect_skipped_when_not_running(self):
        """Test that reconnect is skipped when listener is stopped."""
        listener = ZKillListener()
        listener._running = False

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await listener._handle_reconnect()
            mock_sleep.assert_not_called()


class TestFetchKills:
    """Tests for _fetch_kills method."""

    @pytest.mark.asyncio
    async def test_fetch_kills_no_client(self):
        """Test fetch_kills returns early if no client."""
        listener = ZKillListener()
        listener._client = None

        # Should not raise
        await listener._fetch_kills()

    @pytest.mark.asyncio
    async def test_fetch_kills_success_with_package(self):
        """Test fetching kills with valid package."""
        listener = ZKillListener()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "package": {
                "killmail": {
                    "killmail_id": 12345,
                    "solar_system_id": 30000142,
                    "killmail_time": "2024-01-01T12:00:00Z",
                    "victim": {"ship_type_id": 587},
                    "attackers": [{}],
                },
                "zkb": {"totalValue": 1000000, "points": 10},
            }
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        listener._client = mock_client

        with patch.object(listener, "_process_kill", new_callable=AsyncMock) as mock_process:
            await listener._fetch_kills()
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_kills_no_package(self):
        """Test fetching when no kills available."""
        listener = ZKillListener()

        mock_response = MagicMock()
        mock_response.json.return_value = {"package": None}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        listener._client = mock_client

        with patch.object(listener, "_process_kill", new_callable=AsyncMock) as mock_process:
            await listener._fetch_kills()
            mock_process.assert_not_called()


class TestProcessKill:
    """Tests for _process_kill method."""

    @pytest.fixture
    def sample_package(self):
        """Create a sample kill package."""
        return {
            "killmail": {
                "killmail_id": 98765,
                "solar_system_id": 30000142,
                "killmail_time": "2024-01-15T18:30:00Z",
                "victim": {
                    "ship_type_id": 587,  # Rifter
                    "corporation_id": 123456,
                    "alliance_id": 789012,
                },
                "attackers": [{"character_id": 111}, {"character_id": 222}],
            },
            "zkb": {
                "totalValue": 5000000,
                "points": 15,
                "npc": False,
                "solo": False,
            },
        }

    @pytest.fixture
    def pod_kill_package(self):
        """Create a pod kill package."""
        return {
            "killmail": {
                "killmail_id": 11111,
                "solar_system_id": 30000142,
                "killmail_time": "2024-01-15T18:30:00Z",
                "victim": {"ship_type_id": 670},  # Capsule
                "attackers": [{}],
            },
            "zkb": {"totalValue": 100000, "points": 1},
        }

    @pytest.mark.asyncio
    async def test_process_kill_extracts_data(self, sample_package):
        """Test that kill data is correctly extracted."""
        received_kills = []
        listener = ZKillListener(on_kill=lambda k: received_kills.append(k))

        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_system.region_id = 10000002
        mock_universe.systems = {"Jita": mock_system}

        with (
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch("backend.app.services.zkill_listener.compute_risk") as mock_risk,
            patch("backend.app.services.zkill_listener.connection_manager") as mock_cm,
        ):
            mock_risk.return_value = MagicMock(score=0.75)
            mock_cm.broadcast_kill = AsyncMock()

            await listener._process_kill(sample_package)

        assert len(received_kills) == 1
        kill = received_kills[0]
        assert kill["kill_id"] == 98765
        assert kill["solar_system_id"] == 30000142
        assert kill["solar_system_name"] == "Jita"
        assert kill["region_id"] == 10000002
        assert kill["ship_type_id"] == 587
        assert kill["is_pod"] is False
        assert kill["attacker_count"] == 2
        assert kill["total_value"] == 5000000
        assert kill["risk_score"] == 0.75

    @pytest.mark.asyncio
    async def test_process_kill_detects_pod(self, pod_kill_package):
        """Test that pod kills are detected."""
        received_kills = []
        listener = ZKillListener(on_kill=lambda k: received_kills.append(k))

        mock_universe = MagicMock()
        mock_universe.systems = {}

        with (
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch("backend.app.services.zkill_listener.connection_manager") as mock_cm,
        ):
            mock_cm.broadcast_kill = AsyncMock()
            await listener._process_kill(pod_kill_package)

        assert received_kills[0]["is_pod"] is True

    @pytest.mark.asyncio
    async def test_process_kill_unknown_system(self, sample_package):
        """Test processing kill in unknown system."""
        received_kills = []
        listener = ZKillListener(on_kill=lambda k: received_kills.append(k))

        mock_universe = MagicMock()
        mock_universe.systems = {}  # No systems

        with (
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch("backend.app.services.zkill_listener.connection_manager") as mock_cm,
        ):
            mock_cm.broadcast_kill = AsyncMock()
            await listener._process_kill(sample_package)

        kill = received_kills[0]
        assert kill["solar_system_name"] is None
        assert kill["region_id"] is None
        assert kill["risk_score"] == 0.0

    @pytest.mark.asyncio
    async def test_process_kill_risk_calculation_error(self, sample_package):
        """Test handling of risk calculation errors."""
        received_kills = []
        listener = ZKillListener(on_kill=lambda k: received_kills.append(k))

        mock_universe = MagicMock()
        mock_system = MagicMock()
        mock_system.id = 30000142
        mock_system.region_id = 10000002
        mock_universe.systems = {"Jita": mock_system}

        with (
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch(
                "backend.app.services.zkill_listener.compute_risk",
                side_effect=Exception("Risk error"),
            ),
            patch("backend.app.services.zkill_listener.connection_manager") as mock_cm,
        ):
            mock_cm.broadcast_kill = AsyncMock()
            await listener._process_kill(sample_package)

        # Should still process with 0 risk score
        assert received_kills[0]["risk_score"] == 0.0

    @pytest.mark.asyncio
    async def test_process_kill_broadcasts_to_websocket(self, sample_package):
        """Test that kills are broadcast to WebSocket clients."""
        listener = ZKillListener()

        mock_universe = MagicMock()
        mock_universe.systems = {}

        with (
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch("backend.app.services.zkill_listener.connection_manager") as mock_cm,
        ):
            mock_cm.broadcast_kill = AsyncMock()
            await listener._process_kill(sample_package)
            mock_cm.broadcast_kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_kill_handles_exception(self):
        """Test that exceptions in processing are caught."""
        listener = ZKillListener()

        # Invalid package that will cause an error
        bad_package = {"killmail": None}

        with (
            patch(
                "backend.app.services.data_loader.load_universe",
                side_effect=Exception("Load error"),
            ),
            patch("backend.app.services.zkill_listener.logger") as mock_logger,
        ):
            # Should not raise
            await listener._process_kill(bad_package)
            mock_logger.exception.assert_called()

    @pytest.mark.asyncio
    async def test_process_kill_no_callback(self, sample_package):
        """Test processing kill without callback."""
        listener = ZKillListener()  # No callback

        mock_universe = MagicMock()
        mock_universe.systems = {}

        with (
            patch(
                "backend.app.services.data_loader.load_universe",
                return_value=mock_universe,
            ),
            patch("backend.app.services.zkill_listener.connection_manager") as mock_cm,
        ):
            mock_cm.broadcast_kill = AsyncMock()
            # Should not raise even without callback
            await listener._process_kill(sample_package)


class TestListenLoop:
    """Tests for _listen_loop method."""

    @pytest.mark.asyncio
    async def test_listen_loop_resets_delay_on_success(self):
        """Test that reconnect delay resets after successful fetch."""
        listener = ZKillListener()
        listener._running = True
        listener._reconnect_delay = 32  # Set high

        call_count = 0

        async def fake_fetch():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                listener._running = False

        with patch.object(listener, "_fetch_kills", side_effect=fake_fetch):
            await listener._listen_loop()

        assert listener._reconnect_delay == 1  # Reset to 1

    @pytest.mark.asyncio
    async def test_listen_loop_handles_timeout(self):
        """Test that timeout exceptions are handled gracefully."""
        import httpx

        listener = ZKillListener()
        listener._running = True

        call_count = 0

        async def fake_fetch():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.TimeoutException("Timeout")
            listener._running = False

        with patch.object(listener, "_fetch_kills", side_effect=fake_fetch):
            await listener._listen_loop()

        # Should have been called twice (timeout then success)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_listen_loop_handles_http_error(self):
        """Test that HTTP errors trigger reconnect."""
        import httpx

        listener = ZKillListener()
        listener._running = True

        call_count = 0

        async def fake_fetch():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = MagicMock()
                response.status_code = 503
                raise httpx.HTTPStatusError("Error", request=MagicMock(), response=response)
            listener._running = False

        with (
            patch.object(listener, "_fetch_kills", side_effect=fake_fetch),
            patch.object(listener, "_handle_reconnect", new_callable=AsyncMock) as mock_reconnect,
        ):
            await listener._listen_loop()
            mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_loop_handles_generic_exception(self):
        """Test that generic exceptions trigger reconnect."""
        listener = ZKillListener()
        listener._running = True

        call_count = 0

        async def fake_fetch():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Something went wrong")
            listener._running = False

        with (
            patch.object(listener, "_fetch_kills", side_effect=fake_fetch),
            patch.object(listener, "_handle_reconnect", new_callable=AsyncMock) as mock_reconnect,
        ):
            await listener._listen_loop()
            mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_loop_exits_on_cancel(self):
        """Test that CancelledError exits the loop."""
        listener = ZKillListener()
        listener._running = True

        async def fake_fetch():
            raise asyncio.CancelledError()

        with patch.object(listener, "_fetch_kills", side_effect=fake_fetch):
            # Should exit cleanly without raising
            await listener._listen_loop()


class TestGetZKillListener:
    """Tests for global listener getter."""

    def test_get_zkill_listener_creates_instance(self):
        """Test that get_zkill_listener creates instance."""
        from backend.app.services import zkill_listener

        # Reset global
        zkill_listener._zkill_listener = None

        listener = zkill_listener.get_zkill_listener()
        assert listener is not None
        assert isinstance(listener, ZKillListener)

    def test_get_zkill_listener_returns_same_instance(self):
        """Test that get_zkill_listener returns same instance."""
        from backend.app.services import zkill_listener

        # Reset global
        zkill_listener._zkill_listener = None

        listener1 = zkill_listener.get_zkill_listener()
        listener2 = zkill_listener.get_zkill_listener()
        assert listener1 is listener2
