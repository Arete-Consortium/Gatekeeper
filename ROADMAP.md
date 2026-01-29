# EVE Gatekeeper Roadmap

This document tracks planned tasks and improvements for the EVE Gatekeeper project.

## High Priority

### MCP Server
- [ ] Integration testing - End-to-end tests for all 9 tools
- [ ] Add error handling for edge cases

### Security
- [x] Enforce SECRET_KEY validation in production mode
- [x] Review and tighten CORS configuration for production

## Completed

### Mobile App
- [x] Complete FittingScreen functionality
- [x] Complete AlertsScreen functionality
- [x] Integrate screens with backend APIs
- [x] Add offline capabilities

### Desktop App
- [x] Add system tray support
- [x] Add native notifications
- [x] Complete menu system

### Critical Fixes
- [x] zkill_client.py - Real zKillboard HTTP integration implemented

## Medium Priority

### API Documentation
- [ ] Add real-world usage examples
- [ ] Create sample client implementations

### Authentication & Authorization
- [ ] Implement proper JWT token management
- [ ] Add per-user rate limiting

### Performance
- [ ] Implement query result caching strategies
- [ ] Add WebSocket reconnection logic
- [ ] Add pagination for large result sets

### Monitoring & Observability
- [ ] Fix ESI connectivity check (currently returns 'unknown')
- [ ] Implement actual Redis connectivity check
- [ ] Expand logging coverage
- [ ] Add alerting for service degradation
- [ ] Add cache hit/miss rate metrics

### Logging
- [ ] Replace print() with structured logging in ingest_sde.py

### Configuration
- [ ] Make ESI concurrency limit configurable via env var
- [ ] Make ESI timeout configurable via env var
- [ ] Make WebSocket reconnect delays configurable

### Data Management
- [ ] Implement periodic universe data refresh from ESI
- [ ] Add kill data aging strategy

## Lower Priority

### Cache Improvements
- [ ] Implement file modification time checking for invalidation
- [ ] Add Redis pub/sub for multi-instance deployments

### Visualization
- [ ] Add interactive map to web/desktop
- [ ] Real-time map updates via WebSocket

### New Features
- [ ] Add wormhole routing support
- [ ] Add multi-character support
- [ ] Collaborative routing sessions

### Dependencies
- [ ] Update deprecated npm packages in desktop app
- [ ] Update deprecated npm packages in mobile app

### Operations
- [ ] Create Kubernetes deployment configs

---

## Task Summary

| Category | Open | Done |
|----------|------|------|
| MCP Server | 2 | 0 |
| Mobile App | 0 | 4 |
| Desktop App | 0 | 3 |
| Security | 0 | 2 |
| Critical Fixes | 0 | 1 |
| API Docs | 2 | 0 |
| Auth | 2 | 0 |
| Performance | 3 | 0 |
| Monitoring | 5 | 0 |
| Logging | 1 | 0 |
| Config | 3 | 0 |
| Data | 2 | 0 |
| Cache | 2 | 0 |
| Visualization | 2 | 0 |
| Features | 3 | 0 |
| Dependencies | 2 | 0 |
| Ops | 1 | 0 |
| **Total** | **30** | **10** |

---

## Notes

### Discovered Issues

1. ~~**zkill_client.py stub**: `fetch_system_stats()` at line 4-10 returns empty `ZKillStats()` - needs real HTTP implementation~~ **FIXED**
2. ~~**SECRET_KEY**: Hardcoded default "change-me-in-production" in `backend/app/core/config.py:61`~~ **FIXED** - Validation added
3. ~~**CORS**: `allow_credentials=True` + `allow_methods=["*"]` may be overly permissive in `backend/app/main.py:60-63`~~ **FIXED** - Explicit methods/headers
4. ~~**ESI status**: Health check returns "unknown" - `backend/app/main.py:159-161`~~ **FIXED** - Actual HTTP check
5. ~~**Redis check**: Only verifies config exists, not actual connectivity - `backend/app/api/v1/status.py:51-55`~~ **FIXED** - Uses ping()
6. **Print statements**: ~30+ instances in `backend/starmap/ingest_sde.py` should use structured logging

### References

- Architecture details: See `ARCHITECTURE.md`
- Setup instructions: See `SETUP.md`
- Recent changes: See `CHANGELOG.md`
