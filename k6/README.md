# k6 Load Tests — EVE Gatekeeper API

## Install k6

```bash
# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D68
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# macOS
brew install k6

# Docker
docker pull grafana/k6
```

## Test Scripts

| Script | VUs | Duration | Purpose |
|--------|-----|----------|---------|
| `smoke-test.js` | 1 | 30s | Quick sanity check — all endpoints return expected status codes. Good for CI. |
| `load-test.js` | 1-50 | 3min | Standard load test with per-endpoint latency tracking and thresholds. |
| `stress-test.js` | 1-200 | 10min | Find breaking points under heavy load with weighted request distribution. |

## Run Against Local

```bash
k6 run --env BASE_URL=http://localhost:8000 k6/smoke-test.js
k6 run --env BASE_URL=http://localhost:8000 k6/load-test.js
k6 run --env BASE_URL=http://localhost:8000 k6/stress-test.js
```

## Run Against Production

```bash
k6 run --env BASE_URL=https://eve-gatekeeper.fly.dev k6/smoke-test.js
k6 run --env BASE_URL=https://eve-gatekeeper.fly.dev k6/load-test.js
k6 run --env BASE_URL=https://eve-gatekeeper.fly.dev k6/stress-test.js
```

## Run with Docker

```bash
docker run --rm -i grafana/k6 run --env BASE_URL=https://eve-gatekeeper.fly.dev - < k6/load-test.js
```

## Endpoints Tested

### Lightweight (fast, no external calls)
- `GET /health` — Health check
- `GET /api/v1/status/` — API status with uptime and component health
- `GET /api/v1/status/version` — Version info
- `GET /api/v1/status/kills` — Recent kill history
- `GET /api/v1/map/colors/security` — Security color legend
- `GET /systems/{name}/risk` — Per-system risk score
- `GET /systems/{name}/neighbors` — Adjacent systems
- `GET /systems/` — Full system list

### Heavyweight (universe data or ESI proxy)
- `GET /map/config` — Full universe map config (5400+ systems + risk calc)
- `GET /map/sovereignty` — Proxies ESI sovereignty data
- `GET /map/thera` — Proxies EVE Scout Thera connections
- `GET /map/fw` — Proxies ESI faction warfare data
- `GET /map/activity` — Proxies ESI jumps + kills + incursions
- `GET /map/sovereignty/structures` — Proxies ESI sov structures
- `GET /api/v1/map/market-hubs` — Trade hub data with ESI order counts
- `GET /api/v1/map/region/{name}` — Region map visualization

## Thresholds

### Load Test
- `http_req_duration` p95 < 500ms, p99 < 1000ms
- Error rate < 1%
- Per-endpoint p95 thresholds (health < 200ms, map config < 2s, ESI proxies < 3s)

### Stress Test
- `http_req_duration` p95 < 2000ms, p99 < 5000ms
- Error rate < 5% (relaxed for stress conditions)

## Notes

- ESI-proxied endpoints (`/map/sovereignty`, `/map/thera`, `/map/fw`) may return 503 if CCP/EVE Scout APIs are down. This is expected and not counted as an error in the tests.
- `/map/config` is the heaviest endpoint — it computes risk scores for all 5400+ systems. Watch its latency closely.
- The stress test uses weighted random request distribution to simulate realistic traffic patterns.
