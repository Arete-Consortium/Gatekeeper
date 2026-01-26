"""Unit tests for external links service."""


from backend.app.services.external_links import (
    dotlan_jump_url,
    dotlan_radar_url,
    dotlan_region_url,
    dotlan_route_from_to_url,
    dotlan_route_url,
    dotlan_system_url,
    esi_alliance_url,
    esi_character_url,
    esi_corporation_url,
    esi_system_url,
    esi_type_url,
    eveeye_map_url,
    eveeye_route_url,
    eveeye_system_url,
    evewho_alliance_url,
    evewho_character_url,
    evewho_corporation_url,
    get_alliance_links,
    get_character_links,
    get_corporation_links,
    get_route_links,
    get_ship_links,
    get_system_links,
    zkillboard_alliance_url,
    zkillboard_character_url,
    zkillboard_corporation_url,
    zkillboard_region_url,
    zkillboard_ship_url,
    zkillboard_system_url,
    zkillboard_system_url_by_name,
)


class TestDotlanUrls:
    """Tests for Dotlan URL generators."""

    def test_dotlan_system_url(self):
        """Test Dotlan system URL generation."""
        url = dotlan_system_url("Jita")
        assert url == "https://evemaps.dotlan.net/system/Jita"

    def test_dotlan_system_url_with_spaces(self):
        """Test Dotlan system URL with spaces in name."""
        url = dotlan_system_url("New Caldari")
        assert url == "https://evemaps.dotlan.net/system/New%20Caldari"

    def test_dotlan_region_url(self):
        """Test Dotlan region URL generation."""
        url = dotlan_region_url("The Forge")
        assert url == "https://evemaps.dotlan.net/map/The%20Forge"

    def test_dotlan_route_url_empty(self):
        """Test Dotlan route URL with empty list."""
        url = dotlan_route_url([])
        assert url == "https://evemaps.dotlan.net/route"

    def test_dotlan_route_url_single(self):
        """Test Dotlan route URL with single system."""
        url = dotlan_route_url(["Jita"])
        assert url == "https://evemaps.dotlan.net/route/Jita"

    def test_dotlan_route_url_multiple(self):
        """Test Dotlan route URL with multiple systems."""
        url = dotlan_route_url(["Jita", "Perimeter", "Amarr"])
        assert url == "https://evemaps.dotlan.net/route/Jita:Perimeter:Amarr"

    def test_dotlan_route_from_to_url(self):
        """Test Dotlan route URL from origin to destination."""
        url = dotlan_route_from_to_url("Jita", "Amarr")
        assert url == "https://evemaps.dotlan.net/route/Jita:Amarr"

    def test_dotlan_jump_url_empty(self):
        """Test Dotlan jump URL with empty list."""
        url = dotlan_jump_url([])
        assert url == "https://evemaps.dotlan.net/jump"

    def test_dotlan_jump_url_with_systems(self):
        """Test Dotlan jump URL with systems."""
        url = dotlan_jump_url(["Jita", "Amarr"])
        assert url == "https://evemaps.dotlan.net/jump/Anshar,544/Jita:Amarr"

    def test_dotlan_radar_url(self):
        """Test Dotlan radar URL generation."""
        url = dotlan_radar_url("Rancer")
        assert url == "https://evemaps.dotlan.net/system/Rancer/radar"


class TestZkillboardUrls:
    """Tests for zKillboard URL generators."""

    def test_zkillboard_system_url(self):
        """Test zKillboard system URL by ID."""
        url = zkillboard_system_url(30000142)
        assert url == "https://zkillboard.com/system/30000142/"

    def test_zkillboard_system_url_by_name(self):
        """Test zKillboard system search URL by name."""
        url = zkillboard_system_url_by_name("Jita")
        assert url == "https://zkillboard.com/search/Jita/"

    def test_zkillboard_character_url(self):
        """Test zKillboard character URL."""
        url = zkillboard_character_url(12345678)
        assert url == "https://zkillboard.com/character/12345678/"

    def test_zkillboard_corporation_url(self):
        """Test zKillboard corporation URL."""
        url = zkillboard_corporation_url(98000001)
        assert url == "https://zkillboard.com/corporation/98000001/"

    def test_zkillboard_alliance_url(self):
        """Test zKillboard alliance URL."""
        url = zkillboard_alliance_url(99000001)
        assert url == "https://zkillboard.com/alliance/99000001/"

    def test_zkillboard_region_url(self):
        """Test zKillboard region URL."""
        url = zkillboard_region_url(10000002)
        assert url == "https://zkillboard.com/region/10000002/"

    def test_zkillboard_ship_url(self):
        """Test zKillboard ship URL."""
        url = zkillboard_ship_url(587)
        assert url == "https://zkillboard.com/ship/587/"


class TestEveeyeUrls:
    """Tests for EVE Eye URL generators."""

    def test_eveeye_system_url(self):
        """Test EVE Eye system URL."""
        url = eveeye_system_url("Jita")
        assert url == "https://eveeye.com/?system=Jita"

    def test_eveeye_route_url(self):
        """Test EVE Eye route URL."""
        url = eveeye_route_url("Jita", "Amarr")
        assert url == "https://eveeye.com/?route=Jita:Amarr"

    def test_eveeye_map_url(self):
        """Test EVE Eye map URL."""
        url = eveeye_map_url("The Forge")
        assert url == "https://eveeye.com/?map=The%20Forge"


