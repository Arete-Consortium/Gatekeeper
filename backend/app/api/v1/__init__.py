"""API v1 router - consolidates all versioned endpoints."""

from fastapi import APIRouter

from .ai import router as ai_router
from .auth import router as auth_router
from .bookmarks import router as bookmarks_router
from .bridges import router as bridges_router
from .character import router as character_router
from .fatigue import router as fatigue_router
from .intel import router as intel_router
from .jump import router as jump_router
from .links import router as links_router
from .notes import router as notes_router
from .routing import router as routing_router
from .sharing import router as sharing_router
from .stats import router as stats_router
from .status import router as status_router
from .systems import router as systems_router
from .webhooks import router as webhooks_router
from .websocket import router as websocket_router

router = APIRouter(prefix="/api/v1")

router.include_router(ai_router, prefix="/ai", tags=["ai"])
router.include_router(auth_router, tags=["auth"])
router.include_router(bookmarks_router, prefix="/bookmarks", tags=["bookmarks"])
router.include_router(intel_router)
router.include_router(stats_router, prefix="/stats", tags=["stats"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
router.include_router(character_router)
router.include_router(systems_router, prefix="/systems", tags=["systems"])
router.include_router(routing_router, prefix="/route", tags=["routing"])
router.include_router(sharing_router)
router.include_router(jump_router, prefix="/jump", tags=["jump"])
router.include_router(notes_router)
router.include_router(fatigue_router)
router.include_router(bridges_router, prefix="/bridges", tags=["bridges"])
router.include_router(status_router, prefix="/status", tags=["status"])
router.include_router(websocket_router, tags=["websocket"])
router.include_router(links_router)
