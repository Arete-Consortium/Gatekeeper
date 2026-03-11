import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  vus: 1,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
  },
};

export default function () {
  // Health check
  let res = http.get(`${BASE_URL}/health`);
  check(res, { "GET /health -> 200": (r) => r.status === 200 });

  // API status
  res = http.get(`${BASE_URL}/api/v1/status/`);
  check(res, { "GET /api/v1/status/ -> 200": (r) => r.status === 200 });

  // Map config (heavy — full universe data)
  res = http.get(`${BASE_URL}/map/config`);
  check(res, { "GET /map/config -> 200": (r) => r.status === 200 });

  // Sovereignty (proxies ESI — 503 acceptable if ESI is down)
  res = http.get(`${BASE_URL}/map/sovereignty`);
  check(res, { "GET /map/sovereignty -> 200|503": (r) => r.status === 200 || r.status === 503 });

  // Thera connections (proxies EVE Scout)
  res = http.get(`${BASE_URL}/map/thera`);
  check(res, { "GET /map/thera -> 200|503": (r) => r.status === 200 || r.status === 503 });

  // Faction warfare
  res = http.get(`${BASE_URL}/map/fw`);
  check(res, { "GET /map/fw -> 200|503": (r) => r.status === 200 || r.status === 503 });

  // Activity (jumps + kills + incursions)
  res = http.get(`${BASE_URL}/map/activity`);
  check(res, { "GET /map/activity -> 200|503": (r) => r.status === 200 || r.status === 503 });

  // Market hubs
  res = http.get(`${BASE_URL}/api/v1/map/market-hubs`);
  check(res, { "GET /api/v1/map/market-hubs -> 200": (r) => r.status === 200 });

  // System risk (known system)
  res = http.get(`${BASE_URL}/systems/Jita/risk`);
  check(res, { "GET /systems/Jita/risk -> 200": (r) => r.status === 200 });

  // System neighbors
  res = http.get(`${BASE_URL}/systems/Jita/neighbors`);
  check(res, { "GET /systems/Jita/neighbors -> 200": (r) => r.status === 200 });

  // Systems list
  res = http.get(`${BASE_URL}/systems/`);
  check(res, { "GET /systems/ -> 200": (r) => r.status === 200 });

  // Sov structures
  res = http.get(`${BASE_URL}/map/sovereignty/structures`);
  check(res, { "GET /map/sovereignty/structures -> 200|503": (r) => r.status === 200 || r.status === 503 });

  // Map v1: region map
  res = http.get(`${BASE_URL}/api/v1/map/region/The Forge`);
  check(res, { "GET /api/v1/map/region/The Forge -> 200": (r) => r.status === 200 });

  // Map v1: security colors
  res = http.get(`${BASE_URL}/api/v1/map/colors/security`);
  check(res, { "GET /api/v1/map/colors/security -> 200": (r) => r.status === 200 });

  // Status: version
  res = http.get(`${BASE_URL}/api/v1/status/version`);
  check(res, { "GET /api/v1/status/version -> 200": (r) => r.status === 200 });

  // Status: recent kills
  res = http.get(`${BASE_URL}/api/v1/status/kills?limit=10`);
  check(res, { "GET /api/v1/status/kills -> 200": (r) => r.status === 200 });

  sleep(1);
}
