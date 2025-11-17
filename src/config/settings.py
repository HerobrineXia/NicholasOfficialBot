from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SETTINGS_FILE = PROJECT_ROOT / "config" / "settings.yaml"


def _load_env_file(path: Path, override: bool = False) -> None:
    if path.exists():
        load_dotenv(path, override=override)


def _initialize_environment() -> None:
    _load_env_file(PROJECT_ROOT / ".env", override=False)
    _load_env_file(PROJECT_ROOT / ".env.local", override=True)


_initialize_environment()


class Settings(BaseSettings):
    """Central application settings loaded from YAML + .env files."""

    environment: str = Field(default="prod", alias="ENVIRONMENT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")
    command_start: tuple[str, ...] = Field(default_factory=lambda: ("/",), alias="COMMAND_START")
    command_sep: tuple[str, ...] = Field(default_factory=lambda: ("-",), alias="COMMAND_SEP")
    driver: str = Field(default="~fastapi+~httpx+~websockets", alias="DRIVER")
    qq_is_sandbox: bool = Field(default=True, alias="QQ_IS_SANDBOX")
    config_file: str = Field(default="config/settings.yaml", alias="SETTINGS_FILE", exclude=True)

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            cls.yaml_config_settings_source,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @staticmethod
    def yaml_config_settings_source() -> Dict[str, Any]:
        """Read structured defaults from config/settings.yaml."""

        file_value = os.getenv("SETTINGS_FILE")
        candidate = Path(file_value) if file_value else DEFAULT_SETTINGS_FILE
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        if not candidate.exists():
            return {}
        with candidate.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        return data

    def model_post_init(self, __context: Any) -> None:
        # Ensure command delimiters are tuples for downstream consumers.
        self.command_start = tuple(self.command_start or ("/",))
        self.command_sep = tuple(self.command_sep or ("-",))

    @field_validator("command_start", "command_sep", mode="before")
    @classmethod
    def _parse_sequence(cls, value: Any):
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return value
            if isinstance(parsed, (list, tuple)):
                return tuple(parsed)
        return value


def _load_json_env(env_key: str) -> Dict[str, Any] | None:
    raw_value = os.getenv(env_key)
    if not raw_value:
        return None
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse JSON from %s: %s", env_key, exc)
        return None


def load_config_section(section: str) -> Dict[str, Any]:
    """Return a config section from settings.yaml (empty dict if missing)."""
    data = Settings.yaml_config_settings_source()
    return data.get(section, {}) if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = [
    "Settings",
    "get_settings",
    "load_config_section",
    "_load_json_env",
]
