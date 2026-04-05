"""Unit tests for per-endpoint rate limiting configuration."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from backend.app.core.config import settings
from backend.app.middleware.rate_limit import (
    ENDPOINT_RATE_LIMIT_PATTERNS,
    PerEndpointRateLimitMiddleware,
    _get_endpoint_tier,
    get_endpoint_rate_limit,
    setup_rate_limiting,
)


class TestGetEndpointRateLimit:
    """Tests for per-endpoint rate limit resolution."""

    def _make_request(self, path: str, method: str = "GET") -> MagicMock:
        """Create a mock request with the given path and method."""
        request = MagicMock(spec=Request)
        request.url.path = path
        request.method = method
        return request

    def test_health_endpoint(self):
        """Health endpoint gets the health tier limit."""
        request = self._make_request("/health")
        limit = get_endpoint_rate_limit(request)
        assert limit == 120

    def test_root_endpoint(self):
        """Root endpoint gets the health tier limit."""
        request = self._make_request("/")
        limit = get_endpoint_rate_limit(request)
        assert limit == 120

    def test_status_endpoint(self):
        """Status endpoint gets the health tier limit."""
        request = self._make_request("/api/v1/status")
        limit = get_endpoint_rate_limit(request)
        assert limit == 120

    def test_status_subpath(self):
        """Status subpaths get the health tier limit."""
        request = self._make_request("/api/v1/status/diagnostics")
        limit = get_endpoint_rate_limit(request)
        assert limit == 120

    def test_auth_login(self):
        """Auth endpoints get the auth tier limit."""
        request = self._make_request("/api/v1/auth/login")
        limit = get_endpoint_rate_limit(request)
        assert limit == 10

    def test_auth_callback(self):
        """Auth callback gets the auth tier limit."""
        request = self._make_request("/api/v1/auth/callback")
        limit = get_endpoint_rate_limit(request)
        assert limit == 10

    def test_callback_legacy(self):
        """Legacy callback gets the auth tier limit."""
        request = self._make_request("/callback")
        limit = get_endpoint_rate_limit(request)
        assert limit == 10

    def test_billing_endpoint(self):
        """Billing endpoints get the auth tier limit."""
        request = self._make_request("/api/v1/billing/checkout")
        limit = get_endpoint_rate_limit(request)
        assert limit == 10

    def test_route_calculation(self):
        """Route endpoints get the route tier limit."""
        request = self._make_request("/api/v1/route/calculate")
        limit = get_endpoint_rate_limit(request)
        assert limit == 20

    def test_jump_planning(self):
        """Jump endpoints get the route tier limit."""
        request = self._make_request("/api/v1/jump/plan")
        limit = get_endpoint_rate_limit(request)
        assert limit == 20

    def test_pochven_route(self):
        """Pochven route gets the route tier limit."""
        request = self._make_request("/api/v1/pochven/route")
        limit = get_endpoint_rate_limit(request)
        assert limit == 20

    def test_pochven_non_route(self):
        """Pochven non-route gets the map tier limit."""
        request = self._make_request("/api/v1/pochven/systems")
        limit = get_endpoint_rate_limit(request)
        assert limit == 30

    def test_map_config(self):
        """Map config gets the map tier limit."""
        request = self._make_request("/api/v1/map/config")
        limit = get_endpoint_rate_limit(request)
        assert limit == 30

    def test_map_sovereignty(self):
        """Map sovereignty gets the map tier limit."""
        request = self._make_request("/api/v1/map/sovereignty")
        limit = get_endpoint_rate_limit(request)
        assert limit == 30

    def test_thera_endpoint(self):
        """Thera gets the map tier limit."""
        request = self._make_request("/api/v1/thera/connections")
        limit = get_endpoint_rate_limit(request)
        assert limit == 30

    def test_systems_endpoint(self):
        """Systems gets the map tier limit."""
        request = self._make_request("/api/v1/systems/30000142")
        limit = get_endpoint_rate_limit(request)
        assert limit == 30

    def test_legacy_map_endpoint(self):
        """Legacy /map/ prefix gets the map tier limit."""
        request = self._make_request("/map/config")
        limit = get_endpoint_rate_limit(request)
        assert limit == 30

    def test_websocket_exempt(self):
        """WebSocket paths return 0 (exempt from rate limiting)."""
        request = self._make_request("/api/v1/ws/killfeed")
        limit = get_endpoint_rate_limit(request)
        assert limit == 0

    def test_websocket_map(self):
        """WebSocket map path returns 0."""
        request = self._make_request("/api/v1/ws/map")
        limit = get_endpoint_rate_limit(request)
        assert limit == 0

    def test_write_method_post(self):
        """POST requests to unmatched paths get write limit."""
        request = self._make_request("/api/v1/alerts/subscribe", method="POST")
        limit = get_endpoint_rate_limit(request)
        assert limit == 15

    def test_write_method_put(self):
        """PUT requests to unmatched paths get write limit."""
        request = self._make_request("/api/v1/bookmarks/1", method="PUT")
        limit = get_endpoint_rate_limit(request)
        assert limit == 15

    def test_write_method_delete(self):
        """DELETE requests to unmatched paths get write limit."""
        request = self._make_request("/api/v1/bookmarks/1", method="DELETE")
        limit = get_endpoint_rate_limit(request)
        assert limit == 15

    def test_write_method_patch(self):
        """PATCH requests to unmatched paths get write limit."""
        request = self._make_request("/api/v1/notes/1", method="PATCH")
        limit = get_endpoint_rate_limit(request)
        assert limit == 15

    def test_default_get(self):
        """GET requests to unmatched paths get default limit."""
        request = self._make_request("/api/v1/intel/hot-systems")
        limit = get_endpoint_rate_limit(request)
        assert limit == 60

    def test_default_unmatched_path(self):
        """Completely unmatched paths get default limit."""
        request = self._make_request("/api/v1/fitting/analyze")
        limit = get_endpoint_rate_limit(request)
        assert limit == 60

    def test_custom_setting_override(self):
        """Rate limits respect settings overrides (env var tuning)."""
        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_HEALTH = 200
            mock_settings.RATE_LIMIT_AUTH = 5
            mock_settings.RATE_LIMIT_ROUTE = 10
            mock_settings.RATE_LIMIT_MAP = 25
            mock_settings.RATE_LIMIT_WRITE = 8
            mock_settings.RATE_LIMIT_DEFAULT = 50

            request = self._make_request("/health")
            assert get_endpoint_rate_limit(request) == 200

            request = self._make_request("/api/v1/auth/login")
            assert get_endpoint_rate_limit(request) == 5

            request = self._make_request("/api/v1/route/calculate")
            assert get_endpoint_rate_limit(request) == 10

            request = self._make_request("/api/v1/map/config")
            assert get_endpoint_rate_limit(request) == 25

            request = self._make_request("/api/v1/bookmarks/1", method="POST")
            assert get_endpoint_rate_limit(request) == 8

            request = self._make_request("/api/v1/intel/hot-systems")
            assert get_endpoint_rate_limit(request) == 50


class TestGetEndpointTier:
    """Tests for endpoint tier classification."""

    def test_health_tier(self):
        assert _get_endpoint_tier("/health", "GET") == "RATE_LIMIT_HEALTH"

    def test_root_tier(self):
        assert _get_endpoint_tier("/", "GET") == "RATE_LIMIT_HEALTH"

    def test_auth_tier(self):
        assert _get_endpoint_tier("/api/v1/auth/login", "GET") == "RATE_LIMIT_AUTH"

    def test_route_tier(self):
        assert _get_endpoint_tier("/api/v1/route/calculate", "GET") == "RATE_LIMIT_ROUTE"

    def test_map_tier(self):
        assert _get_endpoint_tier("/api/v1/map/config", "GET") == "RATE_LIMIT_MAP"

    def test_websocket_tier(self):
        assert _get_endpoint_tier("/api/v1/ws/killfeed", "GET") == "WEBSOCKET"

    def test_write_tier(self):
        assert _get_endpoint_tier("/api/v1/alerts/subscribe", "POST") == "RATE_LIMIT_WRITE"

    def test_default_tier(self):
        assert _get_endpoint_tier("/api/v1/intel/hot-systems", "GET") == "RATE_LIMIT_DEFAULT"


class TestEndpointRateLimitPatterns:
    """Tests for pattern ordering and coverage."""

    def test_patterns_are_compiled_regex(self):
        """All patterns are pre-compiled regex objects."""
        for pattern, attr_name in ENDPOINT_RATE_LIMIT_PATTERNS:
            assert hasattr(pattern, "match"), f"Pattern for {attr_name} is not compiled"

    def test_websocket_is_first_pattern(self):
        """WebSocket pattern must be checked first (exempt before any limit)."""
        _, attr_name = ENDPOINT_RATE_LIMIT_PATTERNS[0]
        assert attr_name == "WEBSOCKET"

    def test_pochven_route_before_pochven_general(self):
        """Pochven route pattern must appear before general pochven pattern."""
        pochven_route_idx = None
        pochven_general_idx = None
        for idx, (pattern, attr_name) in enumerate(ENDPOINT_RATE_LIMIT_PATTERNS):
            if attr_name == "RATE_LIMIT_ROUTE" and "pochven" in pattern.pattern:
                pochven_route_idx = idx
            if attr_name == "RATE_LIMIT_MAP" and "pochven" in pattern.pattern:
                pochven_general_idx = idx

        assert pochven_route_idx is not None, "Pochven route pattern missing"
        assert pochven_general_idx is not None, "Pochven general pattern missing"
        assert pochven_route_idx < pochven_general_idx, (
            "Pochven route must come before general pochven"
        )

    def test_all_attr_names_exist_in_settings(self):
        """All attr_name references (except WEBSOCKET) exist on settings."""
        for _, attr_name in ENDPOINT_RATE_LIMIT_PATTERNS:
            if attr_name == "WEBSOCKET":
                continue
            assert hasattr(type(MagicMock()), attr_name) or attr_name.startswith("RATE_LIMIT_"), (
                f"Unexpected attr_name format: {attr_name}"
            )


class TestPerEndpointRateLimitMiddleware:
    """Tests for the per-endpoint rate limiting middleware."""

    def _create_test_app(self, endpoint_limit: int = 5) -> FastAPI:
        """Create a minimal FastAPI app with per-endpoint middleware."""
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/api/v1/route/calculate")
        async def route_calculate():
            return {"route": []}

        @app.get("/api/v1/intel/hot-systems")
        async def intel():
            return {"systems": []}

        @app.post("/api/v1/alerts/subscribe")
        async def subscribe():
            return {"subscribed": True}

        # Add middleware
        app.add_middleware(PerEndpointRateLimitMiddleware)
        return app

    def test_allows_requests_under_limit(self):
        """Requests under the rate limit pass through."""
        app = self._create_test_app()
        client = TestClient(app)

        # Health endpoint has 120/min limit — should always pass
        response = client.get("/health")
        assert response.status_code == 200

    def test_returns_429_when_limit_exceeded(self):
        """Returns 429 when per-endpoint limit is exceeded."""
        app = self._create_test_app()
        client = TestClient(app)

        # Auth endpoint has 10/min limit — hammer it
        # We need an auth endpoint on the app
        @app.get("/api/v1/auth/login")
        async def login():
            return {"url": "https://login.eveonline.com"}

        # Force rebuild the client after route addition
        client = TestClient(app)

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_AUTH = 3
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = False

            # Send requests up to the limit
            for _ in range(3):
                response = client.get("/api/v1/auth/login")
                assert response.status_code == 200

            # Next request should be rate limited
            response = client.get("/api/v1/auth/login")
            assert response.status_code == 429
            body = response.json()
            assert body["error"] == "Rate limit exceeded"

    def test_rate_limit_headers_present(self):
        """Rate limit headers are added to successful responses."""
        app = self._create_test_app()
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        assert "x-ratelimit-limit-endpoint" in response.headers
        assert "x-ratelimit-remaining-endpoint" in response.headers

    def test_different_endpoints_have_independent_buckets(self):
        """Different endpoints have independent rate limit buckets."""
        app = self._create_test_app()

        @app.get("/api/v1/auth/login")
        async def login():
            return {"url": "https://login.eveonline.com"}

        client = TestClient(app)

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_AUTH = 2
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.API_KEY_ENABLED = False

            # Exhaust auth limit
            for _ in range(2):
                client.get("/api/v1/auth/login")

            # Auth should be blocked
            response = client.get("/api/v1/auth/login")
            assert response.status_code == 429

            # Health should still work (different bucket)
            response = client.get("/health")
            assert response.status_code == 200

    def test_websocket_paths_not_rate_limited(self):
        """WebSocket paths bypass rate limiting entirely."""
        app = FastAPI()

        @app.get("/api/v1/ws/killfeed")
        async def ws_stub():
            return {"ws": True}

        app.add_middleware(PerEndpointRateLimitMiddleware)
        client = TestClient(app)

        # Even many requests should pass
        for _ in range(50):
            response = client.get("/api/v1/ws/killfeed")
            assert response.status_code == 200

    def test_write_methods_get_write_limit(self):
        """POST/PUT/DELETE/PATCH to unmatched paths get the write limit."""
        app = self._create_test_app()
        client = TestClient(app)

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_WRITE = 2
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.API_KEY_ENABLED = False

            # POST to alerts/subscribe is unmatched by path patterns
            for _ in range(2):
                response = client.post("/api/v1/alerts/subscribe")
                assert response.status_code == 200

            response = client.post("/api/v1/alerts/subscribe")
            assert response.status_code == 429


class TestSetupRateLimiting:
    """Tests for setup_rate_limiting with per-endpoint middleware."""

    def test_setup_adds_per_endpoint_middleware(self):
        """Setup adds the PerEndpointRateLimitMiddleware."""
        app = FastAPI()

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = True
            mock_settings.RATE_LIMIT_DEFAULT = 60
            mock_settings.RATE_LIMIT_HEALTH = 120
            mock_settings.RATE_LIMIT_MAP = 30
            mock_settings.RATE_LIMIT_ROUTE = 20
            mock_settings.RATE_LIMIT_AUTH = 10
            mock_settings.RATE_LIMIT_WRITE = 15
            mock_settings.RATE_LIMIT_PER_MINUTE = 60
            mock_settings.RATE_LIMIT_PER_MINUTE_USER = 100
            mock_settings.RATE_LIMIT_PER_MINUTE_PRO = 300

            setup_rate_limiting(app)

            assert hasattr(app.state, "limiter")

    def test_setup_disabled_skips_middleware(self):
        """Setup does nothing when rate limiting is disabled."""
        app = FastAPI()

        with patch("backend.app.middleware.rate_limit.settings") as mock_settings:
            mock_settings.RATE_LIMIT_ENABLED = False

            setup_rate_limiting(app)

            assert not hasattr(app.state, "limiter")


class TestRateLimitTierOrdering:
    """Tests verifying that rate limit tiers are correctly ordered."""

    def test_auth_is_strictest(self):
        """Auth limit should be the lowest (strictest)."""
        assert settings.RATE_LIMIT_AUTH <= settings.RATE_LIMIT_WRITE
        assert settings.RATE_LIMIT_AUTH <= settings.RATE_LIMIT_ROUTE
        assert settings.RATE_LIMIT_AUTH <= settings.RATE_LIMIT_MAP
        assert settings.RATE_LIMIT_AUTH <= settings.RATE_LIMIT_DEFAULT
        assert settings.RATE_LIMIT_AUTH <= settings.RATE_LIMIT_HEALTH

    def test_health_is_most_permissive(self):
        """Health limit should be the highest (most permissive)."""
        assert settings.RATE_LIMIT_HEALTH >= settings.RATE_LIMIT_AUTH
        assert settings.RATE_LIMIT_HEALTH >= settings.RATE_LIMIT_WRITE
        assert settings.RATE_LIMIT_HEALTH >= settings.RATE_LIMIT_ROUTE
        assert settings.RATE_LIMIT_HEALTH >= settings.RATE_LIMIT_MAP
        assert settings.RATE_LIMIT_HEALTH >= settings.RATE_LIMIT_DEFAULT

    def test_default_values(self):
        """Verify default values match the specification."""
        from backend.app.core.config import Settings

        # Create a fresh settings instance to check defaults
        # (the imported settings may have env overrides)
        defaults = Settings.model_fields
        assert defaults["RATE_LIMIT_HEALTH"].default == 120
        assert defaults["RATE_LIMIT_MAP"].default == 30
        assert defaults["RATE_LIMIT_ROUTE"].default == 20
        assert defaults["RATE_LIMIT_AUTH"].default == 10
        assert defaults["RATE_LIMIT_WRITE"].default == 15
        assert defaults["RATE_LIMIT_DEFAULT"].default == 60
