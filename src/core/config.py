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
    model_config = SettingsConfigDict(
        env_file="../../.env", env_ignore_empty=True, extra="ignore"
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = (
        60 * 24 * 8
    )  # 60 minutes * 24 hours * 8 days = 8 days

    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    PROJECT_TITLE: str = ""

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []
    ALLOWED_HOSTS: Annotated[list[AnyUrl] | list[str], BeforeValidator(parse_cors)] = []

    db: DataBaseSettings = DataBaseSettings(_env_prefix="postgres_")
    redis: RedisSettings = RedisSettings(_env_prefix="redis_")

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MEDIA_PATH: str = os.path.join(BASE_DIR, "media")

    MODELS_FILE_NAME: str = "models.py"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_hosts_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.ALLOWED_HOSTS]


settings = Settings()
