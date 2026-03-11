import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const errorRate = new Rate("errors");
const mapConfigDuration = new Trend("map_config_duration", true);

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  stages: [
    { duration: "1m", target: 50 },   // warm up
    { duration: "2m", target: 100 },   // ramp to 100
    { duration: "2m", target: 200 },   // ramp to 200 — find breaking point
    { duration: "3m", target: 200 },   // hold at peak
    { duration: "2m", target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<5000"],
    errors: ["rate<0.05"],  // 5% error budget under stress
  },
};

const SYSTEMS = [
  "Jita", "Amarr", "Dodixie", "Rens", "Hek",
  "Perimeter", "Uedama", "Tama", "Amamake", "HED-GP",
  "EC-P8R", "M-OEE8", "BWF-ZZ", "CCP-US", "X47L-Q",
];

function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

export default function () {
  // Mix of lightweight and heavyweight requests to simulate real traffic.
  // Weights approximate real usage: health/status checks are frequent,
  // map config is loaded once per session, risk lookups happen per-click.

  const roll = Math.random();

  if (roll < 0.25) {
    // 25% — lightweight health/status
    group("health-status", () => {
      const res = http.get(`${BASE_URL}/health`);
      const ok = check(res, { "health 200": (r) => r.status === 200 });
      errorRate.add(!ok);

      const res2 = http.get(`${BASE_URL}/api/v1/status/`);
      const ok2 = check(res2, { "status 200": (r) => r.status === 200 });
      errorRate.add(!ok2);
    });
  } else if (roll < 0.40) {
    // 15% — map config (heaviest endpoint)
    group("map-config", () => {
      const res = http.get(`${BASE_URL}/map/config`);
      mapConfigDuration.add(res.timings.duration);
      const ok = check(res, { "map config 200": (r) => r.status === 200 });
      errorRate.add(!ok);
    });
  } else if (roll < 0.55) {
    // 15% — ESI-proxied endpoints (sov, thera, fw)
    group("esi-proxy", () => {
      const endpoints = ["/map/sovereignty", "/map/thera", "/map/fw"];
      const endpoint = pickRandom(endpoints);
      const res = http.get(`${BASE_URL}${endpoint}`);
      const ok = check(res, {
        "esi proxy 200|503": (r) => r.status === 200 || r.status === 503,
      });
      // 503 from ESI being down is not our error
      errorRate.add(res.status !== 200 && res.status !== 503);
    });
  } else if (roll < 0.75) {
    // 20% — system risk lookups
    group("system-risk", () => {
      const system = pickRandom(SYSTEMS);
      const res = http.get(`${BASE_URL}/systems/${system}/risk`);
      const ok = check(res, {
        "risk 200|404": (r) => r.status === 200 || r.status === 404,
      });
      errorRate.add(res.status !== 200 && res.status !== 404);
    });
  } else if (roll < 0.85) {
    // 10% — market hubs
    group("market-hubs", () => {
      const res = http.get(`${BASE_URL}/api/v1/map/market-hubs`);
      const ok = check(res, { "market hubs 200": (r) => r.status === 200 });
      errorRate.add(!ok);
    });
  } else if (roll < 0.95) {
    // 10% — system neighbors
    group("system-neighbors", () => {
      const system = pickRandom(SYSTEMS);
      const res = http.get(`${BASE_URL}/systems/${system}/neighbors`);
      const ok = check(res, {
        "neighbors 200|404": (r) => r.status === 200 || r.status === 404,
      });
      errorRate.add(res.status !== 200 && res.status !== 404);
    });
  } else {
    // 5% — activity data
    group("activity", () => {
      const res = http.get(`${BASE_URL}/map/activity`);
      const ok = check(res, {
        "activity 200|503": (r) => r.status === 200 || r.status === 503,
      });
      errorRate.add(res.status !== 200 && res.status !== 503);
    });
  }

  sleep(0.3 + Math.random() * 0.7); // 300ms-1s between requests
}
