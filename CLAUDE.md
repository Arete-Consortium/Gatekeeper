# CLAUDE.md — EVE_Gatekeeper

## Project Overview

EVE Online navigation, routing, intel, and market visualization SaaS platform.

## Current State

- **Version**: 2.1.0 (pyproject.toml)
- **Codebase**: 641 files across 6 languages, ~166K lines
- **Backend**: Python 3.12 / FastAPI — 2,602 tests passing
- **Frontend**: TypeScript / Next.js 16.1.6 / React 18.2.0 / TailwindCSS 3.4 — 575 tests (Vitest)
- **Rendering**: Canvas2D subway-style maps (universe, FW, Pochven, route, jump range) + SVG overlays
- **Deployment**: Fly.io (backend) + Vercel (frontend, auto-deploy on push to main)
- **Database**: PostgreSQL on Fly.io
- **Billing**: Stripe (Pro $3/mo), direct checkout from account page + portal + webhook lifecycle + admin comp grants
- **Domains**: edengk.com (primary), gatekeeper.aretedriver.dev (alias)
- **Auth**: httpOnly cookie (`gk_session`) + Bearer token fallback, EVE SSO OAuth2
- **PWA**: manifest.json, standalone mode, theme-color #0e7490, custom logo icons

## Frontend Pages (19 routes)

| Route | Purpose |
|-------|---------|
| `/` | Landing → map (re-exports `/map`) |
| `/map` | Interactive New Eden map — 5400+ systems, kill stream, intel overlays, route planning |
| `/route` | Multi-stop route planner — gate routing + jump drive mode (toggle) |
| `/appraisal` | Bulk item appraisal — paste items, get buy/sell prices |
| `/pochven` | Pochven subway map — 27 systems, 3 Krais, BFS pathfinding |
| `/fw` | Faction warfare map — Canvas2D, faction-colored gates/systems |
| `/intel` | Live kill feed — hot systems table, sortable columns, pilot deep-dive |
| `/intel-parse` | Intel chat parser — paste local/intel → hostile highlights on map |
| `/fleet` | Fleet composition analyzer — paste fleet comp → threat assessment |
| `/market` | Market price ticker — ESI history, sortable table, green/red price changes |
| `/characters` | Multi-character dashboard — alt switching, location tracking, SSO linking |
| `/fitting` | Fitting analyzer — EFT paste → travel advice |
| `/alerts` | Alert subscriptions — Discord/Slack webhooks |
| `/pricing` | Subscription tiers + Stripe checkout |
| `/settings` | App preferences (API URL override) |
| `/login` | EVE SSO OAuth2 trigger |
| `/auth/callback` | OAuth2 callback handler |
| `/account` | Account management — direct subscribe button (non-Pro) or Stripe portal (Pro) |
| `/admin` | Hidden admin dashboard — system health metrics |

## Frontend Architecture

