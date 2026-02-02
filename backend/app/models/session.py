"""Collaborative routing session models.

Enables real-time collaborative route planning where multiple users
can share routes, waypoints, and coordinate travel together.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionRole(str, Enum):
    """Role of a participant in a session."""

    OWNER = "owner"  # Created the session, full control
    EDITOR = "editor"  # Can modify routes/waypoints
    VIEWER = "viewer"  # Read-only access


class SessionState(str, Enum):
    """State of a collaborative session."""

    ACTIVE = "active"  # Session is live and accepting participants
    PAUSED = "paused"  # Session is paused (owner away)
    CLOSED = "closed"  # Session has ended


class SessionParticipant(BaseModel):
    """A participant in a routing session."""

    character_id: int
    character_name: str
    role: SessionRole = SessionRole.VIEWER
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    current_system: str | None = None  # Live location if sharing
    sharing_location: bool = False


class SessionWaypoint(BaseModel):
    """A waypoint in a shared route."""

    id: str  # UUID for ordering/deletion
    system_name: str
    added_by: int  # character_id
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str | None = None
    is_destination: bool = False  # Final destination marker


class SessionRoute(BaseModel):
    """A shared route in a session."""

    id: str  # UUID
    name: str = "Route"
    from_system: str
    to_system: str
    profile: str = "safer"
    waypoints: list[str] = Field(default_factory=list)  # System names
    avoid_systems: list[str] = Field(default_factory=list)
    use_bridges: bool = False
    use_wormholes: bool = False
    created_by: int  # character_id
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_jumps: int | None = None
    path: list[str] | None = None  # Computed path


class SessionMessage(BaseModel):
    """A chat message in a session."""

    id: str  # UUID
    character_id: int
    character_name: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_type: str = "chat"  # chat, system, waypoint, route


class RoutingSession(BaseModel):
    """A collaborative routing session."""

    id: str  # Short shareable code (e.g., "ABC123")
    name: str = "Routing Session"
    owner_id: int  # character_id of creator
    owner_name: str
    state: SessionState = SessionState.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None  # Auto-expire after inactivity

    # Participants
    participants: list[SessionParticipant] = Field(default_factory=list)
    max_participants: int = 10

    # Shared content
    routes: list[SessionRoute] = Field(default_factory=list)
    waypoints: list[SessionWaypoint] = Field(default_factory=list)
    messages: list[SessionMessage] = Field(default_factory=list)

    # Settings
    public: bool = False  # Anyone with link can join
    require_approval: bool = True  # Owner must approve new participants
    allow_chat: bool = True
    allow_location_sharing: bool = True


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    name: str = Field("Routing Session", max_length=100)
    public: bool = False
    require_approval: bool = True
    max_participants: int = Field(10, ge=2, le=50)
    expires_hours: int | None = Field(24, ge=1, le=168)  # Max 1 week


class CreateSessionResponse(BaseModel):
    """Response after creating a session."""

    session_id: str
    join_code: str
    join_url: str
    session: RoutingSession


class JoinSessionRequest(BaseModel):
    """Request to join a session."""

    session_id: str
    character_id: int
    character_name: str


class JoinSessionResponse(BaseModel):
    """Response after joining a session."""

    success: bool
    session: RoutingSession | None = None
    pending_approval: bool = False
    error: str | None = None


class SessionUpdate(BaseModel):
    """Partial update to a session."""

    name: str | None = None
    state: SessionState | None = None
    public: bool | None = None
    require_approval: bool | None = None
    allow_chat: bool | None = None


class AddWaypointRequest(BaseModel):
    """Request to add a waypoint."""

    system_name: str
    notes: str | None = None
    is_destination: bool = False


class AddRouteRequest(BaseModel):
    """Request to add a route to a session."""

    name: str = "Route"
    from_system: str
    to_system: str
    profile: str = "safer"
    avoid_systems: list[str] = Field(default_factory=list)
    use_bridges: bool = False
    use_wormholes: bool = False


class SendMessageRequest(BaseModel):
    """Request to send a chat message."""

    message: str = Field(..., max_length=500)


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[RoutingSession]
    total_count: int


class SessionEventType(str, Enum):
    """Types of events broadcast to session participants."""

    PARTICIPANT_JOINED = "participant_joined"
    PARTICIPANT_LEFT = "participant_left"
    PARTICIPANT_LOCATION = "participant_location"
    ROUTE_ADDED = "route_added"
    ROUTE_REMOVED = "route_removed"
    WAYPOINT_ADDED = "waypoint_added"
    WAYPOINT_REMOVED = "waypoint_removed"
    MESSAGE = "message"
    SESSION_UPDATE = "session_update"
    SESSION_CLOSED = "session_closed"


class SessionEvent(BaseModel):
    """An event in a session for WebSocket broadcast."""

    session_id: str
    event_type: SessionEventType
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
