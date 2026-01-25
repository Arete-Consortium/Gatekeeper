"""Unit tests for route bookmarks API."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.api.v1.bookmarks import (
    _bookmark_to_response,
    create_bookmark,
    delete_bookmark,
    get_bookmark,
    list_bookmarks,
    update_bookmark,
)
from backend.app.api.v1.dependencies import AuthenticatedCharacter
from backend.app.db.models import RouteBookmark
from backend.app.models.bookmark import BookmarkCreate, BookmarkUpdate


@pytest.fixture
def mock_character():
    """Create a mock authenticated character."""
    return AuthenticatedCharacter(
        character_id=12345,
        character_name="Test Pilot",
        access_token="test-token",
        scopes=["esi-location.read_location.v1"],
        expires_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_universe():
    """Create a mock universe with test systems."""
    mock = MagicMock()
    mock.systems = {
        "Jita": MagicMock(id=30000142),
        "Amarr": MagicMock(id=30002187),
        "Dodixie": MagicMock(id=30002659),
        "Rens": MagicMock(id=30002510),
    }
    return mock


@pytest.fixture
def mock_risk_config():
    """Create a mock risk configuration."""
    mock = MagicMock()
    mock.routing_profiles = {
        "shortest": {},
        "safer": {},
        "paranoid": {},
    }
    return mock


@pytest.fixture
def sample_bookmark():
    """Create a sample bookmark model."""
    bookmark = MagicMock(spec=RouteBookmark)
    bookmark.id = 1
    bookmark.character_id = 12345
    bookmark.name = "Trade Route"
    bookmark.from_system = "Jita"
    bookmark.to_system = "Amarr"
    bookmark.profile = "safer"
    bookmark.avoid_systems = json.dumps(["Rancer", "Tama"])
    bookmark.use_bridges = False
    bookmark.notes = "Main trade run"
    bookmark.created_at = datetime.now(UTC)
    bookmark.updated_at = datetime.now(UTC)
    return bookmark


class TestBookmarkToResponse:
    """Tests for _bookmark_to_response helper."""

    def test_converts_bookmark_to_response(self, sample_bookmark):
        """Test converting a bookmark model to response."""
        response = _bookmark_to_response(sample_bookmark)

        assert response.id == 1
        assert response.character_id == 12345
        assert response.name == "Trade Route"
        assert response.from_system == "Jita"
        assert response.to_system == "Amarr"
        assert response.profile == "safer"
        assert response.avoid_systems == ["Rancer", "Tama"]
        assert response.use_bridges is False
        assert response.notes == "Main trade run"

    def test_handles_null_avoid_systems(self, sample_bookmark):
        """Test handling null avoid_systems."""
        sample_bookmark.avoid_systems = None
        response = _bookmark_to_response(sample_bookmark)

        assert response.avoid_systems == []

    def test_handles_invalid_json_avoid_systems(self, sample_bookmark):
        """Test handling invalid JSON in avoid_systems."""
        sample_bookmark.avoid_systems = "not valid json"
        response = _bookmark_to_response(sample_bookmark)

        assert response.avoid_systems == []

    def test_handles_empty_avoid_systems(self, sample_bookmark):
        """Test handling empty avoid_systems."""
        sample_bookmark.avoid_systems = json.dumps([])
        response = _bookmark_to_response(sample_bookmark)

        assert response.avoid_systems == []


class TestListBookmarks:
    """Tests for list_bookmarks endpoint."""

    @pytest.mark.asyncio
    async def test_list_bookmarks_returns_all(self, mock_character, sample_bookmark):
        """Test listing all bookmarks for a character."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_bookmark]
        mock_db.execute.return_value = mock_result

        response = await list_bookmarks(mock_character, mock_db)

        assert response.total == 1
        assert len(response.bookmarks) == 1
        assert response.bookmarks[0].name == "Trade Route"

    @pytest.mark.asyncio
    async def test_list_bookmarks_empty(self, mock_character):
        """Test listing bookmarks when none exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        response = await list_bookmarks(mock_character, mock_db)

        assert response.total == 0
        assert response.bookmarks == []


class TestCreateBookmark:
    """Tests for create_bookmark endpoint."""

    @pytest.mark.asyncio
    async def test_create_bookmark_success(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test creating a bookmark successfully."""
        request = BookmarkCreate(
            name="New Route",
            from_system="Jita",
            to_system="Amarr",
            profile="shortest",
            avoid_systems=[],
            use_bridges=False,
        )

        mock_db = AsyncMock()

        async def fake_refresh(obj):
            obj.id = 1
            obj.character_id = mock_character.character_id
            obj.created_at = datetime.now(UTC)
            obj.updated_at = datetime.now(UTC)

        mock_db.refresh = fake_refresh

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            response = await create_bookmark(request, mock_character, mock_db)

        assert response.name == "New Route"
        assert response.from_system == "Jita"
        assert response.to_system == "Amarr"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_bookmark_unknown_from_system(
        self, mock_character, mock_universe, mock_risk_config
    ):
        """Test creating bookmark with unknown from_system."""
        request = BookmarkCreate(
            name="Bad Route",
            from_system="FakeSystem",
            to_system="Amarr",
        )

        mock_db = AsyncMock()

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await create_bookmark(request, mock_character, mock_db)

        assert "Unknown system: FakeSystem" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_bookmark_unknown_to_system(
        self, mock_character, mock_universe, mock_risk_config
    ):
        """Test creating bookmark with unknown to_system."""
        request = BookmarkCreate(
            name="Bad Route",
            from_system="Jita",
            to_system="FakeSystem",
        )

        mock_db = AsyncMock()

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await create_bookmark(request, mock_character, mock_db)

        assert "Unknown system: FakeSystem" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_bookmark_invalid_profile(
        self, mock_character, mock_universe, mock_risk_config
    ):
        """Test creating bookmark with invalid profile."""
        request = BookmarkCreate(
            name="Bad Route",
            from_system="Jita",
            to_system="Amarr",
            profile="invalid_profile",
        )

        mock_db = AsyncMock()

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await create_bookmark(request, mock_character, mock_db)

        assert "Unknown profile" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_bookmark_invalid_avoid_system(
        self, mock_character, mock_universe, mock_risk_config
    ):
        """Test creating bookmark with invalid avoid system."""
        request = BookmarkCreate(
            name="Bad Route",
            from_system="Jita",
            to_system="Amarr",
            avoid_systems=["FakeSystem"],
        )

        mock_db = AsyncMock()

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await create_bookmark(request, mock_character, mock_db)

        assert "Unknown avoid system: FakeSystem" in str(exc_info.value.detail)


