# CLAUDE.md — EVE_Gatekeeper

## Project Overview

EVE Online navigation, routing, and intel visualization platform

## Current State

- **Version**: 1.4.0
- **Language**: Python
- **Files**: 492 across 5 languages
- **Lines**: 132,312

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
# test
pytest tests/ -v
# lint
ruff check src/ tests/
# format
ruff format src/ tests/
# type check
mypy src/
# coverage
pytest --cov=src/ tests/
# gatekeeper-mcp
backend.app.mcp.server:main

# docker CMD
["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
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
