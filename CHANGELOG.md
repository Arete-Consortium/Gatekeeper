# Changelog

All notable changes to EVE Gatekeeper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- MCP (Model Context Protocol) server for Claude Code integration
  - 9 tools: route, parse_fitting, analyze_fitting, ship_info, system_threat, region_info, jump_range, create_alert, list_alerts
  - Console script entry point: `gatekeeper-mcp`
- Mobile app screens for Fitting Analyzer and Kill Alerts
- Desktop app README with build and development instructions
- Mobile app test infrastructure with Jest and React Native Testing Library (46 tests)
- Desktop app test infrastructure with Jest (29 tests)
- Backend tests for map_visualization service (26 tests)
- Backend tests for fitting service edge cases (35 tests)
- Backend tests for MCP server (28 tests)

### Changed
- Improved test coverage for map_visualization.py (32% -> 99%)
- Improved test coverage for fitting.py (77% -> 98%)
- Improved test coverage for MCP server.py (67% -> 84%)
- Total backend tests: 1604

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

[Unreleased]: https://github.com/AreteDriver/EVE_Gatekeeper/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/AreteDriver/EVE_Gatekeeper/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/AreteDriver/EVE_Gatekeeper/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/AreteDriver/EVE_Gatekeeper/releases/tag/v1.0.0
