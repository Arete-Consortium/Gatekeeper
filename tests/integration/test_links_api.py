"""Integration tests for external links API endpoints."""


class TestListToolsEndpoint:
    """Tests for GET /api/v1/links/tools."""

    def test_list_tools(self, test_client):
        """Test listing available tools."""
        response = test_client.get("/api/v1/links/tools")

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) >= 5

        tool_names = [t["name"] for t in data["tools"]]
        assert "Dotlan" in tool_names
        assert "zKillboard" in tool_names
        assert "EVE Eye" in tool_names
        assert "EVE Who" in tool_names
        assert "ESI" in tool_names

    def test_tools_have_required_fields(self, test_client):
        """Test tools have name, url, and description."""
        response = test_client.get("/api/v1/links/tools")
        data = response.json()

        for tool in data["tools"]:
            assert "name" in tool
            assert "url" in tool
            assert "description" in tool
            assert tool["url"].startswith("https://")


class TestSystemLinksEndpoint:
    """Tests for GET /api/v1/links/system/{system_name}."""

    def test_get_system_links(self, test_client):
        """Test getting links for a system."""
        response = test_client.get("/api/v1/links/system/Jita")

        assert response.status_code == 200
        data = response.json()
        assert data["system_name"] == "Jita"
        assert "dotlan" in data["links"]
        assert "eveeye" in data["links"]

    def test_get_system_links_with_id(self, test_client):
        """Test getting links with system ID."""
        response = test_client.get("/api/v1/links/system/Jita?system_id=30000142")

        assert response.status_code == 200
        data = response.json()
        assert data["system_id"] == 30000142
        assert "zkillboard" in data["links"]
        assert "esi" in data["links"]

    def test_get_system_links_with_region(self, test_client):
        """Test getting links with region info."""
        response = test_client.get(
            "/api/v1/links/system/Jita?region_name=The%20Forge&region_id=10000002"
        )

        assert response.status_code == 200
        data = response.json()
        assert "dotlan_region" in data["links"]
        assert "zkillboard_region" in data["links"]

    def test_get_system_links_url_encoded(self, test_client):
        """Test system with spaces in name."""
        response = test_client.get("/api/v1/links/system/New%20Caldari")

        assert response.status_code == 200
        data = response.json()
        assert data["system_name"] == "New Caldari"


class TestCharacterLinksEndpoint:
    """Tests for GET /api/v1/links/character/{character_id}."""

    def test_get_character_links(self, test_client):
        """Test getting links for a character."""
        response = test_client.get("/api/v1/links/character/12345678")

        assert response.status_code == 200
        data = response.json()
        assert data["character_id"] == 12345678
        assert "zkillboard" in data["links"]
        assert "evewho" in data["links"]
        assert "esi" in data["links"]

    def test_character_links_contain_id(self, test_client):
        """Test character ID is in URLs."""
        response = test_client.get("/api/v1/links/character/98765432")
        data = response.json()

        assert "98765432" in data["links"]["zkillboard"]
        assert "98765432" in data["links"]["evewho"]
        assert "98765432" in data["links"]["esi"]


class TestCorporationLinksEndpoint:
    """Tests for GET /api/v1/links/corporation/{corporation_id}."""

    def test_get_corporation_links(self, test_client):
        """Test getting links for a corporation."""
        response = test_client.get("/api/v1/links/corporation/98000001")

        assert response.status_code == 200
        data = response.json()
        assert data["corporation_id"] == 98000001
        assert "zkillboard" in data["links"]
        assert "evewho" in data["links"]
        assert "esi" in data["links"]

    def test_corporation_links_contain_id(self, test_client):
        """Test corporation ID is in URLs."""
        response = test_client.get("/api/v1/links/corporation/98765432")
        data = response.json()

        assert "98765432" in data["links"]["zkillboard"]
        assert "98765432" in data["links"]["evewho"]
        assert "98765432" in data["links"]["esi"]


