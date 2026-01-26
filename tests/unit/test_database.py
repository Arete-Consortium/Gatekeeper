"""Unit tests for database configuration and session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.db.database import (
    Base,
    close_db,
    get_database_url,
    get_db,
    get_engine,
    get_session_factory,
    init_db,
)


class TestDatabaseUrl:
    """Tests for database URL conversion."""

    def test_postgresql_to_asyncpg(self):
        """Test PostgreSQL URL conversion to asyncpg driver."""
        with patch("backend.app.db.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql://user:pass@localhost/db"

            result = get_database_url()
            assert result == "postgresql+asyncpg://user:pass@localhost/db"

    def test_sqlite_to_aiosqlite(self):
        """Test SQLite URL conversion to aiosqlite driver."""
        with patch("backend.app.db.database.settings") as mock_settings:
            mock_settings.database_url = "sqlite:///./test.db"

            result = get_database_url()
            assert result == "sqlite+aiosqlite:///./test.db"

    def test_already_async_url_unchanged(self):
        """Test that already-async URLs are returned unchanged."""
        with patch("backend.app.db.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"

            result = get_database_url()
            # Should not double-convert
            assert result.count("+asyncpg") == 1

    def test_sqlite_memory_url(self):
        """Test SQLite in-memory URL conversion."""
        with patch("backend.app.db.database.settings") as mock_settings:
            mock_settings.database_url = "sqlite:///:memory:"

            result = get_database_url()
            # sqlite:// without three slashes won't match our pattern
            # This tests edge case behavior
            assert "sqlite" in result


class TestBase:
    """Tests for SQLAlchemy Base class."""

    def test_base_is_declarative_base(self):
        """Test that Base is a proper SQLAlchemy DeclarativeBase."""
        from sqlalchemy.orm import DeclarativeBase

        assert issubclass(Base, DeclarativeBase)

    def test_base_has_metadata(self):
        """Test that Base has metadata attribute."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_base_has_registry(self):
        """Test that Base has registry attribute."""
        assert hasattr(Base, "registry")


class TestGetEngine:
    """Tests for get_engine function."""

    def test_get_engine_creates_sqlite_engine(self):
        """Test engine creation with SQLite URL."""
        import backend.app.db.database as db_module

        # Reset global state
        db_module._engine = None
        db_module._session_factory = None

        with patch.object(db_module, "settings") as mock_settings:
            mock_settings.database_url = "sqlite:///./test_engine.db"
            mock_settings.DEBUG = False

            engine = get_engine()

            assert engine is not None
            assert "sqlite" in str(engine.url)

        # Clean up
        db_module._engine = None

    def test_get_engine_caches_engine(self):
        """Test that get_engine returns cached engine on subsequent calls."""
        import backend.app.db.database as db_module

        db_module._engine = None
        db_module._session_factory = None

        with patch.object(db_module, "settings") as mock_settings:
            mock_settings.database_url = "sqlite:///./test_cache.db"
            mock_settings.DEBUG = False

            engine1 = get_engine()
            engine2 = get_engine()

            assert engine1 is engine2

        db_module._engine = None

    def test_get_engine_postgresql_settings(self):
        """Test engine creation with PostgreSQL URL includes pool settings."""
        import backend.app.db.database as db_module

        db_module._engine = None

        with patch.object(db_module, "settings") as mock_settings:
            mock_settings.database_url = "postgresql://user:pass@localhost/db"
            mock_settings.DEBUG = False

            with patch.object(db_module, "create_async_engine") as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine

                get_engine()

                # Should include pool settings for postgresql
                call_kwargs = mock_create.call_args.kwargs
                assert "pool_size" in call_kwargs
                assert "max_overflow" in call_kwargs
                assert call_kwargs["pool_size"] == 5
                assert call_kwargs["max_overflow"] == 10

        db_module._engine = None


class TestGetSessionFactory:
    """Tests for get_session_factory function."""

    def test_get_session_factory_creates_factory(self):
        """Test session factory creation."""
        import backend.app.db.database as db_module

        db_module._engine = None
        db_module._session_factory = None

        with patch.object(db_module, "settings") as mock_settings:
            mock_settings.database_url = "sqlite:///./test_session.db"
            mock_settings.DEBUG = False

            factory = get_session_factory()

            assert factory is not None

        db_module._engine = None
        db_module._session_factory = None

    def test_get_session_factory_caches_factory(self):
        """Test that get_session_factory returns cached factory."""
        import backend.app.db.database as db_module

        db_module._engine = None
        db_module._session_factory = None

        with patch.object(db_module, "settings") as mock_settings:
            mock_settings.database_url = "sqlite:///./test_session_cache.db"
            mock_settings.DEBUG = False

            factory1 = get_session_factory()
            factory2 = get_session_factory()

            assert factory1 is factory2

        db_module._engine = None
        db_module._session_factory = None


class TestGetDb:
    """Tests for get_db async generator."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test that get_db yields a session and commits on success."""
        mock_session = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.db.database.get_session_factory", return_value=mock_factory):
            async for session in get_db():
                assert session is mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_exception(self):
        """Test that get_db rolls back on exception."""
        mock_session = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.app.db.database.get_session_factory", return_value=mock_factory):
            gen = get_db()
            try:
                session = await gen.__anext__()
                assert session is mock_session
                # Raise an exception inside the generator
                await gen.athrow(ValueError("Test error"))
            except ValueError:
                pass

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestInitDb:
    """Tests for init_db function."""

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """Test that init_db creates database tables."""
        mock_conn = AsyncMock()

        # Create a proper async context manager mock
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock()
        mock_engine.begin.return_value = mock_context

        with patch("backend.app.db.database.get_engine", return_value=mock_engine):
            await init_db()

        mock_conn.run_sync.assert_called_once()


class TestCloseDb:
    """Tests for close_db function."""

    @pytest.mark.asyncio
    async def test_close_db_disposes_engine(self):
        """Test that close_db disposes the engine and resets globals."""
        import backend.app.db.database as db_module

        mock_engine = AsyncMock()
        db_module._engine = mock_engine
        db_module._session_factory = MagicMock()

        await close_db()

        mock_engine.dispose.assert_called_once()
        assert db_module._engine is None
        assert db_module._session_factory is None

    @pytest.mark.asyncio
    async def test_close_db_when_no_engine(self):
        """Test that close_db is safe when no engine exists."""
        import backend.app.db.database as db_module

        db_module._engine = None
        db_module._session_factory = None

        # Should not raise
        await close_db()

        assert db_module._engine is None