```
apps/web/src/
├── app/              # Next.js App Router pages (19 routes)
├── components/
│   ├── map/          # UniverseMap (Canvas2D), 11 SVG overlays, controls, hooks (39 files)
│   │   ├── SimpleMapCanvas.tsx    # Main canvas renderer (5400 systems, subway-style)
│   │   ├── UniverseMap.tsx        # Orchestrator — viewport, overlays, imperative ref
│   │   ├── types.ts               # MapSystem, MapGate, MapViewport, getRegionColor(), getSecurityColor()
│   │   ├── SovStructuresOverlay.tsx  # iHub ADM / Skyhook labels (SVG, collision-aware)
│   │   ├── WormholeOverlay.tsx    # User-submitted wormhole connections (SVG)
│   │   ├── CharacterMarker.tsx    # Real-time character location (SVG, pulsing)
│   │   ├── TheraOverlay.tsx       # EVE-Scout Thera connections (SVG)
│   │   ├── SovereigntyOverlay.tsx # Alliance sovereignty colors (SVG)
│   │   ├── FWOverlay.tsx          # Faction warfare occupancy (SVG)
│   │   ├── KillMarkers.tsx        # Live kill indicators (SVG)
│   │   ├── RiskHeatmap.tsx        # Risk score heatmap (SVG)
│   │   ├── RouteOverlay.tsx       # Route path highlight (SVG)
│   │   ├── LandmarksOverlay.tsx   # SDE landmarks (SVG)
│   │   ├── SkyhookHaloOverlay.tsx # Skyhook glow halos (SVG, sky-300)
│   │   ├── SkyhookOverlay.tsx     # Skyhook structure markers (SVG)
│   │   ├── ActivityOverlay.tsx    # System activity visualization (SVG)
│   │   ├── MarketHubsOverlay.tsx  # Trade hub markers (SVG)
│   │   ├── Minimap.tsx            # Overview minimap
│   │   ├── RouteControls.tsx      # Route planner panel
│   │   ├── SystemDetailPanel.tsx  # Selected system info
│   │   ├── SystemSearch.tsx       # System name search
│   │   └── SavedRoutes.tsx        # Bookmark management
│   ├── route/        # RouteResult, JumpRangeMap, RouteMap, JumpStrip, RouteStrip, WaypointList (10 files)
│   ├── pochven/      # PochvenMap (Canvas2D subway map)
│   ├── fw/           # FWMap (Canvas2D), FWSidebar, FWSystemDetail
│   ├── fitting/      # FittingAnalyzer
│   ├── fleet/        # FleetResult
│   ├── alerts/       # AlertForm (region filter, ship type tags), AlertCard, RegionFilter
│   ├── dashboard/    # LiveKillFeed (with PilotThreatCard + SystemSummaryCard popovers)
│   ├── intel/        # PilotDeepDive, PilotThreatCard, PilotLookupTab, IntelFeed, SystemSummaryCard, ThreatsTab
│   ├── system/       # SystemCard, RiskBadge, SecurityBadge
│   ├── market/       # MarketTicker
│   ├── characters/   # CharacterCard
│   ├── layout/       # Navbar (logo from /icon-192.png), Footer, StatusIndicator
│   └── ui/           # Button, Card, Input, Select, Toggle, Badge, Skeleton, etc. (14 files)
├── contexts/
│   ├── AuthContext.tsx           # Cookie-first auth with localStorage fallback
│   └── CookieConsentContext.tsx  # GDPR consent state
├── hooks/            # useRoute, useMultiRoute, useRouteHistory, useHotSystems
└── lib/
    ├── api.ts        # GatekeeperAPIService class (centralized HTTP client, credentials: 'include')
    ├── types.ts      # TypeScript interfaces matching backend Pydantic models
    ├── auth.ts       # JWT storage, token validation, user extraction, fetchSession()
    ├── cookies.ts    # Cookie consent utilities (gk_consent)
    └── utils.ts      # cn(), formatIsk(), formatRelativeTime(), debounce()
```

### Key Frontend Patterns

- **State**: TanStack Query 5 for server state, React Context for auth + cookie consent
- **SSR safety**: `dynamic(() => import(...), { ssr: false })` for canvas/WebSocket components
- **Barrel import pitfall**: Never import canvas components from barrel `@/components/map` — import directly from specific files to avoid SSR module evaluation
- **Map rendering**: Canvas2D subway-style maps with region-colored intra-region gates, dashed cross-region gates, labels below nodes, text shadows
- **Region coloring**: `getRegionColor(regionId)` in `apps/web/src/components/map/types.ts` — golden ratio conjugate hash (`regionId * 137.508 % 360`) for even HSL hue distribution across ~68 regions
- **Auth**: httpOnly cookie (`gk_session`) primary, localStorage JWT fallback, `useAuth()` hook, `isPro` gate
- **Layer persistence**: Map layer toggles + color mode + layout mode saved to `localStorage` (`gk_map_layers`, `gk_map_color_mode`, `gk_map_layout_mode`)
- **Layout modes**: `subway` (compressed, 50% region centroid attraction) or `dotlan` (raw EVE coordinates, CCP/Dotlan-style spatial). Toggle in sidebar under "Layout". UniverseMap compression is conditional on `layoutMode` prop
- **Character tracking**: TanStack Query polls `/character/location` every 10s when authenticated
- **SVG overlay pattern**: All map overlays are SVG elements positioned absolutely over the canvas, using viewport transform `(system.x - viewport.x) * viewport.zoom + viewport.width / 2`
- **Canvas label suppression**: When SovStructuresOverlay renders for a system (iHub/Skyhook), SimpleMapCanvas skips its canvas label via `sovStructureSystems` Set prop
- **Service worker**: `sw.js` — network-first for API/navigation, cache-first for static assets, registered in production only via `ServiceWorkerRegistration.tsx`
- **Wormhole persistence**: PostgreSQL via `WormholeConnectionDB` model, write-through cache, hourly expired connection cleanup
- **Pinning system**: Pilots, corps, alliances, systems pinnable via localStorage with cross-tab sync via `storage` event
- **Map aesthetic**: Dark navy `#0a0e17` background, subway-style gates (region-colored intra, dashed `#334155` cross-region), labels below nodes with text shadow

