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

    # zKillboard
    ZKILL_BASE_URL: str = "https://zkillboard.com/api"
    ZKILL_USER_AGENT: str = "EVE_Gatekeeper/1.0"
    ZKILL_REDISQ_URL: str = "https://redisq.zkillboard.com/listen.php"

    # Redis Cache
    REDIS_URL: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "console"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100

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
