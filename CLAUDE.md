# CLAUDE.md — EVE_Gatekeeper

## Project Overview

EVE Online navigation, routing, and intel visualization platform

## Current State

- **Version**: 1.5.0
- **Language**: Python, TypeScript
- **Tests**: 2,157+ backend passing
- **Deployment**: Fly.io (backend) + Vercel (frontend)
- **Domain**: gatekeeper.aretedriver.dev (frontend), eve-gatekeeper.fly.dev (API)
- **Database**: PostgreSQL on Fly.io

## Key Features (Live)

- **New Eden Map**: Canvas2D interactive universe map with 8,000+ systems
  - Kill stream via backend WebSocket (/ws/killfeed) with zKillboard fallback
  - Route planning with context menu (origin/destination/avoid)
  - System detail panel, search, Thera wormhole overlay (EVE Scout)
  - Sovereignty, faction warfare, landmark overlays
  - URL permalinks, keyboard shortcuts, mobile sidebar
- **Route Planning**: Multi-profile (safer/shortest/paranoid), jump bridges, Thera, Pochven
- **Intel Feed**: Real-time kill data, risk heatmap, hot systems
- **Fitting Analyzer**: EFT paste → travel advice
- **Auth**: EVE SSO OAuth2 → JWT (scopes: read_location, write_waypoint)
- **Billing**: Stripe checkout (Pro $3/mo), billing portal, webhook lifecycle
- **Error Monitoring**: React ErrorBoundary → POST /api/v1/errors
- **Analytics**: Page view tracking → POST /api/v1/analytics/pageview

## Architecture

```
EVE_Gatekeeper/
├── .github/
│   └── workflows/
├── apps/
│   ├── desktop/
│   ├── mobile/
│   └── web/
├── assets/
├── backend/
│   ├── app/
│   ├── data/
│   └── starmap/
├── docs/
├── examples/
├── helm/
│   └── eve-gatekeeper/
├── k8s/
├── monitoring/
├── scripts/
├── streamlit/
│   └── modules/
├── tests/
│   ├── factories/
│   ├── integration/
│   └── unit/
├── .dockerignore
├── .env.example
├── .gitignore
├── .gitleaks.toml
├── .gitleaksignore
├── .pre-commit-config.yaml
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── Dockerfile
├── LICENSE
├── README.md
├── ROADMAP.md
├── SECURITY.md
├── SETUP.md
├── docker-compose.dev.yml
├── docker-compose.yml
├── pyproject.toml
├── requirements-dev.txt
├── version.json
```

## Tech Stack

- **Language**: Python, TypeScript, HTML, JavaScript, CSS
- **Framework**: fastapi
- **Linters**: ruff
- **Formatters**: ruff
- **Type Checkers**: mypy
- **Test Frameworks**: pytest
- **Runtime**: Docker
- **CI/CD**: GitHub Actions

## Coding Standards

- **Naming**: snake_case
- **Quote Style**: double quotes
- **Type Hints**: present
- **Docstrings**: google style
- **Imports**: mixed
- **Path Handling**: pathlib
- **Line Length (p95)**: 78 characters
- **Error Handling**: Custom exception classes present

## Common Commands

```bash
# backend tests
python3 -m pytest tests/ -v --timeout=30
# frontend build
cd apps/web && npx next build
# lint
ruff check backend/ tests/
# format
ruff format backend/ tests/
# deploy backend
/home/arete/.fly/bin/flyctl deploy --remote-only --wait-timeout 600 --app eve-gatekeeper
# fly secrets
/home/arete/.fly/bin/flyctl secrets set KEY=VALUE --app eve-gatekeeper
# docker CMD
["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## ESI OAuth Scopes (Active)

```python
DEFAULT_SCOPES = [
    "esi-location.read_location.v1",
    "esi-ui.write_waypoint.v1",
]
# DEPRECATED (removed): read_online, read_standings, search_structures
```

## Anti-Patterns (Do NOT Do)

- Do NOT commit secrets, API keys, or credentials
- Do NOT skip writing tests for new code
- Do NOT use synchronous database calls in async endpoints
- Do NOT return raw dicts — use Pydantic response models
- Do NOT use `os.path` — use `pathlib.Path` everywhere
- Do NOT use bare `except:` — catch specific exceptions
- Do NOT use mutable default arguments
- Do NOT use `print()` for logging — use the `logging` module
- Do NOT hardcode secrets in Dockerfiles — use environment variables
- Do NOT use `latest` tag — pin specific versions
- Do NOT use `any` type — define proper type interfaces
- Do NOT use `var` — use `const` or `let`

## Dependencies

### Core
- fastapi

### Dev
- pytest
- ruff

## Domain Context

### Key Models/Classes
- `AIService`
- `ActiveCharacterManager`
- `ActiveCharacterResponse`
- `AddRouteRequest`
- `AddWaypointRequest`
- `AlertPreferences`
- `AllIntelResponse`
- `AllianceLinksResponse`
- `AlternativeRoute`
- `AnalyzeFittingResponse`
- `AsyncGatekeeperClient`
- `AuthStatus`
- `AuthenticatedCharacter`
- `AvailableToolsResponse`
- `AvoidanceConfig`

### Domain Terms
- Available Tools
- Aware Routing
- CCP
- CD
- CHANGELOG
- CI
- Capital Jump Planning
- Changelog See
- Claude Code
- Claude Code Configuration Add

### API Endpoints
- `/`
- `/active`
- `/all`
- `/alliance/{alliance_id}`
- `/analyze`
- `/analyze-route`
- `/bulk`
- `/cache/stats`
- `/calculate`
- `/callback`
- `/categories`
- `/character/{character_id}`
- `/character/{character_id}/jump`
- `/characters`
- `/colors/security`

### Enums/Constants
- `A239`
- `ACTIVE`
- `API_VERSION`
- `B274`
- `BASE_URL`
- `BLOPS`
- `BLOPS_FITTING`
- `BOOKMARK`
- `BUBBLE_IMMUNE_FITTING`
- `C125`

### Outstanding Items
- **NOTE**: This file should not be edited (`apps/web/next-env.d.ts`)

## Git Conventions

- Commit messages: Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- Branch naming: `feat/description`, `fix/description`
- Run tests before committing
