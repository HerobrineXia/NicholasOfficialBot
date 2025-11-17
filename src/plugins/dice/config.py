from config.config import DefaultPluginConfig
from config.settings import load_config_section


def get_config() -> DefaultPluginConfig:
    payload = load_config_section("dice") or {}
    return DefaultPluginConfig(**payload) if isinstance(payload, dict) else DefaultPluginConfig()


__all__ = ["get_config"]