class TestGetBookmark:
    """Tests for get_bookmark endpoint."""

    @pytest.mark.asyncio
    async def test_get_bookmark_success(self, mock_character, sample_bookmark):
        """Test getting a bookmark successfully."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        response = await get_bookmark(1, mock_character, mock_db)

        assert response.id == 1
        assert response.name == "Trade Route"

    @pytest.mark.asyncio
    async def test_get_bookmark_not_found(self, mock_character):
        """Test getting a non-existent bookmark."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(Exception) as exc_info:
            await get_bookmark(999, mock_character, mock_db)

        assert "Bookmark not found" in str(exc_info.value.detail)


class TestUpdateBookmark:
    """Tests for update_bookmark endpoint."""

    @pytest.mark.asyncio
    async def test_update_bookmark_name(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark name."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(name="Updated Name")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert sample_bookmark.name == "Updated Name"
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_bookmark_from_system(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark from_system."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(from_system="Dodixie")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert sample_bookmark.from_system == "Dodixie"

    @pytest.mark.asyncio
    async def test_update_bookmark_invalid_from_system(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark with invalid from_system."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(from_system="FakeSystem")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert "Unknown system: FakeSystem" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_bookmark_not_found(self, mock_character, mock_universe, mock_risk_config):
        """Test updating non-existent bookmark."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(name="New Name")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await update_bookmark(999, request, mock_character, mock_db)

        assert "Bookmark not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_bookmark_profile(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark profile."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(profile="paranoid")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert sample_bookmark.profile == "paranoid"

    @pytest.mark.asyncio
    async def test_update_bookmark_invalid_profile(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark with invalid profile."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(profile="invalid")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert "Unknown profile" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_bookmark_avoid_systems(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark avoid_systems."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(avoid_systems=["Dodixie"])

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert sample_bookmark.avoid_systems == json.dumps(["Dodixie"])

    @pytest.mark.asyncio
    async def test_update_bookmark_to_system(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark to_system."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(to_system="Rens")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert sample_bookmark.to_system == "Rens"

    @pytest.mark.asyncio
    async def test_update_bookmark_invalid_to_system(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark with invalid to_system."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(to_system="FakeSystem")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert "Unknown system: FakeSystem" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_bookmark_invalid_avoid_system(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark with invalid avoid system."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(avoid_systems=["FakeSystem"])

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
            pytest.raises(Exception) as exc_info,
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert "Unknown avoid system: FakeSystem" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_bookmark_use_bridges(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark use_bridges."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(use_bridges=True)

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert sample_bookmark.use_bridges is True

    @pytest.mark.asyncio
    async def test_update_bookmark_notes(
        self, mock_character, mock_universe, mock_risk_config, sample_bookmark
    ):
        """Test updating bookmark notes."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        request = BookmarkUpdate(notes="Updated notes")

        with (
            patch("backend.app.api.v1.bookmarks.load_universe", return_value=mock_universe),
            patch("backend.app.api.v1.bookmarks.load_risk_config", return_value=mock_risk_config),
        ):
            await update_bookmark(1, request, mock_character, mock_db)

        assert sample_bookmark.notes == "Updated notes"


class TestDeleteBookmark:
    """Tests for delete_bookmark endpoint."""

    @pytest.mark.asyncio
    async def test_delete_bookmark_success(self, mock_character, sample_bookmark):
        """Test deleting a bookmark successfully."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_bookmark
        mock_db.execute.return_value = mock_result

        await delete_bookmark(1, mock_character, mock_db)

        mock_db.delete.assert_called_once_with(sample_bookmark)

    @pytest.mark.asyncio
    async def test_delete_bookmark_not_found(self, mock_character):
        """Test deleting non-existent bookmark."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(Exception) as exc_info:
            await delete_bookmark(999, mock_character, mock_db)

        assert "Bookmark not found" in str(exc_info.value.detail)


class TestBookmarkModels:
    """Tests for Pydantic bookmark models."""

    def test_bookmark_create_minimal(self):
        """Test creating bookmark with minimal fields."""
        bookmark = BookmarkCreate(
            name="Test",
            from_system="Jita",
            to_system="Amarr",
        )

        assert bookmark.name == "Test"
        assert bookmark.profile == "shortest"
        assert bookmark.avoid_systems == []
        assert bookmark.use_bridges is False
        assert bookmark.notes is None

    def test_bookmark_create_full(self):
        """Test creating bookmark with all fields."""
        bookmark = BookmarkCreate(
            name="Full Test",
            from_system="Jita",
            to_system="Amarr",
            profile="paranoid",
            avoid_systems=["Rancer"],
            use_bridges=True,
            notes="Test notes",
        )

        assert bookmark.name == "Full Test"
        assert bookmark.profile == "paranoid"
        assert bookmark.avoid_systems == ["Rancer"]
        assert bookmark.use_bridges is True
        assert bookmark.notes == "Test notes"

    def test_bookmark_update_partial(self):
        """Test partial update model."""
        update = BookmarkUpdate(name="New Name")

        assert update.name == "New Name"
        assert update.from_system is None
        assert update.to_system is None
        assert update.profile is None
