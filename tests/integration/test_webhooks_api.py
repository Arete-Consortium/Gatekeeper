"""Integration tests for webhooks API endpoints."""


class TestWebhooksListEndpoint:
    """Tests for GET /api/v1/webhooks/ endpoint."""

    def test_list_webhooks(self, test_client):
        """Test listing webhooks."""
        response = test_client.get("/api/v1/webhooks/")
        assert response.status_code == 200

        data = response.json()
        assert "webhooks" in data
        assert "total" in data
        assert isinstance(data["webhooks"], list)


class TestWebhooksCreateEndpoint:
    """Tests for POST /api/v1/webhooks/ endpoint."""

    def test_create_webhook_validation(self, test_client):
        """Test webhook creation validates required fields."""
        response = test_client.post("/api/v1/webhooks/", json={})
        assert response.status_code == 422

    def test_create_webhook_invalid_url(self, test_client):
        """Test webhook creation rejects invalid URL."""
        response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "not-a-valid-url",
                "webhook_type": "discord",
            },
        )
        assert response.status_code == 422

    def test_create_webhook_invalid_type(self, test_client):
        """Test webhook creation rejects invalid type."""
        response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://discord.com/api/webhooks/test",
                "webhook_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    def test_create_webhook_invalid_system(self, test_client):
        """Test webhook creation rejects invalid system."""
        response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://discord.com/api/webhooks/test",
                "webhook_type": "discord",
                "systems": ["NonExistentSystem"],
            },
        )
        assert response.status_code == 400

    def test_create_discord_webhook(self, test_client):
        """Test creating a Discord webhook subscription."""
        response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://discord.com/api/webhooks/123/abc",
                "webhook_type": "discord",
                "systems": ["Jita"],
                "min_value": 100000000,
                "include_pods": False,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["webhook_type"] == "discord"
        assert data["systems"] == ["Jita"]
        assert data["min_value"] == 100000000
        assert data["include_pods"] is False
        assert data["enabled"] is True
        # URL should be masked
        assert "webhook_url_preview" in data
        assert "..." in data["webhook_url_preview"]

    def test_create_slack_webhook(self, test_client):
        """Test creating a Slack webhook subscription."""
        response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://hooks.slack.com/services/T00/B00/xyz",
                "webhook_type": "slack",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["webhook_type"] == "slack"