class TestAllianceLinksEndpoint:
    """Tests for GET /api/v1/links/alliance/{alliance_id}."""

    def test_get_alliance_links(self, test_client):
        """Test getting links for an alliance."""
        response = test_client.get("/api/v1/links/alliance/99000001")

        assert response.status_code == 200
        data = response.json()
        assert data["alliance_id"] == 99000001
        assert "zkillboard" in data["links"]
        assert "evewho" in data["links"]
        assert "esi" in data["links"]

    def test_alliance_links_contain_id(self, test_client):
        """Test alliance ID is in URLs."""
        response = test_client.get("/api/v1/links/alliance/99876543")
        data = response.json()

        assert "99876543" in data["links"]["zkillboard"]
        assert "99876543" in data["links"]["evewho"]
        assert "99876543" in data["links"]["esi"]


class TestRouteLinksEndpoint:
    """Tests for GET /api/v1/links/route."""

    def test_get_route_links(self, test_client):
        """Test getting links for a route."""
        response = test_client.get("/api/v1/links/route?from=Jita&to=Amarr")

        assert response.status_code == 200
        data = response.json()
        assert data["from_system"] == "Jita"
        assert data["to_system"] == "Amarr"
        assert "dotlan" in data["links"]
        assert "eveeye" in data["links"]

    def test_get_route_links_with_path(self, test_client):
        """Test getting links with full path."""
        response = test_client.get(
            "/api/v1/links/route?from=Jita&to=Amarr&path=Jita&path=Perimeter&path=Urlen&path=Amarr"
        )

        assert response.status_code == 200
        data = response.json()
        assert "dotlan_full" in data["links"]
        assert "dotlan_jump" in data["links"]

    def test_route_links_requires_from(self, test_client):
        """Test route requires from parameter."""
        response = test_client.get("/api/v1/links/route?to=Amarr")

        assert response.status_code == 422

    def test_route_links_requires_to(self, test_client):
        """Test route requires to parameter."""
        response = test_client.get("/api/v1/links/route?from=Jita")

        assert response.status_code == 422


class TestShipLinksEndpoint:
    """Tests for GET /api/v1/links/ship/{ship_type_id}."""

    def test_get_ship_links(self, test_client):
        """Test getting links for a ship type."""
        response = test_client.get("/api/v1/links/ship/587")

        assert response.status_code == 200
        data = response.json()
        assert data["ship_type_id"] == 587
        assert "zkillboard" in data["links"]
        assert "esi" in data["links"]

    def test_ship_links_contain_id(self, test_client):
        """Test ship ID is in URLs."""
        response = test_client.get("/api/v1/links/ship/11567")
        data = response.json()

        assert "11567" in data["links"]["zkillboard"]
        assert "11567" in data["links"]["esi"]


class TestLinksUrlValidity:
    """Tests for URL validity in responses."""

    def test_all_urls_are_https(self, test_client):
        """Test all generated URLs use HTTPS."""
        response = test_client.get(
            "/api/v1/links/system/Jita?system_id=30000142&region_name=The%20Forge&region_id=10000002"
        )
        data = response.json()

        for url in data["links"].values():
            assert url.startswith("https://"), f"URL not HTTPS: {url}"

    def test_dotlan_urls_valid(self, test_client):
        """Test Dotlan URLs have correct format."""
        response = test_client.get("/api/v1/links/system/Jita")
        data = response.json()

        assert "evemaps.dotlan.net" in data["links"]["dotlan"]
        assert "evemaps.dotlan.net" in data["links"]["dotlan_radar"]

    def test_zkillboard_urls_valid(self, test_client):
        """Test zKillboard URLs have correct format."""
        response = test_client.get("/api/v1/links/character/12345678")
        data = response.json()

        assert "zkillboard.com/character/" in data["links"]["zkillboard"]

    def test_eveeye_urls_valid(self, test_client):
        """Test EVE Eye URLs have correct format."""
        response = test_client.get("/api/v1/links/system/Jita")
        data = response.json()

        assert "eveeye.com" in data["links"]["eveeye"]

    def test_evewho_urls_valid(self, test_client):
        """Test EVE Who URLs have correct format."""
        response = test_client.get("/api/v1/links/character/12345678")
        data = response.json()

        assert "evewho.com/character/" in data["links"]["evewho"]

    def test_esi_urls_valid(self, test_client):
        """Test ESI URLs have correct format."""
        response = test_client.get("/api/v1/links/character/12345678")
        data = response.json()

        assert "esi.evetech.net/latest/characters/" in data["links"]["esi"]