### localStorage Keys

| Key | Purpose |
|-----|---------|
| `gk_consent` | GDPR cookie consent state (`{ analytics: boolean }`) |
| `gk_map_color_mode` | Map coloring: "security" / "risk" / "star" |
| `gk_map_layout_mode` | Map layout: "subway" / "dotlan" |
| `gk_map_layers` | Map layer toggles (JSON object) |
| `gk_pinned_pilots` | Pinned pilot intelligence list |
| `gk_pinned_corps` | Pinned corporation list |
| `gk_pinned_alliances` | Pinned alliance list |
| `gk_pinned_systems` | Pinned system list |
| `gk_session_id` | Session ID fallback |
| `gatekeeper_api_url` | Custom API URL override (settings page) |

### Map Layer Architecture

| Layer | Component | Toggle Key | Pro? | Data Source |
|-------|-----------|------------|------|-------------|
| Gates | SimpleMapCanvas | `showGates` | No | /map/config |
| Labels | SimpleMapCanvas | `showLabels` | No | /map/config |
| Region labels | SimpleMapCanvas | `showRegionLabels` | No | /map/config |
| Route | RouteOverlay | `showRoute` | No | useMapRoute |
| Kill markers | KillMarkers | `showKills` | Yes | WebSocket /ws/killfeed |
| Risk heatmap | RiskHeatmap | `showHeatmap` | Yes | /map/config risks |
| Sovereignty | SovereigntyOverlay | `showSovereignty` | Yes | /map/sovereignty |
| Thera | TheraOverlay | `showThera` | Yes | /map/thera |
| Faction warfare | FWOverlay | `showFW` | Yes | /map/fw |
| Landmarks | LandmarksOverlay | `showLandmarks` | No | /map/config |
| iHub ADM | SovStructuresOverlay | `showSovStructures` | Yes | /map/sovereignty/structures |
| Skyhook halos | SkyhookHaloOverlay | `showSkyhooks` | Yes | /map/sovereignty/structures |
| Wormholes | WormholeOverlay | `showWormholes` | Yes | /api/v1/wormholes/ |
| System activity | ActivityOverlay | `showActivity` | Yes | /map/activity |
| Trade hubs | MarketHubsOverlay | `showMarketHubs` | No | /map/market-hubs |

### Sov Structures Overlay Details

- **Structure types**: iHub (32458), TCU (32226), Orbital Skyhook (81080), Metenox Moon Drill (81826)
- **Rendering**: 2-row stacked text block — Row 1: system name, Row 2: ADM level + "S" for skyhook
- **ADM colors**: red (<=1) → orange (<=2) → yellow (<=3) → lime (<=4) → green (>=5), gray for null
- **Font scaling**: 30% increase at zoom >= 3
- **Collision avoidance**: Bounding box overlap detection, shifts labels down vertically
- **Canvas suppression**: Systems with iHub or Skyhook get SVG label, canvas label suppressed. TCU-only systems keep canvas labels.

### Intel System

- **PilotThreatCard**: Quick threat display — threat level, K/D, flags, timezone, pinnable to kill feed
- **PilotDeepDive**: Full dossier — fleet companions, 24h activity pattern, corp history, recent kills timeline, ship doctrine
- **PilotLookupTab**: Autocomplete search + bulk fleet lookup with aggregate threat breakdown
- **IntelFeed**: Live kill feed from WebSocket with pilot/system popovers
- **SystemSummaryCard**: System-level intel popover with risk scoring
- **ThreatsTab**: Region-filtered threat aggregation
- **Pinning**: Pilots, corps, alliances pinnable from threat cards, stored in localStorage, synced cross-tab

## Backend Architecture

