"""Unit tests for jump fatigue calculator."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.jump_fatigue import (
    FatigueState,
    FatigueTracker,
    JumpFatigueResult,
    RouteFatigueResult,
    calculate_jump_timers,
    calculate_route_fatigue,
    calculate_single_jump_fatigue,
    format_timer,
    get_fatigue_tracker,
    reset_fatigue_tracker,
)


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset the global fatigue tracker before each test."""
    reset_fatigue_tracker()
    yield
    reset_fatigue_tracker()


@pytest.fixture
def mock_distance():
    """Mock calculate_distance_ly to return predictable values."""
    with patch("backend.app.services.jump_fatigue.calculate_distance_ly") as mock:
        # Default to 5 LY per jump
        mock.return_value = 5.0
        yield mock


class TestFatigueState:
    """Tests for FatigueState dataclass."""

    def test_default_state(self):
        """Test default state has zero timers."""
        state = FatigueState()
        assert state.blue_timer_seconds == 0.0
        assert state.red_timer_seconds == 0.0
        assert state.can_jump is True

    def test_state_with_timers(self):
        """Test state with active timers."""
        state = FatigueState(
            blue_timer_seconds=300.0,  # 5 minutes
            red_timer_seconds=1800.0,  # 30 minutes
        )
        assert state.blue_timer_seconds == 300.0
        assert state.red_timer_seconds == 1800.0
        assert state.can_jump is False

    def test_decay_to_now(self):
        """Test timer decay over time."""
        # Create state with 60 seconds of blue timer, 30 seconds ago
        past = datetime.now(UTC) - timedelta(seconds=30)
        state = FatigueState(
            blue_timer_seconds=60.0,
            red_timer_seconds=600.0,
            last_updated=past,
        )

        decayed = state.decay_to_now()

        # Should have ~30 seconds of blue remaining
        assert 25 <= decayed.blue_timer_seconds <= 35
        # Red should also decay
        assert 565 <= decayed.red_timer_seconds <= 575

    def test_decay_clamps_to_zero(self):
        """Test that decay doesn't go negative."""
        past = datetime.now(UTC) - timedelta(seconds=120)
        state = FatigueState(
            blue_timer_seconds=60.0,
            red_timer_seconds=60.0,
            last_updated=past,
        )

        decayed = state.decay_to_now()

        assert decayed.blue_timer_seconds == 0.0
        assert decayed.red_timer_seconds == 0.0

    def test_can_jump_property(self):
        """Test can_jump reflects blue timer state."""
        state = FatigueState(blue_timer_seconds=0.0)
        assert state.can_jump is True

        state = FatigueState(blue_timer_seconds=60.0)
        assert state.can_jump is False

    def test_time_until_jump(self):
        """Test time_until_jump property."""
        state = FatigueState(blue_timer_seconds=120.0)
        # Approximately 120 seconds (may be slightly less due to time)
        assert 115 <= state.time_until_jump <= 125

    def test_time_until_clear(self):
        """Test time_until_clear returns max of timers."""
        state = FatigueState(
            blue_timer_seconds=60.0,
            red_timer_seconds=300.0,
        )
        # Red timer is larger, so time_until_clear should be ~300
        assert 295 <= state.time_until_clear <= 305


class TestCalculateJumpTimers:
    """Tests for calculate_jump_timers function."""

    def test_basic_jump(self):
        """Test basic jump with no existing fatigue."""
        blue_added, red_added, new_blue, new_red = calculate_jump_timers(5.0)

        # 5 LY = 5 minutes base blue timer = 300 seconds
        assert blue_added == 300.0
        # Red should be blue * 10 = 3000 seconds
        assert 2900 <= new_red <= 3100

    def test_min_blue_timer(self):
        """Test minimum blue timer of 1 minute."""
        blue_added, red_added, new_blue, new_red = calculate_jump_timers(0.5)

        # Should be at least 60 seconds (1 minute minimum)
        assert blue_added >= 60.0

    def test_fatigue_multiplier(self):
        """Test fatigue multiplier from existing red timer."""
        # With 600 seconds of red timer, multiplier = 1.0
        blue_added, red_added, new_blue, new_red = calculate_jump_timers(
            5.0,
            current_red_seconds=600.0,
        )

        # Blue should be 300 * (1 + 1) = 600 seconds
        assert 590 <= blue_added <= 610

    def test_max_red_timer(self):
        """Test red timer caps at 4 hours."""
        # Jump with already high red timer
        blue_added, red_added, new_blue, new_red = calculate_jump_timers(
            10.0,
            current_red_seconds=14000.0,  # Already near max
        )

        # Red timer should cap at 4 hours = 14400 seconds
        assert new_red <= 14400.0


class TestCalculateSingleJumpFatigue:
    """Tests for calculate_single_jump_fatigue function."""

    def test_fresh_jump(self, mock_distance):
        """Test jump with no existing fatigue."""
        mock_distance.return_value = 5.0

        result = calculate_single_jump_fatigue("SystemA", "SystemB")

        assert isinstance(result, JumpFatigueResult)
        assert result.from_system == "SystemA"
        assert result.to_system == "SystemB"
        assert result.distance_ly == 5.0
        assert result.blue_timer_before == 0.0
        assert result.wait_time_seconds == 0.0

    def test_jump_with_existing_fatigue(self, mock_distance):
        """Test jump with existing fatigue state."""
        mock_distance.return_value = 5.0

        state = FatigueState(
            blue_timer_seconds=60.0,
            red_timer_seconds=600.0,
        )

        result = calculate_single_jump_fatigue("SystemA", "SystemB", state)

        # Should have wait time equal to blue timer
        assert result.wait_time_seconds >= 55.0

    def test_fatigue_multiplier_in_result(self, mock_distance):
        """Test fatigue multiplier is included in result."""
        mock_distance.return_value = 5.0

        state = FatigueState(
            blue_timer_seconds=0.0,
            red_timer_seconds=600.0,
        )

        result = calculate_single_jump_fatigue("SystemA", "SystemB", state)

        # Multiplier should be ~1.0 (600/600)
        assert 0.9 <= result.fatigue_multiplier <= 1.1


