"""Pytest configuration and fixtures for EVE Gatekeeper tests."""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///./test_eve_gatekeeper.db"
os.environ["REDIS_URL"] = ""  # Disable Redis for tests
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["DEBUG"] = "true"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def app():
    """Create the FastAPI application for testing."""
    from backend.app.main import app

    return app


@pytest.fixture
def test_client(app) -> Generator:
    """Create a synchronous test client."""
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_systems() -> dict:
    """Sample system data for testing."""
    return {
        "Jita": {
            "id": 30000142,
            "name": "Jita",
            "region_id": 10000002,
            "security": 0.95,
            "category": "highsec",
        },
        "Perimeter": {
            "id": 30000144,
            "name": "Perimeter",
            "region_id": 10000002,
            "security": 0.90,
            "category": "highsec",
        },
        "Amarr": {
            "id": 30002187,
            "name": "Amarr",
            "region_id": 10000043,
            "security": 1.0,
            "category": "highsec",
        },
        "Rancer": {
            "id": 30003068,
            "name": "Rancer",
            "region_id": 10000030,
            "security": 0.4,
            "category": "lowsec",
        },
        "HED-GP": {
            "id": 30001161,
            "name": "HED-GP",
            "region_id": 10000014,
            "security": -0.35,
            "category": "nullsec",
        },
    }


@pytest.fixture
def sample_kill_data() -> dict:
    """Sample kill data from zKillboard."""
    return {
        "kill_id": 123456789,
        "solar_system_id": 30000142,
        "solar_system_name": "Jita",
        "region_id": 10000002,
        "kill_time": "2025-01-01T12:00:00Z",
        "ship_type_id": 17736,  # Typhoon
        "is_pod": False,
        "victim_corporation_id": 98000001,
        "victim_alliance_id": 99000001,
        "attacker_count": 5,
        "total_value": 500000000.0,
        "points": 100,
        "npc": False,
        "solo": False,
        "risk_score": 0.85,
    }


@pytest.fixture
def sample_pod_kill_data(sample_kill_data) -> dict:
    """Sample pod kill data."""
    return {
        **sample_kill_data,
        "kill_id": 123456790,
        "ship_type_id": 670,  # Capsule
        "is_pod": True,
        "total_value": 50000000.0,
    }


@pytest.fixture
def mock_universe_data(sample_systems) -> dict:
    """Mock universe data structure."""
    return {
        "metadata": {
            "version": "1.0.0",
            "source": "test",
            "last_updated": "2025-01-01T00:00:00Z",
        },
        "systems": sample_systems,
        "gates": [
            {"from_system": "Jita", "to_system": "Perimeter", "distance": 1.0},
            {"from_system": "Perimeter", "to_system": "Jita", "distance": 1.0},
        ],
    }


@pytest.fixture
def mock_risk_config() -> dict:
    """Mock risk configuration."""
    return {
        "security_category_weights": {
            "highsec": 0.1,
            "lowsec": 0.5,
            "nullsec": 0.8,
            "wh": 0.7,
        },
        "kill_weights": {
            "recent_kills": 0.05,
            "recent_pods": 0.1,
        },
        "clamp": {
            "min": 0,
            "max": 100,
        },
        "risk_colors": {
            "safe": "#00FF00",
            "moderate": "#FFFF00",
            "dangerous": "#FF0000",
        },
        "map_layers": {
            "gates": True,
            "risk": True,
            "sovereignty": False,
        },
        "routing_profiles": {
            "shortest": {"risk_weight": 0},
            "safer": {"risk_weight": 0.5},
            "paranoid": {"risk_weight": 1.0},
        },
    }


# Cleanup after tests
@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test resources after each test."""
    yield
    # Clear lru_cache singletons to prevent cross-test pollution
    from backend.app.services.data_loader import load_risk_config, load_universe

    load_universe.cache_clear()
    load_risk_config.cache_clear()

    # Clean up test database
    test_db = "./test_eve_gatekeeper.db"
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except PermissionError:
            pass
