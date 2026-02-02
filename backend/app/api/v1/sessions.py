"""Collaborative routing session API endpoints.

Enables real-time collaborative route planning between multiple users.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from ...core.config import settings
from ...models.session import (
    AddRouteRequest,
    AddWaypointRequest,
    CreateSessionRequest,
    CreateSessionResponse,
    JoinSessionResponse,
    RoutingSession,
    SendMessageRequest,
    SessionEvent,
    SessionListResponse,
    SessionMessage,
    SessionRoute,
    SessionUpdate,
    SessionWaypoint,
)
from ...services.session_manager import SessionManager, get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# =============================================================================
# Session Management
# =============================================================================


@router.post(
    "/",
    response_model=CreateSessionResponse,
    summary="Create a routing session",
    description="Create a new collaborative routing session.",
    status_code=201,
)
async def create_session(
    request: CreateSessionRequest,
    character_id: int = Query(..., description="Creating character ID"),
    character_name: str = Query(..., description="Creating character name"),
    manager: SessionManager = Depends(get_session_manager),
) -> CreateSessionResponse:
    """
    Create a new collaborative routing session.

    The creating character becomes the session owner with full control.
    """
    session = manager.create_session(request, character_id, character_name)

    # Build join URL
    base_url = settings.API_BASE_URL or "http://localhost:8000"
    join_url = f"{base_url}/api/v1/sessions/{session.id}/join"

    return CreateSessionResponse(
        session_id=session.id,
        join_code=session.id,
        join_url=join_url,
        session=session,
    )


@router.get(
    "/",
    response_model=SessionListResponse,
    summary="List sessions",
    description="List active sessions. Can filter by public or user's own sessions.",
)
async def list_sessions(
    public: bool = Query(False, description="List only public sessions"),
    character_id: int | None = Query(None, description="List sessions for a character"),
    manager: SessionManager = Depends(get_session_manager),
) -> SessionListResponse:
    """
    List active routing sessions.

    - If `public=True`, lists all public sessions anyone can join.
    - If `character_id` is provided, lists sessions the character is participating in.
    """
    if public:
        sessions = manager.list_public_sessions()
    elif character_id:
        sessions = manager.list_user_sessions(character_id)
    else:
        # Default to public sessions
        sessions = manager.list_public_sessions()

    return SessionListResponse(
        sessions=sessions,
        total_count=len(sessions),
    )


@router.get(
    "/{session_id}",
    response_model=RoutingSession,
    summary="Get session details",
    description="Get full details of a routing session.",
)
async def get_session(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager),
) -> RoutingSession:
    """
    Get full details of a routing session.
    """
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post(
    "/{session_id}/join",
    response_model=JoinSessionResponse,
    summary="Join a session",
    description="Join an existing routing session.",
)
async def join_session(
    session_id: str,
    character_id: int = Query(..., description="Character ID"),
    character_name: str = Query(..., description="Character name"),
    manager: SessionManager = Depends(get_session_manager),
) -> JoinSessionResponse:
    """
    Join an existing routing session.

    Returns the session if successfully joined, or pending_approval if approval is required.
    """
    session, pending, error = await manager.join_session(session_id, character_id, character_name)

    if error:
        return JoinSessionResponse(
            success=False,
            error=error,
        )

    return JoinSessionResponse(
        success=True,
        session=session,
        pending_approval=pending,
    )


@router.post(
    "/{session_id}/leave",
    summary="Leave a session",
    description="Leave a routing session.",
)
async def leave_session(
    session_id: str,
    character_id: int = Query(..., description="Character ID"),
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, str]:
    """
    Leave a routing session.

    If the owner leaves and there are other participants, ownership transfers
    to the next participant. If no one remains, the session closes.
    """
    success = await manager.leave_session(session_id, character_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or not a participant")

    return {"status": "left", "session_id": session_id}


@router.patch(
    "/{session_id}",
    response_model=RoutingSession,
    summary="Update session settings",
    description="Update session settings (owner only).",
)
async def update_session(
    session_id: str,
    update: SessionUpdate,
    character_id: int = Query(..., description="Character ID (must be owner)"),
    manager: SessionManager = Depends(get_session_manager),
) -> RoutingSession:
    """
    Update session settings.

    Only the session owner can update settings.
    """
    session = await manager.update_session(session_id, character_id, update)

    if not session:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this session",
        )

    return session


@router.delete(
    "/{session_id}",
    summary="Close a session",
    description="Close a routing session (owner only).",
)
async def close_session(
    session_id: str,
    character_id: int = Query(..., description="Character ID (must be owner)"),
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, str]:
    """
    Close a routing session.

    Only the session owner can close the session. All participants will be
    notified via WebSocket.
    """
    success = await manager.close_session(session_id, character_id)

    if not success:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to close this session",
        )

    return {"status": "closed", "session_id": session_id}


# =============================================================================
# Route Management
# =============================================================================


@router.post(
    "/{session_id}/routes",
    response_model=SessionRoute,
    summary="Add route to session",
    description="Add a calculated route to the session.",
    status_code=201,
)
async def add_route(
    session_id: str,
    request: AddRouteRequest,
    character_id: int = Query(..., description="Character ID"),
    manager: SessionManager = Depends(get_session_manager),
) -> SessionRoute:
    """
    Add a route to the session.

    The route is calculated automatically based on the request parameters.
    Only owners and editors can add routes.
    """
    route = await manager.add_route(session_id, character_id, request)

    if not route:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to add routes to this session",
        )

    return route


@router.delete(
    "/{session_id}/routes/{route_id}",
    summary="Remove route from session",
    description="Remove a route from the session.",
)
async def remove_route(
    session_id: str,
    route_id: str,
    character_id: int = Query(..., description="Character ID"),
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, str]:
    """
    Remove a route from the session.

    Only owners and editors can remove routes.
    """
    success = await manager.remove_route(session_id, character_id, route_id)

    if not success:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to remove routes from this session",
        )

    return {"status": "removed", "route_id": route_id}


# =============================================================================
# Waypoint Management
# =============================================================================


@router.post(
    "/{session_id}/waypoints",
    response_model=SessionWaypoint,
    summary="Add waypoint to session",
    description="Add a waypoint to the session.",
    status_code=201,
)
async def add_waypoint(
    session_id: str,
    request: AddWaypointRequest,
    character_id: int = Query(..., description="Character ID"),
    manager: SessionManager = Depends(get_session_manager),
) -> SessionWaypoint:
    """
    Add a waypoint to the session.

    Waypoints are shared with all participants. Only owners and editors can add waypoints.
    """
    waypoint = await manager.add_waypoint(session_id, character_id, request)

    if not waypoint:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to add waypoints to this session",
        )

    return waypoint


@router.delete(
    "/{session_id}/waypoints/{waypoint_id}",
    summary="Remove waypoint from session",
    description="Remove a waypoint from the session.",
)
async def remove_waypoint(
    session_id: str,
    waypoint_id: str,
    character_id: int = Query(..., description="Character ID"),
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, str]:
    """
    Remove a waypoint from the session.

    Only owners and editors can remove waypoints.
    """
    success = await manager.remove_waypoint(session_id, character_id, waypoint_id)

    if not success:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to remove waypoints from this session",
        )

    return {"status": "removed", "waypoint_id": waypoint_id}


# =============================================================================
# Messaging
# =============================================================================


@router.post(
    "/{session_id}/messages",
    response_model=SessionMessage,
    summary="Send message to session",
    description="Send a chat message to the session.",
    status_code=201,
)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    character_id: int = Query(..., description="Character ID"),
    character_name: str = Query(..., description="Character name"),
    manager: SessionManager = Depends(get_session_manager),
) -> SessionMessage:
    """
    Send a chat message to the session.

    Messages are broadcast to all participants in real-time.
    """
    message = await manager.send_message(session_id, character_id, character_name, request.message)

    if not message:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to send messages to this session or chat is disabled",
        )

    return message


# =============================================================================
# Location Sharing
# =============================================================================


@router.post(
    "/{session_id}/location",
    summary="Update location",
    description="Update your current location in the session.",
)
async def update_location(
    session_id: str,
    system_name: str = Query(..., description="Current system name"),
    character_id: int = Query(..., description="Character ID"),
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, str]:
    """
    Update your current location in the session.

    Location updates are broadcast to all participants who have location sharing enabled.
    """
    success = await manager.update_location(session_id, character_id, system_name)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Session not found or location sharing not enabled",
        )

    return {"status": "updated", "system_name": system_name}


@router.post(
    "/{session_id}/location/toggle",
    summary="Toggle location sharing",
    description="Enable or disable location sharing for yourself.",
)
async def toggle_location_sharing(
    session_id: str,
    enabled: bool = Query(..., description="Enable or disable"),
    character_id: int = Query(..., description="Character ID"),
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, Any]:
    """
    Enable or disable location sharing for yourself.

    When disabled, your location is no longer broadcast to other participants.
    """
    success = await manager.toggle_location_sharing(session_id, character_id, enabled)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found or not a participant")

    return {"status": "toggled", "sharing_location": enabled}


# =============================================================================
# Statistics
# =============================================================================


@router.get(
    "/stats",
    summary="Get session statistics",
    description="Get statistics about collaborative sessions.",
)
async def get_session_stats(
    manager: SessionManager = Depends(get_session_manager),
) -> dict[str, Any]:
    """
    Get statistics about collaborative routing sessions.
    """
    return manager.get_stats()


# =============================================================================
# WebSocket for Real-time Updates
# =============================================================================


@router.websocket("/ws/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: str,
    character_id: int,
    character_name: str,
    manager: SessionManager = Depends(get_session_manager),
) -> None:
    """
    WebSocket endpoint for real-time session updates.

    Connect to receive:
    - Participant join/leave events
    - Route/waypoint changes
    - Chat messages
    - Location updates

    Send:
    - {"type": "location", "system_name": "Jita"} - Update your location
    - {"type": "message", "message": "Hello"} - Send chat message
    - {"type": "ping"} - Keep connection alive
    """
    session = manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return

    # Verify participant
    is_participant = any(p.character_id == character_id for p in session.participants)
    if not is_participant:
        await websocket.close(code=4003, reason="Not a participant")
        return

    await websocket.accept()

    # Register for events
    async def event_handler(event: SessionEvent) -> None:
        if event.session_id == session_id:
            try:
                await websocket.send_json(event.model_dump(mode="json"))
            except Exception:
                pass

    manager.register_event_callback(event_handler)

    # Send initial state
    await websocket.send_json(
        {
            "type": "connected",
            "session_id": session_id,
            "session": session.model_dump(mode="json"),
        }
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "location":
                system = data.get("system_name")
                if system:
                    await manager.update_location(session_id, character_id, system)

            elif msg_type == "message":
                message = data.get("message")
                if message:
                    await manager.send_message(session_id, character_id, character_name, message)

    except WebSocketDisconnect:
        logger.info(
            "Session WebSocket disconnected",
            extra={"session_id": session_id, "character_id": character_id},
        )
    except Exception as e:
        logger.exception(f"Session WebSocket error: {e}")