class TestCalculateRouteFatigue:
    """Tests for calculate_route_fatigue function."""

    def test_two_jump_route(self, mock_distance):
        """Test route with two jumps."""
        mock_distance.return_value = 5.0

        result = calculate_route_fatigue(["A", "B", "C"])

        assert isinstance(result, RouteFatigueResult)
        assert result.total_jumps == 2
        assert result.total_distance_ly == 10.0
        assert len(result.legs) == 2

    def test_requires_two_waypoints(self, mock_distance):
        """Test that route requires at least 2 waypoints."""
        with pytest.raises(ValueError, match="at least 2 waypoints"):
            calculate_route_fatigue(["A"])

    def test_accumulates_fatigue(self, mock_distance):
        """Test that fatigue accumulates across jumps."""
        mock_distance.return_value = 5.0

        result = calculate_route_fatigue(["A", "B", "C", "D"])

        # Final red timer should be higher than first leg's red timer
        first_leg_red = result.legs[0].red_timer_after
        final_red = result.final_red_timer
        assert final_red > first_leg_red

    def test_wait_time_accumulates(self, mock_distance):
        """Test that wait time accumulates with wait_between_jumps=True."""
        mock_distance.return_value = 5.0

        result = calculate_route_fatigue(
            ["A", "B", "C", "D"],
            wait_between_jumps=True,
        )

        # Should have wait times after first jump
        assert result.total_wait_time_seconds > 0

    def test_no_wait_option(self, mock_distance):
        """Test wait_between_jumps=False option."""
        mock_distance.return_value = 5.0

        result = calculate_route_fatigue(
            ["A", "B", "C"],
            wait_between_jumps=False,
        )

        # Wait times should all be 0
        for leg in result.legs:
            assert leg.wait_time_seconds == 0.0


class TestFormatTimer:
    """Tests for format_timer function."""

    def test_zero(self):
        """Test formatting zero."""
        assert format_timer(0) == "0:00"

    def test_seconds_only(self):
        """Test formatting seconds."""
        assert format_timer(45) == "0:45"

    def test_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_timer(185) == "3:05"

    def test_hours_minutes_seconds(self):
        """Test formatting with hours."""
        assert format_timer(3661) == "1:01:01"

    def test_negative(self):
        """Test formatting negative (should return 0:00)."""
        assert format_timer(-10) == "0:00"


class TestFatigueTracker:
    """Tests for FatigueTracker class."""

    def test_get_default_state(self):
        """Test getting state for unknown character."""
        tracker = FatigueTracker()
        state = tracker.get_state(12345)

        assert state.character_id == 12345
        assert state.blue_timer_seconds == 0.0
        assert state.red_timer_seconds == 0.0

    def test_set_and_get_state(self):
        """Test setting and retrieving state."""
        tracker = FatigueTracker()
        tracker.set_state(
            character_id=12345,
            blue_timer_seconds=300.0,
            red_timer_seconds=1800.0,
            character_name="Test Pilot",
        )

        state = tracker.get_state(12345)

        assert state.character_name == "Test Pilot"
        # Timers should be approximately correct (with decay)
        assert 290 <= state.blue_timer_seconds <= 310
        assert 1790 <= state.red_timer_seconds <= 1810

    def test_record_jump(self, mock_distance):
        """Test recording a jump updates state."""
        mock_distance.return_value = 5.0

        tracker = FatigueTracker()
        # Set initial state with zero fatigue
        tracker.set_state(12345, 0.0, 0.0)

        state = tracker.record_jump(12345, "SystemA", "SystemB")

        # Should now have blue and red timers
        assert state.blue_timer_seconds > 0
        assert state.red_timer_seconds > 0

    def test_clear_state(self):
        """Test clearing state."""
        tracker = FatigueTracker()
        tracker.set_state(12345, 300.0, 1800.0)
        tracker.clear_state(12345)

        state = tracker.get_state(12345)

        assert state.blue_timer_seconds == 0.0
        assert state.red_timer_seconds == 0.0

    def test_subscribe_callback(self):
        """Test subscription callbacks."""
        tracker = FatigueTracker()
        callback_data = []

        def callback(char_id, state):
            callback_data.append((char_id, state))

        tracker.subscribe(callback)
        tracker.set_state(12345, 300.0, 1800.0)

        assert len(callback_data) == 1
        assert callback_data[0][0] == 12345

    def test_unsubscribe_callback(self):
        """Test unsubscription."""
        tracker = FatigueTracker()
        callback_data = []

        def callback(char_id, state):
            callback_data.append((char_id, state))

        tracker.subscribe(callback)
        tracker.unsubscribe(callback)
        tracker.set_state(12345, 300.0, 1800.0)

        assert len(callback_data) == 0


class TestGetFatigueTracker:
    """Tests for get_fatigue_tracker singleton."""

    def test_returns_same_instance(self):
        """Test singleton returns same instance."""
        tracker1 = get_fatigue_tracker()
        tracker2 = get_fatigue_tracker()
        assert tracker1 is tracker2

    def test_reset_creates_new_instance(self):
        """Test reset creates new instance."""
        tracker1 = get_fatigue_tracker()
        reset_fatigue_tracker()
        tracker2 = get_fatigue_tracker()
        assert tracker1 is not tracker2
