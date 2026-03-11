"""API v1 router - consolidates all versioned endpoints."""

from fastapi import APIRouter

from .ai import router as ai_router
from .alerts import router as alerts_router
from .analytics import router as analytics_router
from .appraisal import router as appraisal_router
from .auth import router as auth_router
from .avoidance import router as avoidance_router
from .billing import router as billing_router
from .bookmarks import router as bookmarks_router
from .bridges import router as bridges_router
from .character import router as character_router
from .characters import router as characters_router
from .errors import router as errors_router
from .fatigue import router as fatigue_router
from .fitting import router as fitting_router
from .fleet import router as fleet_router
from .intel import router as intel_router
from .intel_parse import router as intel_parse_router
from .jump import router as jump_router
from .jumpbridge_connections import router as jumpbridge_connections_router
from .links import router as links_router
from .map import router as map_router
from .market_ticker import router as market_ticker_router
from .notes import router as notes_router
from .pochven import router as pochven_router
from .routing import router as routing_router
from .sessions import router as sessions_router
from .sharing import router as sharing_router
from .stats import router as stats_router
from .status import router as status_router
from .systems import router as systems_router
from .thera import router as thera_router
from .webhooks import router as webhooks_router
from .websocket import router as websocket_router
from .wormholes import router as wormholes_router

router = APIRouter(prefix="/api/v1")

router.include_router(ai_router, prefix="/ai", tags=["ai"])
router.include_router(alerts_router)
router.include_router(avoidance_router, prefix="/avoidance", tags=["avoidance"])
router.include_router(auth_router, tags=["auth"])
router.include_router(billing_router)
router.include_router(bookmarks_router, prefix="/bookmarks", tags=["bookmarks"])
router.include_router(intel_router)
router.include_router(intel_parse_router)
router.include_router(stats_router, prefix="/stats", tags=["stats"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
router.include_router(character_router)
router.include_router(characters_router)
router.include_router(systems_router, prefix="/systems", tags=["systems"])
router.include_router(routing_router, prefix="/route", tags=["routing"])
router.include_router(sessions_router)
router.include_router(sharing_router)
router.include_router(jump_router, prefix="/jump", tags=["jump"])
router.include_router(notes_router)
router.include_router(fatigue_router)
router.include_router(map_router)
router.include_router(fitting_router)
router.include_router(fleet_router)
router.include_router(bridges_router, prefix="/bridges", tags=["bridges"])
router.include_router(thera_router, prefix="/thera", tags=["thera"])
router.include_router(pochven_router, prefix="/pochven", tags=["pochven"])
router.include_router(wormholes_router)
router.include_router(jumpbridge_connections_router)
router.include_router(status_router, prefix="/status", tags=["status"])
router.include_router(websocket_router, tags=["websocket"])
router.include_router(links_router)
router.include_router(errors_router, prefix="/errors", tags=["errors"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
router.include_router(appraisal_router)
router.include_router(market_ticker_router)