class TestWebhooksDetailEndpoint:
    """Tests for GET/PATCH/DELETE /api/v1/webhooks/{id} endpoints."""

    def test_get_webhook_not_found(self, test_client):
        """Test getting nonexistent webhook returns 404."""
        response = test_client.get("/api/v1/webhooks/nonexistent-id")
        assert response.status_code == 404

    def test_delete_webhook_not_found(self, test_client):
        """Test deleting nonexistent webhook returns 404."""
        response = test_client.delete("/api/v1/webhooks/nonexistent-id")
        assert response.status_code == 404

    def test_update_webhook_not_found(self, test_client):
        """Test updating nonexistent webhook returns 404."""
        response = test_client.patch("/api/v1/webhooks/nonexistent-id", json={"enabled": False})
        assert response.status_code == 404

    def test_webhook_crud_flow(self, test_client):
        """Test full CRUD flow for webhooks."""
        # Create
        create_response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://discord.com/api/webhooks/999/test",
                "webhook_type": "discord",
                "systems": ["Jita", "Perimeter"],
            },
        )
        assert create_response.status_code == 201
        webhook_id = create_response.json()["id"]

        # Read
        get_response = test_client.get(f"/api/v1/webhooks/{webhook_id}")
        assert get_response.status_code == 200
        assert get_response.json()["systems"] == ["Jita", "Perimeter"]

        # Update
        update_response = test_client.patch(
            f"/api/v1/webhooks/{webhook_id}", json={"enabled": False, "systems": ["Jita"]}
        )
        assert update_response.status_code == 200
        assert update_response.json()["enabled"] is False
        assert update_response.json()["systems"] == ["Jita"]

        # Delete
        delete_response = test_client.delete(f"/api/v1/webhooks/{webhook_id}")
        assert delete_response.status_code == 204

        # Verify deleted
        verify_response = test_client.get(f"/api/v1/webhooks/{webhook_id}")
        assert verify_response.status_code == 404

    def test_update_webhook_invalid_system(self, test_client):
        """Test updating webhook with invalid system returns 400."""
        # Create first
        create_response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://discord.com/api/webhooks/888/test",
                "webhook_type": "discord",
                "systems": ["Jita"],
            },
        )
        assert create_response.status_code == 201
        webhook_id = create_response.json()["id"]

        # Update with invalid system
        update_response = test_client.patch(
            f"/api/v1/webhooks/{webhook_id}", json={"systems": ["NonExistentSystem"]}
        )
        assert update_response.status_code == 400
        assert "Unknown system" in update_response.json()["detail"]

    def test_update_webhook_min_value(self, test_client):
        """Test updating webhook min_value field."""
        # Create first
        create_response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://discord.com/api/webhooks/777/test",
                "webhook_type": "discord",
            },
        )
        assert create_response.status_code == 201
        webhook_id = create_response.json()["id"]

        # Update min_value only
        update_response = test_client.patch(
            f"/api/v1/webhooks/{webhook_id}", json={"min_value": 500000000}
        )
        assert update_response.status_code == 200
        assert update_response.json()["min_value"] == 500000000

    def test_update_webhook_include_pods(self, test_client):
        """Test updating webhook include_pods field."""
        # Create first
        create_response = test_client.post(
            "/api/v1/webhooks/",
            json={
                "webhook_url": "https://discord.com/api/webhooks/666/test",
                "webhook_type": "discord",
                "include_pods": True,
            },
        )
        assert create_response.status_code == 201
        webhook_id = create_response.json()["id"]
        assert create_response.json()["include_pods"] is True

        # Update include_pods only
        update_response = test_client.patch(
            f"/api/v1/webhooks/{webhook_id}", json={"include_pods": False}
        )
        assert update_response.status_code == 200
        assert update_response.json()["include_pods"] is False


class TestWebhookTestEndpoint:
    """Tests for POST /api/v1/webhooks/test endpoint."""

    def test_test_webhook_validation(self, test_client):
        """Test webhook test validates required fields."""
        response = test_client.post("/api/v1/webhooks/test", json={})
        assert response.status_code == 422

    def test_test_webhook_invalid_url(self, test_client):
        """Test webhook test rejects invalid URL."""
        response = test_client.post(
            "/api/v1/webhooks/test",
            json={
                "webhook_url": "not-a-url",
                "webhook_type": "discord",
            },
        )
        assert response.status_code == 422

    def test_test_webhook_success(self, test_client, monkeypatch):
        """Test successful webhook test message."""
        from unittest.mock import AsyncMock

        # Mock the send_webhook function to return success
        mock_send = AsyncMock(return_value=True)
        monkeypatch.setattr("backend.app.api.v1.webhooks.send_webhook", mock_send)

        response = test_client.post(
            "/api/v1/webhooks/test",
            json={
                "webhook_url": "https://discord.com/api/webhooks/123/test",
                "webhook_type": "discord",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully" in data["message"]

    def test_test_webhook_failure(self, test_client, monkeypatch):
        """Test failed webhook test message."""
        from unittest.mock import AsyncMock

        # Mock the send_webhook function to return failure
        mock_send = AsyncMock(return_value=False)
        monkeypatch.setattr("backend.app.api.v1.webhooks.send_webhook", mock_send)

        response = test_client.post(
            "/api/v1/webhooks/test",
            json={
                "webhook_url": "https://discord.com/api/webhooks/456/test",
                "webhook_type": "discord",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Failed" in data["message"]

    def test_test_webhook_slack_type(self, test_client, monkeypatch):
        """Test webhook test with Slack type."""
        from unittest.mock import AsyncMock

        mock_send = AsyncMock(return_value=True)
        monkeypatch.setattr("backend.app.api.v1.webhooks.send_webhook", mock_send)

        response = test_client.post(
            "/api/v1/webhooks/test",
            json={
                "webhook_url": "https://hooks.slack.com/services/T/B/x",
                "webhook_type": "slack",
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
