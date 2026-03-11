import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const healthDuration = new Trend("health_duration", true);
const statusDuration = new Trend("status_duration", true);
const mapConfigDuration = new Trend("map_config_duration", true);
const sovDuration = new Trend("sovereignty_duration", true);
const theraDuration = new Trend("thera_duration", true);
const fwDuration = new Trend("fw_duration", true);
const marketHubsDuration = new Trend("market_hubs_duration", true);
const systemRiskDuration = new Trend("system_risk_duration", true);

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  stages: [
    { duration: "30s", target: 50 },  // ramp up to 50 VUs
    { duration: "2m", target: 50 },   // hold at 50 VUs
    { duration: "30s", target: 0 },   // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    errors: ["rate<0.01"],
    health_duration: ["p(95)<200"],
    status_duration: ["p(95)<500"],
    map_config_duration: ["p(95)<2000"],  // heavy endpoint — universe + risk calc
    sovereignty_duration: ["p(95)<3000"], // proxies to ESI
    thera_duration: ["p(95)<3000"],       // proxies to EVE Scout
    fw_duration: ["p(95)<3000"],          // proxies to ESI
    market_hubs_duration: ["p(95)<2000"],
    system_risk_duration: ["p(95)<500"],
  },
};

// Well-known system names for parameterized requests
const SYSTEMS = ["Jita", "Amarr", "Dodixie", "Rens", "Hek", "Perimeter", "Uedama", "Niarja"];

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

export default function () {
  // -------------------------------------------------------------------------
  // Health & Status
  // -------------------------------------------------------------------------
  group("health", () => {
    const res = http.get(`${BASE_URL}/health`);
    healthDuration.add(res.timings.duration);
    const ok = check(res, {
      "health status 200": (r) => r.status === 200,
      "health body has status": (r) => {
        try { return JSON.parse(r.body).status !== undefined; } catch { return false; }
      },
    });
    errorRate.add(!ok);
  });

  group("api-status", () => {
    const res = http.get(`${BASE_URL}/api/v1/status/`);
    statusDuration.add(res.timings.duration);
    const ok = check(res, {
      "status 200": (r) => r.status === 200,
      "status operational": (r) => {
        try { return JSON.parse(r.body).status === "operational"; } catch { return false; }
      },
    });
    errorRate.add(!ok);
  });

  sleep(0.5);

  // -------------------------------------------------------------------------
  // Map endpoints (legacy /map/ prefix)
  // -------------------------------------------------------------------------
  group("map-config", () => {
    const res = http.get(`${BASE_URL}/map/config`);
    mapConfigDuration.add(res.timings.duration);
    const ok = check(res, {
      "map config 200": (r) => r.status === 200,
      "map config has systems": (r) => {
        try { return Object.keys(JSON.parse(r.body).systems).length > 0; } catch { return false; }
      },
    });
    errorRate.add(!ok);
  });

  sleep(0.3);

  group("sovereignty", () => {
    const res = http.get(`${BASE_URL}/map/sovereignty`);
    sovDuration.add(res.timings.duration);
    const ok = check(res, {
      "sovereignty 200 or 503": (r) => r.status === 200 || r.status === 503,
    });
    errorRate.add(res.status !== 200 && res.status !== 503);
  });

  group("thera", () => {
    const res = http.get(`${BASE_URL}/map/thera`);
    theraDuration.add(res.timings.duration);
    const ok = check(res, {
      "thera 200 or 503": (r) => r.status === 200 || r.status === 503,
    });
    errorRate.add(res.status !== 200 && res.status !== 503);
  });

  group("fw", () => {
    const res = http.get(`${BASE_URL}/map/fw`);
    fwDuration.add(res.timings.duration);
    const ok = check(res, {
      "fw 200 or 503": (r) => r.status === 200 || r.status === 503,
    });
    errorRate.add(res.status !== 200 && res.status !== 503);
  });

  sleep(0.3);

  // -------------------------------------------------------------------------
  // Map v1 endpoints (/api/v1/map/)
  // -------------------------------------------------------------------------
  group("market-hubs", () => {
    const res = http.get(`${BASE_URL}/api/v1/map/market-hubs`);
    marketHubsDuration.add(res.timings.duration);
    const ok = check(res, {
      "market hubs 200": (r) => r.status === 200,
      "market hubs has data": (r) => {
        try { return JSON.parse(r.body).hubs.length > 0; } catch { return false; }
      },
    });
    errorRate.add(!ok);
  });

  // -------------------------------------------------------------------------
  // Systems
  // -------------------------------------------------------------------------
  group("system-risk", () => {
    const system = pickRandom(SYSTEMS);
    const res = http.get(`${BASE_URL}/systems/${system}/risk`);
    systemRiskDuration.add(res.timings.duration);
    const ok = check(res, {
      "risk 200": (r) => r.status === 200,
      "risk has score": (r) => {
        try { return JSON.parse(r.body).score !== undefined; } catch { return false; }
      },
    });
    errorRate.add(!ok);
  });

  sleep(0.5);
}
