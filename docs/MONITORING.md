# EVE Gatekeeper Monitoring Guide

This guide covers setting up monitoring, alerting, and observability for EVE Gatekeeper.

## Table of Contents

- [Metrics Overview](#metrics-overview)
- [Prometheus Setup](#prometheus-setup)
- [Grafana Dashboards](#grafana-dashboards)
- [Alert Rules](#alert-rules)
- [Cache Monitoring](#cache-monitoring)
- [Health Endpoints](#health-endpoints)
- [Troubleshooting](#troubleshooting)

## Metrics Overview

EVE Gatekeeper exposes Prometheus metrics at `/metrics`.

### Available Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, path, status | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, path | Request latency |
| `route_cache_hits_total` | Counter | profile | Route cache hits |
| `route_cache_misses_total` | Counter | profile | Route cache misses |
| `risk_cache_hits_total` | Counter | - | Risk cache hits |
| `risk_cache_misses_total` | Counter | - | Risk cache misses |
| `cache_hits_total` | Counter | cache_type | General cache hits |
| `cache_misses_total` | Counter | cache_type | General cache misses |
| `esi_requests_total` | Counter | endpoint, status | ESI API requests |
| `route_calculations_total` | Counter | profile | Route calculations |
| `risk_calculations_total` | Counter | - | Risk calculations |
| `zkill_events_total` | Counter | event_type | zKillboard events |
| `websocket_connections_active` | Gauge | - | Active WebSocket connections |
| `service_degradation_state` | Gauge | component | Service health (0=healthy, 1=degraded, 2=unhealthy) |
| `eve_gatekeeper_info` | Gauge | version | Application info |

## Prometheus Setup

### Docker Compose Example

```yaml
version: '3.8'

services:
  gatekeeper:
    image: eve-gatekeeper:latest
    ports:
      - "8000:8000"

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts.yml:/etc/prometheus/rules/gatekeeper.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  grafana-data:
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'gatekeeper'
    static_configs:
      - targets: ['gatekeeper:8000']
    metrics_path: /metrics
```

### alertmanager.yml

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@example.com'

route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default'

  routes:
    - match:
        severity: critical
      receiver: 'critical'

receivers:
  - name: 'default'
    email_configs:
      - to: 'ops@example.com'

  - name: 'critical'
    email_configs:
      - to: 'oncall@example.com'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#alerts'
```

## Grafana Dashboards

### Key Panels

#### Request Rate
```
rate(http_requests_total[5m])
```

#### Error Rate
```
sum(rate(http_requests_total{status=~"5.."}[5m])) /
sum(rate(http_requests_total[5m]))
```

#### 95th Percentile Latency
```
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

#### Cache Hit Rate (Routes)
```
sum(rate(route_cache_hits_total[5m])) /
(sum(rate(route_cache_hits_total[5m])) + sum(rate(route_cache_misses_total[5m])))
```

#### Cache Hit Rate (Risk)
```
rate(risk_cache_hits_total[5m]) /
(rate(risk_cache_hits_total[5m]) + rate(risk_cache_misses_total[5m]))
```

#### Route Calculations by Profile
```
sum by (profile) (rate(route_calculations_total[5m]))
```

#### zKillboard Events
```
rate(zkill_events_total[5m])
```

#### WebSocket Connections
```
websocket_connections_active
```

#### Service Health
```
service_degradation_state
```

### Dashboard JSON

A complete Grafana dashboard JSON is available at: `monitoring/grafana-dashboard.json`

Import via: Grafana → Dashboards → Import → Upload JSON file

## Alert Rules

Alert rules are defined in `monitoring/alerts.yml`. Key alerts:

| Alert | Severity | Description |
|-------|----------|-------------|
| HighRouteCacheMissRate | warning | Route cache miss rate > 50% |
| HighRiskCacheMissRate | warning | Risk cache miss rate > 70% |
| CacheMissRateCritical | critical | Overall cache miss rate > 90% |
| APILatencyHigh | warning | 95th percentile > 2s |
| APILatencyCritical | critical | 95th percentile > 5s |
| HighErrorRate | warning | 5xx error rate > 5% |
| ErrorRateCritical | critical | 5xx error rate > 10% |
| ServiceDegraded | warning | Component in degraded state |
| ServiceUnhealthy | critical | Component unhealthy |
| ESIHighErrorRate | warning | ESI errors > 10% |
| ZKillboardDisconnected | warning | No events for 15 minutes |

### Tuning Alert Thresholds

Adjust thresholds based on your traffic patterns:

```yaml
# For high-traffic deployments, increase thresholds
- alert: HighRequestRate
  expr: rate(http_requests_total[1m]) > 5000  # Increased from 1000
```

```yaml
# For stricter SLAs, lower latency thresholds
- alert: APILatencyHigh
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
```

## Cache Monitoring

### Cache Stats Endpoint

```bash
curl http://localhost:8000/api/v1/status/cache/stats
```

Response:
```json
{
  "cache_type": "memory",
  "hits": 1234,
  "misses": 56,
  "total_requests": 1290,
  "hit_ratio": 0.9566,
  "hit_percentage": 95.66,
  "entries": 789
}
```

### Cache Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Route cache hit rate | > 80% | < 50% |
| Risk cache hit rate | > 60% | < 30% |
| Overall hit rate | > 70% | < 50% |

### Cache Sizing

Memory cache default: 10,000 entries

Estimate cache size needs:
- Route entries: ~500 bytes per entry
- Risk entries: ~200 bytes per entry
- 10,000 entries ≈ 5-10 MB RAM

For Redis, configure maxmemory:
```
redis-cli CONFIG SET maxmemory 100mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Health Endpoints

### Basic Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

### Detailed Status

```bash
curl http://localhost:8000/api/v1/status/
```

Response:
```json
{
  "status": "operational",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "uptime_formatted": "1d 0h 0m 0s",
  "checks": {
    "database": "ok",
    "cache": "redis",
    "systems_loaded": 7600
  },
  "features": {
    "rate_limiting": true,
    "api_key_auth": false,
    "metrics": true
  }
}
```

### WebSocket Health

```bash
curl http://localhost:8000/api/v1/status/websocket-health
```

Response:
```json
{
  "zkill_listener": {
    "connected": true,
    "uptime_seconds": 3600,
    "events_received": 150,
    "last_event": "2026-01-01T12:00:00Z"
  },
  "client_connections": {
    "active": 5,
    "total_connected": 120,
    "total_messages": 15000
  }
}
```

## Troubleshooting

### High Cache Miss Rate

**Symptoms:**
- `route_cache_misses_total` increasing faster than hits
- API latency increasing

**Causes:**
- Cache TTL too short
- Too many unique route queries
- Cache not persisting (Redis disconnected)

**Solutions:**
1. Check cache status: `GET /api/v1/status/cache/stats`
2. Increase cache TTL in settings
3. Check Redis connectivity
4. Analyze query patterns for optimization

### High API Latency

**Symptoms:**
- `http_request_duration_seconds` p95 > 2s
- Users report slow responses

**Causes:**
- Cache misses (forcing computation)
- Database slowness
- zKillboard API delays

**Solutions:**
1. Check cache hit rates
2. Enable caching if not already enabled
3. Check external service health (ESI, zKillboard)
4. Scale horizontally if load is high

### zKillboard Disconnections

**Symptoms:**
- `zkill_events_total` stops increasing
- WebSocket health shows disconnected

**Causes:**
- zKillboard WebSocket server issues
- Network connectivity problems
- Rate limiting by zKillboard

**Solutions:**
1. Check zKillboard status: https://zkillboard.com/
2. Verify outbound connectivity
3. Check for rate limiting (reduce reconnection frequency)

### Service Degradation

**Symptoms:**
- `service_degradation_state{component="X"} == 1` or `2`

**Actions by Component:**

| Component | Degraded | Unhealthy |
|-----------|----------|-----------|
| database | Retry connection, check DB health | Fail open or maintenance mode |
| cache | Fall back to memory cache | Accept higher latency |
| zkill | Log warning, stale risk data | Historical data only |
| esi | Rate limit ESI calls | Use cached ESI data |

### Prometheus Scrape Failures

**Symptoms:**
- Missing metrics in Prometheus
- `up{job="gatekeeper"} == 0`

**Solutions:**
1. Verify `/metrics` endpoint responds
2. Check network connectivity
3. Verify Prometheus scrape config
4. Check for rate limiting on metrics endpoint

## Recommended SLOs

| Metric | SLO | Error Budget |
|--------|-----|--------------|
| Availability | 99.9% | 8.7 hours/year |
| Latency (p95) | < 500ms | - |
| Error rate | < 0.1% | - |
| Route cache hit | > 80% | - |

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [AlertManager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [SRE Workbook: Alerting](https://sre.google/workbook/alerting-on-slos/)
