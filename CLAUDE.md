# CLAUDE.md — EVE_Gatekeeper

## Project Overview

EVE Online navigation, routing, intel, and market visualization SaaS platform.

## Current State

- **Version**: 1.6.0
- **Backend**: Python 3.12 / FastAPI — 2,200+ tests passing
- **Frontend**: TypeScript / Next.js 16 / React 18 / TailwindCSS 3.4
- **Rendering**: Pixi.js 7 (universe map), Canvas2D (jump range map, Pochven map)
- **Deployment**: Fly.io (backend) + Vercel (frontend)
- **Domains**: gatekeeper.aretedriver.dev (frontend), eve-gatekeeper.fly.dev (API)
- **Database**: PostgreSQL on Fly.io
- **Billing**: Stripe (Pro $3/mo), checkout + portal + webhook lifecycle

## Frontend Pages (14 routes)

| Route | Purpose |
|-------|---------|
| `/` | Landing → map (re-exports `/map`) |
| `/map` | Interactive New Eden map — 5400+ systems, kill stream, intel overlays, route planning |
| `/route` | Multi-stop route planner — gate routing + jump drive mode (toggle) |
| `/appraisal` | Bulk item appraisal — paste items, get buy/sell prices |
| `/pochven` | Pochven subway map — 27 systems, 3 Krais, BFS pathfinding |
| `/intel` | Live kill feed — hot systems table, sortable columns |
| `/fitting` | Fitting analyzer — EFT paste → travel advice |
| `/alerts` | Alert subscriptions — Discord/Slack webhooks |
| `/pricing` | Subscription tiers + Stripe checkout |
| `/settings` | App preferences (API URL override) |
| `/login` | EVE SSO OAuth2 trigger |
| `/auth/callback` | OAuth2 callback handler |
| `/account` | Account management (billing portal) |

## Frontend Architecture

```
apps/web/src/
├── app/              # Next.js App Router pages
├── components/
│   ├── map/          # UniverseMap (Pixi.js), overlays, controls, hooks
│   ├── route/        # RouteResult, JumpRangeMap, WaypointList
│   ├── pochven/      # PochvenMap (Canvas2D subway map)
│   ├── fitting/      # FittingAnalyzer
│   ├── alerts/       # AlertForm, AlertCard
│   ├── dashboard/    # LiveKillFeed
│   ├── system/       # SystemCard, RiskBadge, SecurityBadge
│   ├── layout/       # Navbar, Footer, StatusIndicator
│   └── ui/           # Button, Card, Input, Select, Toggle, Badge, etc.
├── contexts/         # AuthContext (JWT + subscription state)
├── hooks/            # useRoute, useMultiRoute, useRouteHistory, useHotSystems
└── lib/
    ├── api.ts        # GatekeeperAPIService class (centralized HTTP client)
    ├── types.ts      # TypeScript interfaces matching backend Pydantic models
    ├── auth.ts       # JWT storage, token validation, user extraction
    └── utils.ts      # cn(), formatIsk(), formatRelativeTime(), debounce()
```

### Key Frontend Patterns

- **State**: TanStack Query 5 for server state, React Context for auth
- **SSR safety**: `dynamic(() => import(...), { ssr: false })` for canvas/WebSocket components
- **Barrel import pitfall**: Never import canvas components from barrel `@/components/map` — import directly from specific files to avoid SSR module evaluation
- **Map rendering**: Pixi.js for 8000-system universe map, Canvas2D for smaller maps (jump range, Pochven)
- **Auth**: JWT in localStorage, `useAuth()` hook, `isPro` gate for subscription features

## Backend Architecture

```
backend/
├── app/
│   ├── api/v1/       # FastAPI routers (routing, intel, auth, billing, etc.)
│   ├── core/         # Config, security, pagination
│   ├── models/       # Pydantic request/response models
│   └── services/     # Business logic (routing, jump_drive, pochven, intel, etc.)
├── starmap/
│   ├── sde/          # SDE data models + SQLite schema
│   ├── graph/        # Universe graph for pathfinding
│   └── ingest_sde.py # SDE import pipeline
└── data/             # universe.json, risk_config.json
```

### Key Backend Services

- **routing.py**: Dijkstra shortest-path with gate/bridge/Thera/Pochven/wormhole edges
- **jump_drive.py**: Capital ship jump planning — fuel, fatigue, range, cyno-eligible filtering
- **pochven.py**: 27-system Pochven internal gate network (3 Krais, 30 SDE-verified connections)
- **intel.py**: Kill data aggregation, risk scoring, hot systems
- **auth.py**: EVE SSO OAuth2 → JWT token lifecycle

## EVE Domain Rules (Critical)

- **Cyno mechanics**: Cynos can only be lit in lowsec/nullsec (not highsec, WH, or Pochven)
- **Pochven jump drives**: Can jump OUT of Pochven but NOT into it — Pochven systems appear as nullsec (security -1.0) but must be explicitly excluded from cyno destinations
- **Pochven internal gates**: 27 systems in 3 Krais (Perun/Svarog/Veles), connected by conduit gates. Fixed topology, no branches. Cross-Krai borders at 3 junctions.
- **Filaments**: Random destinations — not predictable, don't model as fixed routes
- **Security classes**: highsec (>=0.5), lowsec (0.1-0.4), nullsec (<=0.0)
- **ESI scopes**: Only `read_location` + `write_waypoint` remain valid (CCP deprecated others)

## Common Commands

```bash
# Backend
python3 -m pytest tests/ -v --timeout=30
ruff check backend/ tests/ && ruff format backend/ tests/

# Frontend
cd apps/web && npx next build
cd apps/web && npx next dev

# Deploy
/home/arete/.fly/bin/flyctl deploy --remote-only --wait-timeout 600 --app eve-gatekeeper
cd apps/web && npx vercel --prod
git push origin main  # also triggers Vercel auto-deploy

# Fly secrets
/home/arete/.fly/bin/flyctl secrets set KEY=VALUE --app eve-gatekeeper
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend framework | FastAPI |
| Frontend framework | Next.js 16 (App Router) |
| UI library | React 18 + TailwindCSS 3.4 |
| Map rendering | Pixi.js 7 + Canvas2D |
| Server state | TanStack Query 5 |
| Icons | Lucide React |
| Testing (backend) | pytest |
| Testing (frontend) | Vitest + Playwright |
| Linting | ruff (Python), ESLint (TS) |
| CI/CD | GitHub Actions |
| Containerization | Docker (uvicorn) |

## Coding Standards

- **Python**: snake_case, double quotes, type hints, google-style docstrings, pathlib (not os.path)
- **TypeScript**: strict mode, const/let (no var), proper interfaces (no `any`)
- **Error handling**: Specific exceptions (no bare `except:`), Pydantic response models (no raw dicts)
- **Logging**: `logging` module (no `print()`)
- **Secrets**: Environment variables only (no hardcoded values)
- **Git**: Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)

## Anti-Patterns

- Do NOT import from `@/components/map` barrel in SSR contexts — import specific files
- Do NOT model filament entry/exit as predictable routes — they're random
- Do NOT include Pochven systems in cyno destination candidates
- Do NOT use synchronous database calls in async endpoints
- Do NOT use mutable default arguments in Python
- Do NOT use `latest` tag in Docker — pin specific versions
