import warnings
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Project Info
    PROJECT_NAME: str = "EVE Gatekeeper"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_BASE_URL: str | None = None  # Base URL for generating links (e.g., session join URLs)

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parents[2]
    DATA_DIR: Path = BASE_DIR / "app" / "data"
    UNIVERSE_FILE: Path = DATA_DIR / "universe.json"
    RISK_CONFIG_FILE: Path = DATA_DIR / "risk_config.json"

    # Database
    DATABASE_URL: str = "sqlite:///./eve_gatekeeper.db"
    POSTGRES_URL: str | None = None

    # ESI (EVE Swagger Interface)
    ESI_BASE_URL: str = "https://esi.evetech.net/latest"
    ESI_CLIENT_ID: str | None = None
    ESI_SECRET_KEY: str | None = None
    ESI_CALLBACK_URL: str = "http://localhost:8000/callback"
    ESI_USER_AGENT: str = "EVE_Gatekeeper/1.0 (https://github.com/AreteDriver/EVE_Gatekeeper)"
    ESI_CONCURRENCY_LIMIT: int = 20  # Max concurrent ESI requests
    ESI_TIMEOUT: float = 30.0  # ESI request timeout in seconds

    # zKillboard
    ZKILL_BASE_URL: str = "https://zkillboard.com/api"
    ZKILL_USER_AGENT: str = "EVE_Gatekeeper/1.0"
    ZKILL_REDISQ_URL: str = "https://redisq.zkillboard.com/listen.php"

    # WebSocket Reconnection
    WS_INITIAL_RETRY_DELAY: float = 1.0  # Initial delay in seconds
    WS_MAX_RETRY_DELAY: float = 60.0  # Maximum delay between retries
    WS_RETRY_MULTIPLIER: float = 2.0  # Exponential backoff multiplier
    WS_MAX_RETRY_ATTEMPTS: int = 0  # 0 = unlimited retries
    WS_HEALTH_CHECK_INTERVAL: float = 30.0  # Health check ping interval in seconds
    WS_CONNECTION_TIMEOUT: float = 10.0  # Connection timeout in seconds

    # Redis Cache
    REDIS_URL: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "console"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100  # Default for unauthenticated (IP-based)
    RATE_LIMIT_PER_MINUTE_USER: int = 200  # Per authenticated user (character_id)
    RATE_LIMIT_PER_MINUTE_APIKEY: int = 300  # Per API key

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Security
    API_KEY_ENABLED: bool = False
    API_KEY: str | None = None
    SECRET_KEY: str = "change-me-in-production"

    # Monitoring
    SENTRY_DSN: str | None = None
    METRICS_ENABLED: bool = True

    # Webhooks (Discord/Slack)
    DISCORD_WEBHOOK_URL: str | None = None
    SLACK_WEBHOOK_URL: str | None = None
    WEBHOOK_TIMEOUT: int = 10  # seconds

    # Cache TTLs (in seconds)
    CACHE_TTL_ESI: int = 300  # 5 minutes
    CACHE_TTL_ROUTE: int = 600  # 10 minutes
    CACHE_TTL_RISK: int = 120  # 2 minutes

    # Universe Data Refresh
    UNIVERSE_REFRESH_ENABLED: bool = True
    UNIVERSE_REFRESH_INTERVAL_HOURS: int = 24  # Refresh every 24 hours
    UNIVERSE_REFRESH_ON_STARTUP: bool = False  # Check for refresh on startup

    # Kill Data Aging
    KILL_HISTORY_ENABLED: bool = True
    KILL_HISTORY_MAX_AGE_HOURS: int = 24  # Maximum age of stored kills (default 24 hours)
    KILL_HISTORY_MAX_ENTRIES: int = 10000  # Maximum number of kills to store
    KILL_HISTORY_CLEANUP_INTERVAL_MINUTES: int = 15  # How often to run cleanup

    # Redis Pub/Sub (for multi-instance deployments)
    REDIS_PUBSUB_ENABLED: bool = True  # Auto-enabled if REDIS_URL is set
    REDIS_PUBSUB_CHANNEL: str = "eve_gatekeeper:kills"  # Channel name for kill events

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            warnings.warn(
                f"SECRET_KEY should be at least 32 characters (got {len(v)})",
                stacklevel=2,
            )
        if v == "change-me-in-production":
            warnings.warn(
                "SECRET_KEY using default value - insecure for production!",
                stacklevel=2,
            )
        return v

    @model_validator(mode="after")
    def enforce_production_security(self):
        if self.is_production:
            if self.SECRET_KEY == "change-me-in-production":
                raise ValueError("SECRET_KEY must be changed from default in production")
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    f"SECRET_KEY must be at least 32 characters in production (got {len(self.SECRET_KEY)})"
                )
        return self

    @property
    def database_url(self) -> str:
        """Return PostgreSQL URL if available, else SQLite."""
        return self.POSTGRES_URL or self.DATABASE_URL

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.DEBUG


settings = Settings()
