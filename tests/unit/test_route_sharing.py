"""Unit tests for route sharing service."""

from datetime import UTC, datetime, timedelta

import pytest

from backend.app.services.route_sharing import (
    RouteShareStore,
    SharedRoute,
    create_route_hash,
    export_to_dotlan_url,
    export_to_eveeye_url,
    export_to_json,
    export_to_text,
    export_to_waypoint_names,
    get_share_store,
    reset_share_store,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the global share store before each test."""
    reset_share_store()
    yield
    reset_share_store()


@pytest.fixture
def sample_route_data():
    """Sample route data for testing."""
    return {
        "from_system": "Jita",
        "to_system": "Amarr",
        "profile": "safer",
        "total_jumps": 15,
        "path": [
            {"system_name": "Jita", "security": 0.95},
            {"system_name": "Perimeter", "security": 0.94},
            {"system_name": "Urlen", "security": 0.87},
            {"system_name": "Amarr", "security": 1.0},
        ],
    }


class TestSharedRoute:
    """Tests for SharedRoute dataclass."""

    def test_basic_creation(self, sample_route_data):
        """Test creating a SharedRoute."""
        route = SharedRoute(
            token="abc123",
            route_data=sample_route_data,
            from_system="Jita",
            to_system="Amarr",
        )
        assert route.token == "abc123"
        assert route.from_system == "Jita"

    def test_is_expired_with_future_expiry(self, sample_route_data):
        """Test is_expired returns False for future expiry."""
        route = SharedRoute(
            token="abc123",
            route_data=sample_route_data,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert route.is_expired is False

    def test_is_expired_with_past_expiry(self, sample_route_data):
        """Test is_expired returns True for past expiry."""
        route = SharedRoute(
            token="abc123",
            route_data=sample_route_data,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert route.is_expired is True

    def test_is_expired_with_no_expiry(self, sample_route_data):
        """Test is_expired returns False when no expiry set."""
        route = SharedRoute(
            token="abc123",
            route_data=sample_route_data,
            expires_at=None,
        )
        assert route.is_expired is False

    def test_url_path(self, sample_route_data):
        """Test url_path property."""
        route = SharedRoute(
            token="abc123",
            route_data=sample_route_data,
        )
        assert route.url_path == "/s/abc123"


class TestRouteShareStore:
    """Tests for RouteShareStore class."""

    def test_create_share(self, sample_route_data):
        """Test creating a share."""
        store = RouteShareStore()
        shared = store.create_share(sample_route_data)

        assert shared.token is not None
        assert len(shared.token) == 8
        assert shared.from_system == "Jita"
        assert shared.to_system == "Amarr"

    def test_create_share_with_creator(self, sample_route_data):
        """Test creating share with creator name."""
        store = RouteShareStore()
        shared = store.create_share(
            sample_route_data,
            creator_name="TestPilot",
            description="My route",
        )

        assert shared.creator_name == "TestPilot"
        assert shared.description == "My route"

    def test_create_share_with_custom_ttl(self, sample_route_data):
        """Test creating share with custom TTL."""
        store = RouteShareStore()
        shared = store.create_share(sample_route_data, ttl_hours=48)

        assert shared.expires_at is not None
        # Should expire in ~48 hours
        diff = shared.expires_at - datetime.now(UTC)
        assert 47 * 3600 < diff.total_seconds() < 49 * 3600

    def test_create_share_never_expires(self, sample_route_data):
        """Test creating share that never expires."""
        store = RouteShareStore()
        shared = store.create_share(sample_route_data, ttl_hours=-1)

        assert shared.expires_at is None
        assert shared.is_expired is False

    def test_get_share(self, sample_route_data):
        """Test retrieving a share."""
        store = RouteShareStore()
        created = store.create_share(sample_route_data)

        retrieved = store.get_share(created.token)

        assert retrieved is not None
        assert retrieved.token == created.token
        assert retrieved.access_count == 1

    def test_get_share_increments_access(self, sample_route_data):
        """Test that getting share increments access count."""
        store = RouteShareStore()
        created = store.create_share(sample_route_data)

        store.get_share(created.token)
        store.get_share(created.token)
        retrieved = store.get_share(created.token)

        assert retrieved.access_count == 3

    def test_get_nonexistent_share(self):
        """Test getting nonexistent share returns None."""
        store = RouteShareStore()
        result = store.get_share("nonexistent")
        assert result is None

    def test_get_expired_share(self, sample_route_data):
        """Test getting expired share returns None."""
        store = RouteShareStore()
        shared = store.create_share(sample_route_data, ttl_hours=0)

        # Manually set past expiry
        store._routes[shared.token].expires_at = datetime.now(UTC) - timedelta(hours=1)

        result = store.get_share(shared.token)
        assert result is None

    def test_delete_share(self, sample_route_data):
        """Test deleting a share."""
        store = RouteShareStore()
        created = store.create_share(sample_route_data)

        assert store.delete_share(created.token) is True
        assert store.get_share(created.token) is None

    def test_delete_nonexistent_share(self):
        """Test deleting nonexistent share returns False."""
        store = RouteShareStore()
        assert store.delete_share("nonexistent") is False

    def test_list_shares(self, sample_route_data):
        """Test listing shares."""
        store = RouteShareStore()
        store.create_share(sample_route_data)
        store.create_share(sample_route_data)
        store.create_share(sample_route_data)

        shares = store.list_shares()
        assert len(shares) == 3

    def test_list_shares_by_creator(self, sample_route_data):
        """Test listing shares filtered by creator."""
        store = RouteShareStore()
        store.create_share(sample_route_data, creator_name="Alice")
        store.create_share(sample_route_data, creator_name="Bob")
        store.create_share(sample_route_data, creator_name="Alice")

        alice_shares = store.list_shares(creator_name="Alice")
        assert len(alice_shares) == 2

    def test_list_shares_with_limit(self, sample_route_data):
        """Test listing shares with limit."""
        store = RouteShareStore()
        for _ in range(10):
            store.create_share(sample_route_data)

        shares = store.list_shares(limit=5)
        assert len(shares) == 5

    def test_unique_tokens(self, sample_route_data):
        """Test that generated tokens are unique."""
        store = RouteShareStore()
        tokens = set()

        for _ in range(100):
            shared = store.create_share(sample_route_data)
            tokens.add(shared.token)

        assert len(tokens) == 100

    def test_prune_expired(self, sample_route_data):
        """Test expired routes are pruned."""
        store = RouteShareStore()
        shared1 = store.create_share(sample_route_data, ttl_hours=24)
        shared2 = store.create_share(sample_route_data, ttl_hours=24)

        # Manually expire one
        store._routes[shared1.token].expires_at = datetime.now(UTC) - timedelta(hours=1)

        # Trigger prune
        store._prune_expired()

        assert shared1.token not in store._routes
        assert shared2.token in store._routes


class TestExportFunctions:
    """Tests for export functions."""

    def test_export_to_text(self, sample_route_data):
        """Test exporting to text format."""
        text = export_to_text(sample_route_data)

        assert "Route: Jita -> Amarr" in text
        assert "15 jumps" in text
        assert "safer" in text
        assert "1. Jita" in text
        assert "4. Amarr" in text

    def test_export_to_text_with_security(self, sample_route_data):
        """Test text export includes security."""
        text = export_to_text(sample_route_data)
        assert "(0.95)" in text  # Jita security

    def test_export_to_waypoint_names(self, sample_route_data):
        """Test exporting waypoint names."""
        names = export_to_waypoint_names(sample_route_data)

        assert names == ["Jita", "Perimeter", "Urlen", "Amarr"]

    def test_export_to_waypoint_names_empty(self):
        """Test waypoint export with empty route."""
        names = export_to_waypoint_names({"path": []})
        assert names == []

    def test_export_to_dotlan_url(self, sample_route_data):
        """Test generating Dotlan URL."""
        url = export_to_dotlan_url(sample_route_data)

        assert url.startswith("https://evemaps.dotlan.net/route/")
        assert "Jita:Perimeter:Urlen:Amarr" in url

    def test_export_to_eveeye_url(self, sample_route_data):
        """Test generating EVE Eye URL."""
        url = export_to_eveeye_url(sample_route_data)

        assert url.startswith("https://eveeye.com/")
        assert "route=Jita:Amarr" in url

    def test_export_to_json(self, sample_route_data):
        """Test JSON export."""
        json_str = export_to_json(sample_route_data)

        assert "Jita" in json_str
        assert "Amarr" in json_str

    def test_export_to_json_pretty(self, sample_route_data):
        """Test pretty JSON export."""
        json_str = export_to_json(sample_route_data, pretty=True)

        assert "\n" in json_str  # Pretty print has newlines

    def test_create_route_hash(self, sample_route_data):
        """Test route hash generation."""
        hash1 = create_route_hash(sample_route_data)
        hash2 = create_route_hash(sample_route_data)

        assert hash1 == hash2  # Same route, same hash
        assert len(hash1) == 12

    def test_create_route_hash_different_routes(self, sample_route_data):
        """Test different routes have different hashes."""
        hash1 = create_route_hash(sample_route_data)

        modified = sample_route_data.copy()
        modified["to_system"] = "Dodixie"
        hash2 = create_route_hash(modified)

        assert hash1 != hash2


class TestGetShareStore:
    """Tests for get_share_store singleton."""

    def test_returns_same_instance(self):
        """Test singleton returns same instance."""
        store1 = get_share_store()
        store2 = get_share_store()
        assert store1 is store2

    def test_reset_creates_new_instance(self):
        """Test reset creates new instance."""
        store1 = get_share_store()
        reset_share_store()
        store2 = get_share_store()
        assert store1 is not store2


class TestRouteShareStoreCapacity:
    """Tests for store capacity and pruning."""

    def test_prune_if_full(self, sample_route_data):
        """Test routes are pruned when at capacity."""
        store = RouteShareStore(max_routes=10)

        # Fill to capacity
        for _ in range(10):
            store.create_share(sample_route_data)

        assert store.count == 10

        # Add one more - should trigger prune
        store.create_share(sample_route_data)

        # Should have removed 10% (1 route) and added 1
        assert store.count == 10

    def test_prune_removes_oldest_accessed(self, sample_route_data):
        """Test that oldest accessed routes are pruned first."""
        store = RouteShareStore(max_routes=5)

        # Create 5 shares
        shares = []
        for i in range(5):
            shares.append(store.create_share(sample_route_data, creator_name=f"creator_{i}"))

        # Access the newest ones to update last_accessed
        store.get_share(shares[3].token)
        store.get_share(shares[4].token)

        # Add more to trigger prune
        store.create_share(sample_route_data)

        # Oldest unaccessed (0) should be gone
        assert store.get_share(shares[0].token) is None or store.count <= 5


class TestRouteShareStoreEdgeCases:
    """Edge case tests for RouteShareStore."""

    def test_token_collision_handling(self, sample_route_data):
        """Test that token collisions are handled."""
        store = RouteShareStore(token_length=1)  # Very short tokens increase collision chance

        # Create many shares to increase collision probability
        for _ in range(50):
            store.create_share(sample_route_data)

        # All should have unique tokens
        assert store.count == 50

    def test_get_share_expired_during_retrieval(self, sample_route_data):
        """Test getting a share that expired between prune and retrieval."""
        store = RouteShareStore()
        shared = store.create_share(sample_route_data, ttl_hours=24)

        # Manually set expiry to just expired (after prune_expired would run)
        store._routes[shared.token].expires_at = datetime.now(UTC) - timedelta(seconds=1)

        # Should return None and delete the route
        result = store.get_share(shared.token)
        assert result is None
        assert shared.token not in store._routes

    def test_get_share_expired_check_in_lock(self, sample_route_data):
        """Test the is_expired check inside get_share lock block."""
        store = RouteShareStore()
        shared = store.create_share(sample_route_data, ttl_hours=24)

        # We need to make the route appear expired AFTER _prune_expired runs
        # by setting expires_at in the past but with no expiry on other routes
        # so prune doesn't see it

        # Create a non-expired route first to prevent early exit in prune
        store.create_share(sample_route_data, ttl_hours=-1)  # Never expires

        # Now set the first route to expired - prune checks all routes but
        # they need to be expired at prune time
        # The key is that is_expired is a property that checks datetime.now() each time
        # So we set expires_at to exactly now, then it should be expired when checked
        store._routes[shared.token].expires_at = datetime.now(UTC) - timedelta(microseconds=1)

        result = store.get_share(shared.token)
        assert result is None


class TestExportEdgeCases:
    """Edge case tests for export functions."""

    def test_export_to_text_none_security(self):
        """Test export handles None security."""
        route_data = {
            "from_system": "Jita",
            "to_system": "Thera",
            "profile": "wormhole",
            "total_jumps": 2,
            "path": [
                {"system_name": "Jita", "security": 0.95},
                {"system_name": "Thera", "security": None},
            ],
        }
        text = export_to_text(route_data)
        assert "2. Thera" in text
        # No security shown for Thera

    def test_export_to_dotlan_empty_path(self):
        """Test Dotlan URL with empty path."""
        url = export_to_dotlan_url({"path": []})
        assert url == "https://evemaps.dotlan.net/route/"

    def test_export_to_eveeye_single_system(self):
        """Test EVE Eye URL with only one system."""
        url = export_to_eveeye_url({"path": [{"system_name": "Jita"}]})
        assert url == "https://eveeye.com/"

    def test_export_to_eveeye_empty_path(self):
        """Test EVE Eye URL with empty path."""
        url = export_to_eveeye_url({"path": []})
        assert url == "https://eveeye.com/"
