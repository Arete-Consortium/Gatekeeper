"""Jump fatigue calculator for capital ships.

Implements EVE Online's jump fatigue mechanics:
- Blue Timer (Jump Activation Timer): Prevents jump activation
- Red Timer (Jump Fatigue): Increases blue timer for future jumps
- Both timers decay in real-time when not jumping
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import RLock

from .jump_drive import calculate_distance_ly


@dataclass
class FatigueState:
    """Current fatigue state for a character."""

    character_id: int | None = None
    character_name: str | None = None

    # Blue timer (jump activation timer) in seconds
    blue_timer_seconds: float = 0.0
    blue_timer_expires: datetime | None = None

    # Red timer (jump fatigue) in seconds
    red_timer_seconds: float = 0.0
    red_timer_expires: datetime | None = None

    # Last update timestamp
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))

    def decay_to_now(self) -> "FatigueState":
        """Return a new state with timers decayed to current time."""
        now = datetime.now(UTC)
        elapsed = (now - self.last_updated).total_seconds()

        new_blue = max(0.0, self.blue_timer_seconds - elapsed)
        new_red = max(0.0, self.red_timer_seconds - elapsed)

        # Update expiry times
        blue_expires = None
        red_expires = None
        if new_blue > 0:
            blue_expires = now + timedelta(seconds=new_blue)
        if new_red > 0:
            red_expires = now + timedelta(seconds=new_red)

        return FatigueState(
            character_id=self.character_id,
            character_name=self.character_name,
            blue_timer_seconds=new_blue,
            blue_timer_expires=blue_expires,
            red_timer_seconds=new_red,
            red_timer_expires=red_expires,
            last_updated=now,
        )

    @property
    def can_jump(self) -> bool:
        """Check if character can jump (blue timer expired)."""
        decayed = self.decay_to_now()
        return decayed.blue_timer_seconds <= 0

    @property
    def time_until_jump(self) -> float:
        """Get seconds until next jump is available."""
        decayed = self.decay_to_now()
        return max(0.0, decayed.blue_timer_seconds)

    @property
    def time_until_clear(self) -> float:
        """Get seconds until all fatigue clears."""
        decayed = self.decay_to_now()
        return max(decayed.blue_timer_seconds, decayed.red_timer_seconds)


@dataclass
class JumpFatigueResult:
    """Result of a fatigue calculation for a jump."""

    distance_ly: float
    from_system: str
    to_system: str

    # Before jump (decayed to jump time)
    blue_timer_before: float
    red_timer_before: float

    # Timer values added by this jump
    blue_timer_added: float
    red_timer_added: float

    # After jump
    blue_timer_after: float
    red_timer_after: float

    # Useful info
    wait_time_seconds: float  # Time until this jump can be made
    fatigue_multiplier: float  # Current fatigue multiplier


@dataclass
class RouteFatigueResult:
    """Fatigue calculation for an entire route."""

    from_system: str
    to_system: str
    total_jumps: int
    total_distance_ly: float

    # Total timers at end of route
    final_blue_timer: float
    final_red_timer: float

    # Total wait time (sum of all waits)
    total_wait_time_seconds: float

    # Time until route is complete (jumps + waits)
    total_time_seconds: float

    # Per-leg breakdown
    legs: list[JumpFatigueResult]

    # Optimal wait between legs (if waiting for fatigue to decay)
    recommended_wait_before_start: float = 0.0


# Constants for fatigue calculation
MIN_BLUE_TIMER_SECONDS = 60.0  # 1 minute minimum blue timer
BLUE_TIMER_PER_LY = 60.0  # 1 minute per LY
MAX_RED_TIMER_SECONDS = 4 * 60 * 60  # 4 hours max red timer
FATIGUE_MULTIPLIER_DIVISOR = 600.0  # Red timer / 600 gives multiplier


def calculate_jump_timers(
    distance_ly: float,
    current_blue_seconds: float = 0.0,
    current_red_seconds: float = 0.0,
) -> tuple[float, float, float, float]:
    """
    Calculate jump fatigue timers for a single jump.

    EVE Fatigue Formula:
    - Base Blue Timer = max(1 minute, LY × 1 minute)
    - Fatigue Multiplier = Red Timer / 600 seconds
    - Actual Blue Timer = Base Blue × (1 + Multiplier)
    - New Red Timer = (Old Red + Actual Blue) × 10

    Args:
        distance_ly: Jump distance in light years
        current_blue_seconds: Current blue timer in seconds
        current_red_seconds: Current red timer in seconds

    Returns:
        Tuple of (blue_added, red_added, new_blue_total, new_red_total)
    """
    # Base blue timer from distance
    base_blue = max(MIN_BLUE_TIMER_SECONDS, distance_ly * BLUE_TIMER_PER_LY)

    # Fatigue multiplier from current red timer
    multiplier = current_red_seconds / FATIGUE_MULTIPLIER_DIVISOR

    # Actual blue timer with fatigue
    blue_added = base_blue * (1 + multiplier)

    # Red timer accumulation: (current_red + blue_added) multiplied
    # Simplified: new_red = min(current_red * multiplier_factor + blue_added * 10, max)
    new_red_raw = current_red_seconds + (blue_added * 10)
    new_red = min(new_red_raw, MAX_RED_TIMER_SECONDS)

    red_added = new_red - current_red_seconds

    return (blue_added, red_added, blue_added, new_red)


def calculate_single_jump_fatigue(
    from_system: str,
    to_system: str,
    current_state: FatigueState | None = None,
) -> JumpFatigueResult:
    """
    Calculate fatigue for a single jump.

    Args:
        from_system: Origin system name
        to_system: Destination system name
        current_state: Current fatigue state (optional)

    Returns:
        JumpFatigueResult with full breakdown
    """
    distance = calculate_distance_ly(from_system, to_system)

    # Get current timer values
    if current_state:
        decayed = current_state.decay_to_now()
        blue_before = decayed.blue_timer_seconds
        red_before = decayed.red_timer_seconds
    else:
        blue_before = 0.0
        red_before = 0.0

    # Calculate wait time (must wait for blue timer to expire)
    wait_time = max(0.0, blue_before)

    # Calculate timers for jump (after waiting)
    blue_added, red_added, blue_after, red_after = calculate_jump_timers(
        distance,
        current_blue_seconds=0.0,  # Blue is 0 after waiting
        current_red_seconds=max(0.0, red_before - wait_time),  # Red decays during wait
    )

    multiplier = (red_before - wait_time) / FATIGUE_MULTIPLIER_DIVISOR if red_before > wait_time else 0.0

    return JumpFatigueResult(
        distance_ly=round(distance, 2),
        from_system=from_system,
        to_system=to_system,
        blue_timer_before=round(blue_before, 1),
        red_timer_before=round(red_before, 1),
        blue_timer_added=round(blue_added, 1),
        red_timer_added=round(red_added, 1),
        blue_timer_after=round(blue_after, 1),
        red_timer_after=round(red_after, 1),
        wait_time_seconds=round(wait_time, 1),
        fatigue_multiplier=round(max(0.0, multiplier), 3),
    )


def calculate_route_fatigue(
    waypoints: list[str],
    current_state: FatigueState | None = None,
    wait_between_jumps: bool = True,
) -> RouteFatigueResult:
    """
    Calculate fatigue for a multi-jump route.

    Args:
        waypoints: List of system names in order
        current_state: Current fatigue state (optional)
        wait_between_jumps: If True, assume waiting for blue timer between jumps

    Returns:
        RouteFatigueResult with complete breakdown
    """
    if len(waypoints) < 2:
        raise ValueError("Route must have at least 2 waypoints")

    legs: list[JumpFatigueResult] = []
    total_distance = 0.0
    total_wait = 0.0

    # Start with current state
    if current_state:
        decayed = current_state.decay_to_now()
        current_blue = decayed.blue_timer_seconds
        current_red = decayed.red_timer_seconds
    else:
        current_blue = 0.0
        current_red = 0.0

    for i in range(len(waypoints) - 1):
        from_sys = waypoints[i]
        to_sys = waypoints[i + 1]

        distance = calculate_distance_ly(from_sys, to_sys)
        total_distance += distance

        # Wait for blue timer if needed
        if wait_between_jumps:
            wait_time = max(0.0, current_blue)
            total_wait += wait_time
            # Decay red timer during wait
            current_red = max(0.0, current_red - wait_time)
            current_blue = 0.0
        else:
            wait_time = 0.0

        # Calculate jump
        blue_added, red_added, new_blue, new_red = calculate_jump_timers(
            distance,
            current_blue_seconds=current_blue,
            current_red_seconds=current_red,
        )

        multiplier = current_red / FATIGUE_MULTIPLIER_DIVISOR

        legs.append(
            JumpFatigueResult(
                distance_ly=round(distance, 2),
                from_system=from_sys,
                to_system=to_sys,
                blue_timer_before=round(current_blue, 1),
                red_timer_before=round(current_red, 1),
                blue_timer_added=round(blue_added, 1),
                red_timer_added=round(red_added, 1),
                blue_timer_after=round(new_blue, 1),
                red_timer_after=round(new_red, 1),
                wait_time_seconds=round(wait_time, 1),
                fatigue_multiplier=round(multiplier, 3),
            )
        )

        current_blue = new_blue
        current_red = new_red

    return RouteFatigueResult(
        from_system=waypoints[0],
        to_system=waypoints[-1],
        total_jumps=len(legs),
        total_distance_ly=round(total_distance, 2),
        final_blue_timer=round(current_blue, 1),
        final_red_timer=round(current_red, 1),
        total_wait_time_seconds=round(total_wait, 1),
        total_time_seconds=round(total_wait + current_blue, 1),
        legs=legs,
    )


def format_timer(seconds: float) -> str:
    """Format seconds as human-readable timer string."""
    if seconds <= 0:
        return "0:00"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


# =============================================================================
# Character Fatigue Tracking
# =============================================================================


class FatigueTracker:
    """Track fatigue state for multiple characters."""

    def __init__(self):
        self._states: dict[int, FatigueState] = {}
        self._lock = RLock()
        self._subscribers: list[Callable[[int, FatigueState], None]] = []

    def get_state(self, character_id: int) -> FatigueState:
        """Get current fatigue state for a character."""
        with self._lock:
            if character_id not in self._states:
                return FatigueState(character_id=character_id)
            return self._states[character_id].decay_to_now()

    def set_state(
        self,
        character_id: int,
        blue_timer_seconds: float,
        red_timer_seconds: float,
        character_name: str | None = None,
    ) -> FatigueState:
        """Set fatigue state for a character (e.g., from ESI data)."""
        now = datetime.now(UTC)

        blue_expires = now + timedelta(seconds=blue_timer_seconds) if blue_timer_seconds > 0 else None
        red_expires = now + timedelta(seconds=red_timer_seconds) if red_timer_seconds > 0 else None

        state = FatigueState(
            character_id=character_id,
            character_name=character_name,
            blue_timer_seconds=blue_timer_seconds,
            blue_timer_expires=blue_expires,
            red_timer_seconds=red_timer_seconds,
            red_timer_expires=red_expires,
            last_updated=now,
        )

        with self._lock:
            self._states[character_id] = state

        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(character_id, state)
            except Exception:
                pass

        return state

    def record_jump(
        self,
        character_id: int,
        from_system: str,
        to_system: str,
    ) -> FatigueState:
        """Record a jump and update fatigue state."""
        current = self.get_state(character_id)
        result = calculate_single_jump_fatigue(from_system, to_system, current)

        return self.set_state(
            character_id,
            blue_timer_seconds=result.blue_timer_after,
            red_timer_seconds=result.red_timer_after,
            character_name=current.character_name,
        )

    def clear_state(self, character_id: int) -> None:
        """Clear fatigue state for a character."""
        with self._lock:
            if character_id in self._states:
                del self._states[character_id]

    def subscribe(self, callback: Callable[[int, FatigueState], None]) -> None:
        """Subscribe to fatigue state changes."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[int, FatigueState], None]) -> None:
        """Unsubscribe from fatigue state changes."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)


# Global tracker instance
_fatigue_tracker: FatigueTracker | None = None


def get_fatigue_tracker() -> FatigueTracker:
    """Get the global fatigue tracker instance."""
    global _fatigue_tracker
    if _fatigue_tracker is None:
        _fatigue_tracker = FatigueTracker()
    return _fatigue_tracker


def reset_fatigue_tracker() -> None:
    """Reset the global fatigue tracker (for testing)."""
    global _fatigue_tracker
    _fatigue_tracker = None
