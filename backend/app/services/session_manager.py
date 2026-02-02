"""Collaborative routing session service.

Manages routing sessions for real-time collaborative route planning.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from ..models.session import (
    AddRouteRequest,
    AddWaypointRequest,
    CreateSessionRequest,
    RoutingSession,
    SessionEvent,
    SessionEventType,
    SessionMessage,
    SessionParticipant,
    SessionRole,
    SessionRoute,
    SessionState,
    SessionUpdate,
    SessionWaypoint,
)

logger = logging.getLogger(__name__)

# Session expiry settings
DEFAULT_SESSION_EXPIRY_HOURS = 24
MAX_SESSION_EXPIRY_HOURS = 168  # 1 week
SESSION_CLEANUP_INTERVAL_MINUTES = 15
MAX_MESSAGES_PER_SESSION = 100


def _generate_session_id() -> str:
    """Generate a short, URL-safe session ID."""
    # 6 character alphanumeric code
    return secrets.token_urlsafe(4)[:6].upper()


def _generate_uuid() -> str:
    """Generate a UUID for items."""
    return str(uuid.uuid4())


class SessionManager:
    """Manages collaborative routing sessions.

    Features:
    - Create/join/leave sessions
    - Add/remove routes and waypoints
    - Real-time participant location sharing
    - Session chat
    - Auto-expiry of inactive sessions
    """

    def __init__(self):
        self._sessions: dict[str, RoutingSession] = {}
        # Track WebSocket connections per session
        self._session_connections: dict[str, set[str]] = {}  # session_id -> client_ids
        # Event callbacks for WebSocket broadcast
        self._event_callbacks: list[Any] = []

    def register_event_callback(self, callback: Any) -> None:
        """Register a callback for session events (for WebSocket broadcast)."""
        self._event_callbacks.append(callback)

    async def _broadcast_event(self, event: SessionEvent) -> None:
        """Broadcast an event to all registered callbacks."""
        for callback in self._event_callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.warning(f"Error broadcasting event: {e}")

    def create_session(
        self,
        request: CreateSessionRequest,
        owner_id: int,
        owner_name: str,
    ) -> RoutingSession:
        """Create a new routing session.

        Args:
            request: Session creation parameters
            owner_id: Character ID of the creator
            owner_name: Character name of the creator

        Returns:
            Created session
        """
        session_id = _generate_session_id()

        # Ensure unique ID
        while session_id in self._sessions:
            session_id = _generate_session_id()

        # Calculate expiry
        expires_at = None
        if request.expires_hours:
            expires_at = datetime.now(UTC) + timedelta(hours=request.expires_hours)

        session = RoutingSession(
            id=session_id,
            name=request.name,
            owner_id=owner_id,
            owner_name=owner_name,
            public=request.public,
            require_approval=request.require_approval,
            max_participants=request.max_participants,
            expires_at=expires_at,
            participants=[
                SessionParticipant(
                    character_id=owner_id,
                    character_name=owner_name,
                    role=SessionRole.OWNER,
                )
            ],
        )

        self._sessions[session_id] = session
        self._session_connections[session_id] = set()

        logger.info(
            "Session created",
            extra={
                "session_id": session_id,
                "owner_id": owner_id,
                "owner_name": owner_name,
            },
        )

        return session

    def get_session(self, session_id: str) -> RoutingSession | None:
        """Get a session by ID."""
        session = self._sessions.get(session_id.upper())
        if session and session.state != SessionState.CLOSED:
            return session
        return None

    def list_public_sessions(self) -> list[RoutingSession]:
        """List all public active sessions."""
        self._cleanup_expired()
        return [s for s in self._sessions.values() if s.public and s.state == SessionState.ACTIVE]

    def list_user_sessions(self, character_id: int) -> list[RoutingSession]:
        """List sessions a user is participating in."""
        self._cleanup_expired()
        result = []
        for session in self._sessions.values():
            if session.state == SessionState.CLOSED:
                continue
            for participant in session.participants:
                if participant.character_id == character_id:
                    result.append(session)
                    break
        return result

    async def join_session(
        self,
        session_id: str,
        character_id: int,
        character_name: str,
    ) -> tuple[RoutingSession | None, bool, str | None]:
        """Join a session.

        Args:
            session_id: Session to join
            character_id: Joining character
            character_name: Character name

        Returns:
            Tuple of (session if joined, pending_approval, error)
        """
        session = self.get_session(session_id)
        if not session:
            return None, False, "Session not found"

        if session.state != SessionState.ACTIVE:
            return None, False, "Session is not active"

        # Check if already a participant
        for p in session.participants:
            if p.character_id == character_id:
                return session, False, None  # Already in session

        # Check capacity
        if len(session.participants) >= session.max_participants:
            return None, False, "Session is full"

        # Add participant
        participant = SessionParticipant(
            character_id=character_id,
            character_name=character_name,
            role=SessionRole.VIEWER,
        )

        if session.require_approval and not session.public:
            # Would need approval system - for now just add them
            pass

        session.participants.append(participant)
        session.updated_at = datetime.now(UTC)

        # Broadcast event
        await self._broadcast_event(
            SessionEvent(
                session_id=session_id,
                event_type=SessionEventType.PARTICIPANT_JOINED,
                data={
                    "character_id": character_id,
                    "character_name": character_name,
                    "role": participant.role.value,
                },
            )
        )

        logger.info(
            "Participant joined session",
            extra={
                "session_id": session_id,
                "character_id": character_id,
                "character_name": character_name,
            },
        )

        return session, False, None

    async def leave_session(
        self,
        session_id: str,
        character_id: int,
    ) -> bool:
        """Leave a session.

        Args:
            session_id: Session to leave
            character_id: Leaving character

        Returns:
            True if left successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Find and remove participant
        for i, p in enumerate(session.participants):
            if p.character_id == character_id:
                removed = session.participants.pop(i)

                # If owner leaves, close session or transfer ownership
                if removed.role == SessionRole.OWNER:
                    if session.participants:
                        # Transfer to first remaining participant
                        session.participants[0].role = SessionRole.OWNER
                    else:
                        # No one left, close session
                        session.state = SessionState.CLOSED

                session.updated_at = datetime.now(UTC)

                # Broadcast event
                await self._broadcast_event(
                    SessionEvent(
                        session_id=session_id,
                        event_type=SessionEventType.PARTICIPANT_LEFT,
                        data={
                            "character_id": character_id,
                        },
                    )
                )

                logger.info(
                    "Participant left session",
                    extra={"session_id": session_id, "character_id": character_id},
                )
                return True

        return False

    async def update_session(
        self,
        session_id: str,
        character_id: int,
        update: SessionUpdate,
    ) -> RoutingSession | None:
        """Update session settings (owner only).

        Args:
            session_id: Session to update
            character_id: Character making the update
            update: Updates to apply

        Returns:
            Updated session or None if not authorized
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Check if owner
        if session.owner_id != character_id:
            return None

        if update.name is not None:
            session.name = update.name
        if update.state is not None:
            session.state = update.state
        if update.public is not None:
            session.public = update.public
        if update.require_approval is not None:
            session.require_approval = update.require_approval
        if update.allow_chat is not None:
            session.allow_chat = update.allow_chat

        session.updated_at = datetime.now(UTC)

        # Broadcast update
        await self._broadcast_event(
            SessionEvent(
                session_id=session_id,
                event_type=SessionEventType.SESSION_UPDATE,
                data={"update": update.model_dump(exclude_none=True)},
            )
        )

        return session

    async def close_session(
        self,
        session_id: str,
        character_id: int,
    ) -> bool:
        """Close a session (owner only).

        Args:
            session_id: Session to close
            character_id: Character closing (must be owner)

        Returns:
            True if closed
        """
        session = self.get_session(session_id)
        if not session:
            return False

        if session.owner_id != character_id:
            return False

        session.state = SessionState.CLOSED
        session.updated_at = datetime.now(UTC)

        # Broadcast closure
        await self._broadcast_event(
            SessionEvent(
                session_id=session_id,
                event_type=SessionEventType.SESSION_CLOSED,
                data={},
            )
        )

        logger.info("Session closed", extra={"session_id": session_id})
        return True

    # =========================================================================
    # Route Management
    # =========================================================================

    async def add_route(
        self,
        session_id: str,
        character_id: int,
        request: AddRouteRequest,
    ) -> SessionRoute | None:
        """Add a route to a session.

        Args:
            session_id: Session to add route to
            character_id: Character adding the route
            request: Route details

        Returns:
            Added route or None if not authorized
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Check if participant
        participant = None
        for p in session.participants:
            if p.character_id == character_id:
                participant = p
                break

        if not participant:
            return None

        # Check role (owner or editor can add routes)
        if participant.role == SessionRole.VIEWER:
            return None

        # Compute route
        from .routing import compute_route

        try:
            computed = compute_route(
                request.from_system,
                request.to_system,
                request.profile,
                avoid=set(request.avoid_systems),
                use_bridges=request.use_bridges,
                use_wormholes=request.use_wormholes,
            )
            path = [h.system_name for h in computed.path]
            total_jumps = computed.total_jumps
        except ValueError:
            path = None
            total_jumps = None

        route = SessionRoute(
            id=_generate_uuid(),
            name=request.name,
            from_system=request.from_system,
            to_system=request.to_system,
            profile=request.profile,
            avoid_systems=request.avoid_systems,
            use_bridges=request.use_bridges,
            use_wormholes=request.use_wormholes,
            created_by=character_id,
            total_jumps=total_jumps,
            path=path,
        )

        session.routes.append(route)
        session.updated_at = datetime.now(UTC)

        # Broadcast
        await self._broadcast_event(
            SessionEvent(
                session_id=session_id,
                event_type=SessionEventType.ROUTE_ADDED,
                data={"route": route.model_dump(mode="json")},
            )
        )

        return route

    async def remove_route(
        self,
        session_id: str,
        character_id: int,
        route_id: str,
    ) -> bool:
        """Remove a route from a session.

        Args:
            session_id: Session to remove route from
            character_id: Character removing the route
            route_id: Route to remove

        Returns:
            True if removed
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Check if participant with edit rights
        participant = None
        for p in session.participants:
            if p.character_id == character_id:
                participant = p
                break

        if not participant or participant.role == SessionRole.VIEWER:
            return False

        # Find and remove route
        for i, route in enumerate(session.routes):
            if route.id == route_id:
                session.routes.pop(i)
                session.updated_at = datetime.now(UTC)

                await self._broadcast_event(
                    SessionEvent(
                        session_id=session_id,
                        event_type=SessionEventType.ROUTE_REMOVED,
                        data={"route_id": route_id},
                    )
                )
                return True

        return False

    # =========================================================================
    # Waypoint Management
    # =========================================================================

    async def add_waypoint(
        self,
        session_id: str,
        character_id: int,
        request: AddWaypointRequest,
    ) -> SessionWaypoint | None:
        """Add a waypoint to a session."""
        session = self.get_session(session_id)
        if not session:
            return None

        # Check if participant
        participant = None
        for p in session.participants:
            if p.character_id == character_id:
                participant = p
                break

        if not participant or participant.role == SessionRole.VIEWER:
            return None

        waypoint = SessionWaypoint(
            id=_generate_uuid(),
            system_name=request.system_name,
            added_by=character_id,
            notes=request.notes,
            is_destination=request.is_destination,
        )

        session.waypoints.append(waypoint)
        session.updated_at = datetime.now(UTC)

        await self._broadcast_event(
            SessionEvent(
                session_id=session_id,
                event_type=SessionEventType.WAYPOINT_ADDED,
                data={"waypoint": waypoint.model_dump(mode="json")},
            )
        )

        return waypoint

    async def remove_waypoint(
        self,
        session_id: str,
        character_id: int,
        waypoint_id: str,
    ) -> bool:
        """Remove a waypoint from a session."""
        session = self.get_session(session_id)
        if not session:
            return False

        participant = None
        for p in session.participants:
            if p.character_id == character_id:
                participant = p
                break

        if not participant or participant.role == SessionRole.VIEWER:
            return False

        for i, wp in enumerate(session.waypoints):
            if wp.id == waypoint_id:
                session.waypoints.pop(i)
                session.updated_at = datetime.now(UTC)

                await self._broadcast_event(
                    SessionEvent(
                        session_id=session_id,
                        event_type=SessionEventType.WAYPOINT_REMOVED,
                        data={"waypoint_id": waypoint_id},
                    )
                )
                return True

        return False

    # =========================================================================
    # Messaging
    # =========================================================================

    async def send_message(
        self,
        session_id: str,
        character_id: int,
        character_name: str,
        message: str,
    ) -> SessionMessage | None:
        """Send a chat message to a session."""
        session = self.get_session(session_id)
        if not session:
            return None

        if not session.allow_chat:
            return None

        # Check if participant
        is_participant = any(p.character_id == character_id for p in session.participants)
        if not is_participant:
            return None

        msg = SessionMessage(
            id=_generate_uuid(),
            character_id=character_id,
            character_name=character_name,
            message=message[:500],  # Limit message length
        )

        session.messages.append(msg)

        # Trim old messages
        if len(session.messages) > MAX_MESSAGES_PER_SESSION:
            session.messages = session.messages[-MAX_MESSAGES_PER_SESSION:]

        session.updated_at = datetime.now(UTC)

        await self._broadcast_event(
            SessionEvent(
                session_id=session_id,
                event_type=SessionEventType.MESSAGE,
                data={"message": msg.model_dump(mode="json")},
            )
        )

        return msg

    # =========================================================================
    # Location Sharing
    # =========================================================================

    async def update_location(
        self,
        session_id: str,
        character_id: int,
        system_name: str,
    ) -> bool:
        """Update a participant's current location."""
        session = self.get_session(session_id)
        if not session:
            return False

        if not session.allow_location_sharing:
            return False

        for p in session.participants:
            if p.character_id == character_id:
                if p.sharing_location:
                    p.current_system = system_name

                    await self._broadcast_event(
                        SessionEvent(
                            session_id=session_id,
                            event_type=SessionEventType.PARTICIPANT_LOCATION,
                            data={
                                "character_id": character_id,
                                "system_name": system_name,
                            },
                        )
                    )
                return True

        return False

    async def toggle_location_sharing(
        self,
        session_id: str,
        character_id: int,
        enabled: bool,
    ) -> bool:
        """Toggle location sharing for a participant."""
        session = self.get_session(session_id)
        if not session:
            return False

        for p in session.participants:
            if p.character_id == character_id:
                p.sharing_location = enabled
                if not enabled:
                    p.current_system = None
                session.updated_at = datetime.now(UTC)
                return True

        return False

    # =========================================================================
    # Maintenance
    # =========================================================================

    def _cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = datetime.now(UTC)
        expired = []

        for session_id, session in self._sessions.items():
            if session.expires_at and session.expires_at < now:
                expired.append(session_id)
            elif session.state == SessionState.CLOSED:
                # Remove closed sessions after 1 hour
                if (now - session.updated_at).total_seconds() > 3600:
                    expired.append(session_id)

        for session_id in expired:
            del self._sessions[session_id]
            self._session_connections.pop(session_id, None)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)

    def get_stats(self) -> dict[str, Any]:
        """Get session manager statistics."""
        self._cleanup_expired()
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": sum(
                1 for s in self._sessions.values() if s.state == SessionState.ACTIVE
            ),
            "public_sessions": sum(1 for s in self._sessions.values() if s.public),
            "total_participants": sum(len(s.participants) for s in self._sessions.values()),
        }


# =============================================================================
# Dependency Injection
# =============================================================================

_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the session manager instance."""
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager()

    return _session_manager