```
backend/
├── app/
│   ├── api/v1/       # FastAPI routers (36 files)
│   │   ├── auth.py         # EVE SSO OAuth2, JWT, httpOnly cookies, session endpoint
│   │   ├── character.py    # ESI location, ship, waypoint, route-from-here
│   │   ├── characters.py   # Multi-character management, preferences, avoid/watch lists
│   │   ├── routing.py      # Route calculation
│   │   ├── alerts.py       # Alert subscription CRUD
│   │   ├── webhooks.py     # Webhook CRUD (duplicate of alerts, masks URLs)
│   │   ├── wormholes.py    # Wormhole connection CRUD + WebSocket broadcast
│   │   ├── map.py          # Route/region/constellation visualization
│   │   ├── intel.py        # Kill aggregation, risk scoring, pilot deep-dive
│   │   ├── billing.py      # Stripe checkout/portal/webhook
│   │   ├── admin.py        # Admin comp Pro grants/revokes (X-Admin-Secret auth)
│   │   ├── websocket.py    # /ws/killfeed + /ws/map real-time streams
│   │   └── dependencies.py # Auth deps: LocationScope, WaypointScope, cookie+bearer
│   ├── core/         # Config, security, pagination
│   ├── models/       # Pydantic request/response models
│   ├── db/           # SQLAlchemy models + Alembic migrations
│   └── services/     # 41 service modules
│       ├── routing.py        # Dijkstra with gate/bridge/Thera/Pochven/wormhole edges
│       ├── jump_drive.py     # Capital jump planning — fuel, fatigue, range
│       ├── pochven.py        # 27-system Pochven network
│       ├── intel.py          # Kill data aggregation, risk scoring
│       ├── wormhole.py       # Wormhole connection management (in-memory + DB)
│       ├── webhooks.py       # Discord/Slack webhook formatting + dispatch
│       ├── zkill_listener.py # zKillboard RedisQ listener → kills + alerts
│       ├── kill_history.py   # Rolling kill window (PostgreSQL persistence)
│       ├── thera.py          # EVE-Scout API integration (5-min cache)
│       ├── pilot_intel.py    # Pilot threat assessment + deep-dive (ESI + zKill + corp history)
│       ├── hotzone.py        # Hotzone detection with trend prediction
│       ├── appraisal.py      # Fuzzwork API for Jita prices
│       ├── stripe_service.py # Stripe billing (checkout, portal, webhooks)
│       ├── token_store.py    # Encrypted ESI token storage
│       ├── fw_cache.py       # Faction warfare ESI cache (5-min expiry)
│       ├── market_hubs.py    # Live ESI market order counts
│       ├── market_ticker.py  # Market history caching
│       ├── risk_engine.py    # Risk calculation with zKillboard integration
│       ├── ai_analyzer.py    # AI-powered route danger analysis
│       └── ...               # 22 more (fitting, fleet, cache, redis, data_loader, etc.)
├── starmap/
│   ├── sde/          # SDE data models + SQLite schema
│   ├── esi/          # ESI client with rate limiting + token refresh
│   ├── graph/        # Universe graph for pathfinding
│   └── ingest_sde.py # SDE import pipeline
└── data/             # universe.json (5432 systems, 6888 gates), risk_config.json
```

### Key Backend Services

- **routing.py**: Dijkstra shortest-path with gate/bridge/Thera/Pochven/wormhole edges
- **jump_drive.py**: Capital ship jump planning — fuel, fatigue, range, cyno-eligible filtering
- **pochven.py**: 27-system Pochven internal gate network (3 Krais, 30 SDE-verified connections)
- **intel.py**: Kill data aggregation, risk scoring, hot systems
- **auth.py**: EVE SSO OAuth2 → JWT + httpOnly cookie (`gk_session`), session endpoint
- **webhooks.py**: Discord/Slack kill alert dispatch, subscription filtering (system/region/value/pod/ship), **PostgreSQL-persisted subscriptions** (write-through)
- **zkill_listener.py**: zKillboard RedisQ → kill history + WebSocket broadcast + webhook dispatch
- **kill_history.py**: Rolling kill window with **PostgreSQL persistence** — loads on startup, fire-and-forget writes, background cleanup
- **wormhole.py**: User-submitted wormhole connections with mass/life tracking, automatic expiry
- **pilot_intel.py**: Pilot threat assessment + deep-dive — ESI character info + zKill stats, threat level scoring, timezone inference, behavior flags, fleet companions (from zKill topLists), corp history (ESI), recent kills, 24h activity pattern
- **hotzone.py**: Hotzone detection — aggregates kill history with trend prediction (decay factor 0.7), gate camp detection (pod:kill ratio > 0.5)
- **stripe_service.py**: Checkout session creation, billing portal, webhook processing
- **fw_cache.py**: Faction warfare system data from ESI with 5-min cache

