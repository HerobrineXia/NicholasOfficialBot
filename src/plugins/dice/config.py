from pydantic import Field
from config.config import DefaultPluginConfig
from config.settings import load_config_section


class DiceConfig(DefaultPluginConfig):
    default_sides: int = Field(default=20)
    max_sides: int = Field(default=100)
    max_repeat: int = Field(default=20)
    max_count_per_term: int = Field(default=20)


def get_config() -> DiceConfig:
    payload = load_config_section("dice") or {}
    return DiceConfig(**payload) if isinstance(payload, dict) else DiceConfig()


__all__ = ["get_config", "DiceConfig"]
