from __future__ import annotations

import dataclasses
from typing import List

from pydantic import Field
from pydantic.dataclasses import dataclass

from config.config import DefaultPluginConfig as DConfig
from config.settings import load_config_section, _load_json_env


@dataclass
class ModelData:
    models: List[str] = dataclasses.field(default_factory=list)
    preset: List[str] = dataclasses.field(default_factory=list)
    base_url: str = ""
    max_input_tokens: List[int] = dataclasses.field(default_factory=list)
    max_output_tokens: List[int] = dataclasses.field(default_factory=list)
    extra: dict[str, str] = dataclasses.field(default_factory=dict)


@dataclass
class KeyData:
    key: str = ""


class ChatConfig(DConfig):
    model: dict[str, ModelData] = Field(default_factory=dict)
    key: dict[str, KeyData] = Field(default_factory=dict)
    default_model: str = ""


def get_config() -> ChatConfig:
    """Load chat plugin config, isolated from the global settings model."""
    payload = load_config_section("chat") or {}
    config = ChatConfig(**payload) if isinstance(payload, dict) else ChatConfig()

    # Env-based overrides (only for model/key).
    if env_models := _load_json_env("CHAT__MODEL"):
        config.model = {name: ModelData(**p) for name, p in env_models.items()}
    if env_keys := _load_json_env("CHAT__KEY"):
        config.key = {name: KeyData(**p) for name, p in env_keys.items()}

    return config


__all__ = ["ChatConfig", "ModelData", "KeyData", "get_config"]