### Intel API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/intel/pilot/{character_id}` | GET | Basic pilot threat assessment |
| `/intel/pilot/{character_id}/deep-dive` | GET | Full dossier: companions, activity, corp history, recent kills |
| `/intel/pilot/search` | GET | Autocomplete pilot name search |
| `/intel/pilot/fleet-lookup` | POST | Bulk fleet threat assessment |

### Auth Flow

1. EVE SSO OAuth2 → `/auth/callback` → JWT issued
2. JWT stored in httpOnly cookie (`gk_session`, SameSite=None, Secure) + localStorage fallback
3. All API requests include `credentials: 'include'` for cross-origin cookie sending
4. `dependencies.py` checks Authorization header first, then `gk_session` cookie
5. ESI scopes: `esi-location.read_location.v1` + `esi-ui.write_waypoint.v1` only

### Alert Pipeline

```
zKillboard RedisQ → zkill_listener._process_kill()
  ├─→ kill_history.add_kill()
  ├─→ connection_manager.broadcast_kill() (WebSocket)
  ├─→ webhooks.dispatch_alert() → KillAlert → filter subscriptions → async send
  └─→ connection_manager.broadcast_system_risk_update() (WebSocket)
```

### Cookie Consent (GDPR)

- Auth cookies (`gk_session`): "strictly necessary" — exempt from consent
- Analytics cookies: gated behind `gk_consent` cookie with `analytics: true`
- `CookieConsentBanner` component with "Accept All" / "Necessary Only"
- `ConsentGatedVercelAnalytics` only renders when consent.analytics === true

## EVE Domain Rules (Critical)

- **Cyno mechanics**: Cynos can only be lit in lowsec/nullsec (not highsec, WH, or Pochven)
- **Pochven jump drives**: Can jump OUT of Pochven but NOT into it — Pochven systems appear as nullsec (security -1.0) but must be explicitly excluded from cyno destinations
- **Pochven internal gates**: 27 systems in 3 Krais (Perun/Svarog/Veles), connected by conduit gates. Fixed topology, no branches. Cross-Krai borders at 3 junctions.
- **Filaments**: Random destinations — not predictable, don't model as fixed routes
- **Security classes**: highsec (>=0.5), lowsec (0.1-0.4), nullsec (<=0.0)
- **ESI scopes**: Only `read_location` + `write_waypoint` remain valid (CCP deprecated others)
- **Sov structures**: iHub (32458) has ADM 0-6 (can be null), TCU (32226), Orbital Skyhook (81080), Metenox Moon Drill (81826)

## Common Commands

