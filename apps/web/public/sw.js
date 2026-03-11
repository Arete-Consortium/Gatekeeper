// EVE Gatekeeper Service Worker — offline caching for static assets and API data
const CACHE_VERSION = 'gk-v2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;

// Static assets to precache on install
const PRECACHE_URLS = [
  '/',
  '/map',
  '/route',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

// API endpoints to cache with network-first strategy
// Only cache non-Pro, non-session-dependent endpoints
const CACHEABLE_API_PATTERNS = [
  /\/api\/v1\/map\/config/,
  /\/api\/v1\/map\/market-hubs/,
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch(() => {
        // Don't fail install if some pages aren't available yet
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key.startsWith('gk-') && key !== STATIC_CACHE && key !== API_CACHE)
          .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip WebSocket upgrades
  if (url.protocol === 'ws:' || url.protocol === 'wss:') return;

  // API requests: network-first with cache fallback
  if (CACHEABLE_API_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
    event.respondWith(networkFirstWithCache(request, API_CACHE, 5 * 60 * 1000));
    return;
  }

  // Static assets (JS, CSS, images): cache-first
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirstWithNetwork(request, STATIC_CACHE));
    return;
  }

  // Navigation requests: network-first with cache fallback
  if (request.mode === 'navigate') {
    event.respondWith(networkFirstWithCache(request, STATIC_CACHE, 60 * 60 * 1000));
    return;
  }
});

async function networkFirstWithCache(request, cacheName, maxAge) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    // Return offline fallback for navigation
    if (request.mode === 'navigate') {
      const fallback = await caches.match('/');
      if (fallback) return fallback;
    }
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

async function cacheFirstWithNetwork(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

function isStaticAsset(pathname) {
  return /\.(js|css|png|jpg|jpeg|svg|ico|woff2?|ttf|eot)$/.test(pathname) ||
    pathname.startsWith('/_next/static/');
}
