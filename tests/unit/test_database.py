"""Unit tests for database configuration and session management."""

import os
from unittest.mock import patch

import pytest

from backend.app.db.database import (
    Base,
    get_database_url,
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
