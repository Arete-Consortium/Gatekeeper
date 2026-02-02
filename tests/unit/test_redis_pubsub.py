"""Tests for the Redis pub/sub service."""

import pytest


class TestRedisPubSub:
    """Tests for RedisPubSub class."""

    @pytest.fixture
    def pubsub(self):
        """Create a fresh RedisPubSub instance for testing."""
        from backend.app.services.redis_pubsub import RedisPubSub

        return RedisPubSub(channel="test:kills")

    def test_generate_instance_id(self, pubsub):
        """Test that instance ID is generated."""
        assert pubsub._instance_id is not None
        assert len(pubsub._instance_id) > 0
        assert "-" in pubsub._instance_id

    def test_instance_id_unique(self):
        """Test that different instances have different IDs."""
        from backend.app.services.redis_pubsub import RedisPubSub

        pubsub1 = RedisPubSub(channel="test:kills")
        pubsub2 = RedisPubSub(channel="test:kills")

        assert pubsub1._instance_id != pubsub2._instance_id

    def test_is_enabled_without_redis_url(self, pubsub, monkeypatch):
        """Test that pub/sub is disabled without Redis URL."""
        from backend.app.core import config

        monkeypatch.setattr(config.settings, "REDIS_URL", None)

        assert pubsub.is_enabled is False

    def test_is_enabled_with_redis_url(self, pubsub, monkeypatch):
        """Test that pub/sub is enabled with Redis URL."""
        from backend.app.core import config

        monkeypatch.setattr(config.settings, "REDIS_URL", "redis://localhost:6379")
        monkeypatch.setattr(config.settings, "REDIS_PUBSUB_ENABLED", True)

        assert pubsub.is_enabled is True

    def test_is_enabled_disabled_by_config(self, pubsub, monkeypatch):
        """Test that pub/sub can be disabled via config."""
        from backend.app.core import config

        monkeypatch.setattr(config.settings, "REDIS_URL", "redis://localhost:6379")
        monkeypatch.setattr(config.settings, "REDIS_PUBSUB_ENABLED", False)

        assert pubsub.is_enabled is False

    def test_is_connected_initially_false(self, pubsub):
        """Test that connected is false initially."""
        assert pubsub.is_connected is False

    def test_get_stats(self, pubsub):
        """Test getting statistics."""
        stats = pubsub.get_stats()

        assert "enabled" in stats
        assert "connected" in stats
        assert "channel" in stats
        assert "instance_id" in stats
        assert "messages_published" in stats
        assert "messages_received" in stats
        assert "messages_ignored_self" in stats
        assert stats["channel"] == "test:kills"

    def test_channel_configurable(self):
        """Test that channel is configurable."""
        from backend.app.services.redis_pubsub import RedisPubSub

        pubsub = RedisPubSub(channel="custom:channel")

        assert pubsub._channel == "custom:channel"

    @pytest.mark.asyncio
    async def test_publish_kill_without_connection(self, pubsub):
        """Test that publish returns False when not connected."""
        kill_data = {"kill_id": 12345, "solar_system_id": 30000142}

        result = await pubsub.publish_kill(kill_data)

        assert result is False


class TestRedisPubSubGlobal:
    """Tests for global pub/sub instance."""

    def test_get_redis_pubsub_singleton(self):
        """Test that get_redis_pubsub returns same instance."""
        from backend.app.services import redis_pubsub

        # Reset global
        redis_pubsub._redis_pubsub = None

        p1 = redis_pubsub.get_redis_pubsub()
        p2 = redis_pubsub.get_redis_pubsub()

        assert p1 is p2

        # Clean up
        redis_pubsub._redis_pubsub = None
