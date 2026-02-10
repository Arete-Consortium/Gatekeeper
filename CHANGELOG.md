# Changelog

All notable changes to EVE Gatekeeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] - 2026-02-09

### Added
- **Web Frontend** - Complete React/Next.js web application
  - PixiJS WebGL map renderer with minimap and region labels
  - Playwright E2E test suite and vitest unit tests
  - React performance optimizations
  - CI/CD workflow for web frontend
- **Routing Enhancements**
  - Thera wormhole routing via EVE-Scout API
  - Pochven filament routing (27 systems)
  - Multi-stop waypoint routing with TSP optimization
  - Named avoidance lists with CRUD and persistence
- **MCP Server** - Thera connection and status tools registered
- **Security** - SECRET_KEY production validation, hardened CORS, CodeQL scanning
- **Infrastructure**
  - Per-user rate limiting (character_id for authenticated, IP for anonymous)
  - WebSocket reconnection logic
  - Structured logging in ingest_sde.py (replaced print statements)
  - Actual Redis and ESI connectivity health checks
  - MCP error handling, pagination, and expanded logging
  - JWT token management improvements
  - Configurable ESI concurrency/timeout and WebSocket reconnect delays
- **Mobile** - Bridge and Thera toggle switches, API endpoint sync
- **Desktop** - Production features and offline support
- **Website** - Version endpoint and version.json
- Comprehensive backend and app test suites
- ROADMAP.md with all 40 tasks completed

### Changed
- Total backend tests: 2099
- Improved test coverage for map_visualization.py (32% -> 99%)
- Improved test coverage for fitting.py (77% -> 98%)
- Improved test coverage for MCP server.py (67% -> 84%)

### Fixed
- Pydantic `json_str` field name vs alias in model construction
- Mypy type errors across multiple modules
- Route cache key for wormholes parameter
- Abstract `get_stats` added to CacheService
- Mobile netinfo downgraded to existing v11.4.x
- FastAPI Request type annotation compatibility
- IPv4 Docker health checks for web frontend
- Security vulnerabilities in web frontend dependencies

### Security
- Added CodeQL automated security scanning (weekly)
- Dependency bumps: tar, @isaacs/brace-expansion

## [1.2.0] - 2025-01-25

### Added
- **Alerts API** - Kill alert subscriptions with Discord/Slack webhooks
- **Fitting API** - EFT format parser with travel recommendations
- **Map Visualization API** - Region maps, jump ranges, nearby intel
- **Jump Bridges** - ESI structure discovery and route comparison
- **Bridge Management** - Individual bridge CRUD and statistics
- **Bridge Validation** - Bulk operations for bridge networks

### Changed
- Improved test coverage to 1500+ tests

### Fixed
- Mypy type errors resolved
- Mock setup for nearby intel tests
- Lint cleanup (unused imports, B904 exception chaining)

## [1.1.0] - 2025-01-15

### Added
- **Production Infrastructure**
  - Structured logging with JSON output
  - Prometheus metrics endpoint
  - CI/CD pipelines with GitHub Actions
  - Pre-commit hooks for code quality
- **Real-time Features**
  - WebSocket kill feed from zKillboard
  - Caching layer (Redis/memory)
  - Database support (SQLite/PostgreSQL)
- **Security & Performance**
  - API v1 versioning
  - Rate limiting middleware
  - Security headers
- **Deployment**
  - Production Docker configuration
  - Comprehensive environment configuration

### Changed
- API structure reorganized under `/api/v1/`

## [1.0.0] - 2025-01-01

### Added
- **Core Routing**
  - Risk-aware pathfinding with Dijkstra algorithm
  - Route profiles: shortest, safer, paranoid
  - Ship-type risk profiles (hauler, frigate, capital, cloaky, etc.)
  - System avoidance support
- **Universe Data**
  - Full EVE SDE integration
  - Region and constellation data
  - Security status calculations
- **Capital Ships**
  - Jump freighter route planner
  - Jump range calculations
  - Ansiblex jump bridge support
- **zKillboard Integration**
  - Dynamic risk scoring
  - Real-time kill data
- **Additional Features**
  - Route bookmarks API
  - Route history tracking
  - Discord/Slack webhook alerts
  - Route sharing and export
  - System notes for annotations
  - Intel channel parser
  - Jump fatigue calculator
  - AI-powered route danger analysis
  - ESI OAuth2 authentication
  - Character waypoint management

### Security
- Fixed Electron ASAR integrity bypass vulnerability

[Unreleased]: https://github.com/AreteDriver/EVE_Gatekeeper/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/AreteDriver/EVE_Gatekeeper/compare/v1.3.0...v1.4.0
[1.2.0]: https://github.com/AreteDriver/EVE_Gatekeeper/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/AreteDriver/EVE_Gatekeeper/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/AreteDriver/EVE_Gatekeeper/releases/tag/v1.0.0
