from util import get_metadata
from .command_handler import plugin_config

__plugin_meta__ = get_metadata(plugin_config)

__plugin_meta__.description += "，当前使用的模型为: " + plugin_config.model
