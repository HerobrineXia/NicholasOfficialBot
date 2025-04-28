from util import get_metadata
from .command_handler import plugin_config

__plugin_meta__ = get_metadata(plugin_config)

__plugin_meta__.description += "，可用的模型有："
for model in plugin_config.model:
    for model_name in plugin_config.model[model].models:
        __plugin_meta__.description += f"\n    {model} - {model_name}"