```bash
# Backend
source .venv/bin/activate && python3 -m pytest tests/ -x -q
ruff check backend/ tests/ && ruff format backend/ tests/

# Frontend
cd apps/web && npx next build
cd apps/web && npx vitest run
cd apps/web && npx next dev

# Deploy
/home/arete/.fly/bin/flyctl deploy --remote-only --wait-timeout 600 --app eve-gatekeeper
git push origin main  # triggers Vercel auto-deploy

# Fly secrets
/home/arete/.fly/bin/flyctl secrets set KEY=VALUE --app eve-gatekeeper

# Database migrations
cd backend && source ../.venv/bin/activate && alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI |
| Frontend framework | Next.js 16.1.6 (App Router) |
| UI library | React 18.2.0 + TailwindCSS 3.4 |
| Map rendering | Canvas2D (subway-style) + SVG overlays |
| Server state | TanStack Query 5.28.0 |
| Icons | Lucide React 0.363.0 |
| Testing (backend) | pytest (2602 passing) |
| Testing (frontend) | Vitest + Playwright |
| Linting | ruff (Python), ESLint (TS) |
| CI/CD | GitHub Actions |
| Containerization | Docker (uvicorn) |
| Database | PostgreSQL + SQLAlchemy + Alembic |
| Auth | EVE SSO OAuth2, JWT, httpOnly cookies |
| Payments | Stripe (checkout, portal, webhooks) |
| PWA | manifest.json (standalone, installable) |

## Coding Standards

- **Python**: snake_case, double quotes, type hints, google-style docstrings, pathlib (not os.path)
- **TypeScript**: strict mode, const/let (no var), proper interfaces (no `any`)
- **Error handling**: Specific exceptions (no bare `except:`), Pydantic response models (no raw dicts)
- **Logging**: `logging` module (no `print()`)
- **Secrets**: Environment variables only (no hardcoded values)
- **Git**: Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- **Tests**: Mock lucide-react icons in test files, wrap TanStack Query consumers in QueryClientProvider

## Anti-Patterns

- Do NOT import from `@/components/map` barrel in SSR contexts — import specific files
- Do NOT model filament entry/exit as predictable routes — they're random
- Do NOT include Pochven systems in cyno destination candidates
- Do NOT use synchronous database calls in async endpoints
- Do NOT use mutable default arguments in Python
- Do NOT use `latest` tag in Docker — pin specific versions
- Do NOT suppress canvas labels for TCU-only systems — only iHub (32458) and Orbital Skyhook (81080), Metenox Moon Drill (81826)
- Do NOT render SVG overlay for systems with null ADM without a name-only fallback block
- Do NOT forget `credentials: 'include'` on cross-origin fetch calls (cookie auth breaks)
- Do NOT use `--timeout` flag with pytest (plugin not installed) — use `-x -q` for fast failure
- Do NOT commit secrets, API keys, or credentials
- Do NOT skip writing tests for new code
- Do NOT return raw dicts from endpoints — use Pydantic response models

## Admin Comp System

- **Endpoint**: `POST /api/v1/admin/grant-pro` / `POST /api/v1/admin/revoke-pro`
- **Auth**: `X-Admin-Secret` header checked against `ADMIN_SECRET` env var
- **Fields**: `User.comp_expires_at` (auto-expire), `User.comp_reason`
- **Auto-downgrade**: `_get_subscription_tier()` in dependencies checks comp expiration on every auth'd request
- **Safety**: Revoke refuses to touch users with active Stripe subscriptions

## Architecture

Monorepo with Python backend + Next.js frontend:

```
Gatekeeper/
├── backend/           # FastAPI (Python 3.12) — API, services, DB
│   ├── app/api/v1/    # 36 route files
│   ├── app/services/  # 41 service modules
│   ├── app/db/        # SQLAlchemy + Alembic migrations
│   └── starmap/       # SDE, ESI client, universe graph
├── apps/web/          # Next.js 16 (TypeScript) — App Router, Canvas2D maps
│   └── src/
│       ├── app/       # 19 routes
│       ├── components/# map/ (Canvas2D + 11 SVG overlays), route/, intel/, ui/
│       ├── contexts/  # Auth, CookieConsent
│       └── lib/       # API client, types, utils
├── data/              # universe.json, risk_config.json
└── tests/             # pytest (backend), vitest (frontend)
```

Data flow: ESI/zKill → backend services → FastAPI endpoints → TanStack Query → Canvas2D/SVG rendering

## Dependencies

**Backend** (`pyproject.toml`): FastAPI, SQLAlchemy, Alembic, httpx, pydantic, stripe, python-jose
**Frontend** (`apps/web/package.json`): next, react, @tanstack/react-query, tailwindcss, lucide-react

> Note: This is a monorepo — frontend dependencies are in `apps/web/package.json`, not the project root.

## Git Conventions

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Commit messages explain "why", not just "what"
- Main branch deploys automatically (Fly.io backend, Vercel frontend)
- Branch protection bypassed for direct pushes (CI billing blocker)

## Domain Context

EVE Online third-party tool for navigation, intel, and market analysis. Users are EVE players who need:
- Route planning through dangerous space (nullsec gate camps, pirate insurgency)
- Real-time kill intel (zKillboard feed) with threat assessment
- Map visualization of 5400+ solar systems across ~68 regions
- Multi-character management with ESI OAuth2

Key domain terms: system (solar system), gate (stargate connection), security status (-1.0 to 1.0), gate camp (ambush at stargate), Pochven (isolated region), sovereignty (alliance-controlled space), ESI (EVE Swagger Interface API)

## Outstanding Notes

- zKill API puts stats at top level (`data.shipsDestroyed`), NOT nested under `data.info` — see `pilot_intel.py`
- `apps/web/next-env.d.ts` is auto-generated — do NOT edit
- MCP server entry point: `backend.app.mcp.server:main`