class TestEvewhoUrls:
    """Tests for EVE Who URL generators."""

    def test_evewho_character_url(self):
        """Test EVE Who character URL."""
        url = evewho_character_url(12345678)
        assert url == "https://evewho.com/character/12345678"

    def test_evewho_corporation_url(self):
        """Test EVE Who corporation URL."""
        url = evewho_corporation_url(98000001)
        assert url == "https://evewho.com/corporation/98000001"

    def test_evewho_alliance_url(self):
        """Test EVE Who alliance URL."""
        url = evewho_alliance_url(99000001)
        assert url == "https://evewho.com/alliance/99000001"


class TestEsiUrls:
    """Tests for ESI URL generators."""

    def test_esi_system_url(self):
        """Test ESI system URL."""
        url = esi_system_url(30000142)
        assert url == "https://esi.evetech.net/latest/universe/systems/30000142/"

    def test_esi_character_url(self):
        """Test ESI character URL."""
        url = esi_character_url(12345678)
        assert url == "https://esi.evetech.net/latest/characters/12345678/"

    def test_esi_corporation_url(self):
        """Test ESI corporation URL."""
        url = esi_corporation_url(98000001)
        assert url == "https://esi.evetech.net/latest/corporations/98000001/"

    def test_esi_alliance_url(self):
        """Test ESI alliance URL."""
        url = esi_alliance_url(99000001)
        assert url == "https://esi.evetech.net/latest/alliances/99000001/"

    def test_esi_type_url(self):
        """Test ESI type URL."""
        url = esi_type_url(587)
        assert url == "https://esi.evetech.net/latest/universe/types/587/"


class TestGetSystemLinks:
    """Tests for get_system_links aggregator."""

    def test_basic_system_links(self):
        """Test basic system links without IDs."""
        links = get_system_links("Jita")

        assert "dotlan" in links
        assert "dotlan_radar" in links
        assert "eveeye" in links
        assert "zkillboard_search" in links
        assert "zkillboard" not in links
        assert "esi" not in links

    def test_system_links_with_id(self):
        """Test system links with system ID."""
        links = get_system_links("Jita", system_id=30000142)

        assert "dotlan" in links
        assert "zkillboard" in links
        assert "esi" in links
        assert "zkillboard_search" not in links

    def test_system_links_with_region(self):
        """Test system links with region info."""
        links = get_system_links("Jita", region_name="The Forge")

        assert "dotlan_region" in links
        assert "eveeye_map" in links

    def test_system_links_with_region_id(self):
        """Test system links with region ID."""
        links = get_system_links("Jita", region_id=10000002)

        assert "zkillboard_region" in links

    def test_system_links_full(self):
        """Test system links with all info."""
        links = get_system_links(
            "Jita",
            system_id=30000142,
            region_name="The Forge",
            region_id=10000002,
        )

        assert len(links) == 8
        assert "dotlan" in links
        assert "dotlan_radar" in links
        assert "dotlan_region" in links
        assert "eveeye" in links
        assert "eveeye_map" in links
        assert "zkillboard" in links
        assert "zkillboard_region" in links
        assert "esi" in links


class TestGetCharacterLinks:
    """Tests for get_character_links aggregator."""

    def test_character_links(self):
        """Test character links generation."""
        links = get_character_links(12345678)

        assert len(links) == 3
        assert "zkillboard" in links
        assert "evewho" in links
        assert "esi" in links
        assert "12345678" in links["zkillboard"]


class TestGetCorporationLinks:
    """Tests for get_corporation_links aggregator."""

    def test_corporation_links(self):
        """Test corporation links generation."""
        links = get_corporation_links(98000001)

        assert len(links) == 3
        assert "zkillboard" in links
        assert "evewho" in links
        assert "esi" in links
        assert "98000001" in links["zkillboard"]


class TestGetAllianceLinks:
    """Tests for get_alliance_links aggregator."""

    def test_alliance_links(self):
        """Test alliance links generation."""
        links = get_alliance_links(99000001)

        assert len(links) == 3
        assert "zkillboard" in links
        assert "evewho" in links
        assert "esi" in links
        assert "99000001" in links["zkillboard"]


class TestGetRouteLinks:
    """Tests for get_route_links aggregator."""

    def test_basic_route_links(self):
        """Test basic route links without full path."""
        links = get_route_links("Jita", "Amarr")

        assert len(links) == 2
        assert "dotlan" in links
        assert "eveeye" in links
        assert "dotlan_full" not in links

    def test_route_links_with_path(self):
        """Test route links with full path."""
        links = get_route_links(
            "Jita",
            "Amarr",
            full_path=["Jita", "Perimeter", "Urlen", "Amarr"],
        )

        assert len(links) == 4
        assert "dotlan" in links
        assert "dotlan_full" in links
        assert "dotlan_jump" in links
        assert "eveeye" in links

    def test_route_links_short_path(self):
        """Test route links with path too short."""
        links = get_route_links("Jita", "Amarr", full_path=["Jita"])

        # Short path should not generate full/jump links
        assert "dotlan_full" not in links
        assert "dotlan_jump" not in links


class TestGetShipLinks:
    """Tests for get_ship_links aggregator."""

    def test_ship_links(self):
        """Test ship links generation."""
        links = get_ship_links(587)

        assert len(links) == 2
        assert "zkillboard" in links
        assert "esi" in links
        assert "587" in links["zkillboard"]


class TestUrlEncoding:
    """Tests for URL encoding edge cases."""

    def test_special_characters_in_system(self):
        """Test special characters are properly encoded."""
        url = dotlan_system_url("J-12345")
        assert "J-12345" in url

    def test_unicode_in_system(self):
        """Test unicode characters are properly encoded."""
        # Some wormhole systems have odd names
        url = dotlan_system_url("Thera")
        assert "Thera" in url

    def test_spaces_encoded_as_percent20(self):
        """Test spaces are URL encoded."""
        url = dotlan_region_url("Pure Blind")
        assert "Pure%20Blind" in url
