"""Runtime configuration, read from the environment (or a local .env file)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    #: Any SQLAlchemy URL. The default keeps a clean checkout runnable with no
    #: infrastructure; docker compose points this at PostgreSQL.
    database_url: str = "sqlite+pysqlite:///./accommodation.db"
    #: Comma-separated list of browser origins allowed to call the API.
    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    sql_echo: bool = False
    log_level: str = "INFO"
    #: Create tables on startup. Convenient locally; a real deployment runs
    #: migrations instead (see README, "Schema management").
    auto_create_schema: bool = True

    @property
    def allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
