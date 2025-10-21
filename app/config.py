"""Configuration helpers for the staging backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal


@dataclass(slots=True)
class Settings:
    """Runtime settings sourced from environment variables."""

    environment: Literal["local", "staging", "production"] = "staging"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_assistant_id: str | None = None
    cors_allow_origins: tuple[str, ...] = ("http://localhost:3000",)
    data_directory: Path = Path("./data")
    database_path: Path = Path("./data/metadata.db")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached runtime settings."""
    cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    origins: tuple[str, ...]
    if cors_origins:
        origins = tuple(origin.strip() for origin in cors_origins.split(",") if origin.strip())
    else:
        origins = Settings.cors_allow_origins

    data_dir = Path(os.getenv("DATA_DIRECTORY", Settings.data_directory.as_posix())).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    database_path_str = os.getenv("DATABASE_PATH")
    if database_path_str:
        database_path = Path(database_path_str).expanduser()
        database_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        database_path = data_dir / "metadata.db"

    return Settings(
        environment=os.getenv("ENVIRONMENT", Settings.environment),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL", Settings.openai_base_url),
        openai_assistant_id=os.getenv("OPENAI_ASSISTANT_ID"),
        cors_allow_origins=origins,
        data_directory=data_dir,
        database_path=database_path,
    )
