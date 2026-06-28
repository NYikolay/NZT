import os
from pathlib import Path
import secrets
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    PostgresDsn,
    computed_field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


INSTALLED_APPS = [
    "src.domain.users",
    "src.domain.memory",
]


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v

    raise ValueError(v)


class DataBaseSettings(BaseSettings):
    host: str
    port: int = 5432
    password: str = ""
    name: str = ""
    user: str

    POOL_SIZE: int = 10
    """Number of persistent connections in the pool."""

    MAX_OVERFLOW: int = 20
    """Additional connections allowed beyond pool_size."""

    POOL_RECYCLE: int = 3600
    """Recycle connections after this many seconds to prevent stale connections."""

    ECHO: bool = False
    """If True, emit SQL statements to logs (useful for debugging)."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            path=self.name,
        )


class RedisSettings(BaseSettings):
    host: str
    port: int
    db: int


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file="../../.env", env_ignore_empty=True, extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    """API version prefix. Default: /api/v1."""

    SECRET_KEY: str = secrets.token_urlsafe(32)
    """Secret key for JWT signing. Auto-generated if not set via SECRET_KEY env var."""

    BOT_SECRET_TOKEN: str
    """Bot secret token for Telegram authentication. Required."""

    LOG_FORMAT: str
    """Log output format. Options: json, console. Required."""

    LOG_LEVEL: str
    """Logging level. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL. Required."""

    LOG_FILE: str
    """Path to the log file. Required."""

    LOG_ROTATION: str
    """Log rotation strategy. Options: DAILY, or size-based. Required."""

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    """JWT access token expiration in minutes. Default: 8 days (60 min * 24 h * 8 d)."""

    OPEN_ROUTER_API_KEY: str
    """API key for OpenRouter LLM gateway. Required."""

    ENVIRONMENT: Literal["local", "staging", "production"]
    """Deployment environment. One of: local, staging, production. Required."""

    PROJECT_TITLE: str
    """Application title displayed in OpenAPI docs. Required."""

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)]
    """List of allowed CORS origins. Required."""

    ALLOWED_HOSTS: Annotated[list[AnyUrl] | list[str], BeforeValidator(parse_cors)]
    """List of allowed host headers. Required."""

    db: DataBaseSettings = DataBaseSettings(_env_prefix="postgres_")
    """PostgreSQL database connection settings."""

    redis: RedisSettings = RedisSettings(_env_prefix="redis_")
    """Redis connection settings."""

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    """Absolute path to the project root directory. Derived automatically."""

    MEDIA_PATH: str = os.path.join(BASE_DIR, "media")
    """Path to media storage directory. Derived from BASE_DIR."""

    MODELS_FILE_NAME: str = "models.py"
    """Filename pattern for auto-discovering SQLAlchemy models. Default: models.py."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """Stripped list of CORS origins without trailing slashes."""
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_hosts_origins(self) -> list[str]:
        """Stripped list of allowed hosts without trailing slashes."""
        return [str(origin).rstrip("/") for origin in self.ALLOWED_HOSTS]


settings = Settings()
