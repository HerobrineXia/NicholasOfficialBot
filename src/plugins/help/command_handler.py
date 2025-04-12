
from .config import Config
from util import get_command
from nonebot import get_driver, logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import get_plugin_config, get_loaded_plugins
from nonebot.plugin.model import PluginMetadata
from nonebot.internal.matcher import Matcher

# Get the plugin config
plugin_config = get_plugin_config(Config).help
command_list: dict[str, type[Matcher]] = get_command(plugin_config.commands)


# Get the list of all commands
help_all = command_list["Help"]
@help_all.handle()
async def _():
    logger.info("Help command called")
    # Get all commands' description
    all_commands_desc: dict[str, PluginMetadata] = {}
    for plugin in get_loaded_plugins():
        if(plugin.metadata is None): continue
        all_commands_desc[plugin.metadata.name] = plugin.metadata
    # Respond
    respond = "插件列表:\n"
    for command_name, command_data in all_commands_desc.items():
        respond += f"{command_name}: {command_data.description}\n"
    respond += f"\n{plugin_config.usage}"
    await help_all.finish(respond)


# Get the detailed description of a command
help_spec = command_list["HelpCommand"]
@help_spec.handle()
async def _(args: Message = CommandArg()):
    if command := args.extract_plain_text():
        respond = ""
        for plugin in get_loaded_plugins():
            if(plugin.metadata is None): continue
            if(command == plugin.metadata.name
                    or command in [cmd.prefix for cmd in plugin.metadata.extra["commands"].values()]
                    or command in [alias for cmd in plugin.metadata.extra["commands"].values() for alias in cmd.aliases]):
                respond = f"{plugin.metadata.name}:{plugin.metadata.description}\n{plugin.metadata.usage}\n"
                respond += f"使用方法(缩写):\n"
                for command_data in plugin.metadata.extra["commands"].values():
                    respond += f"{list(get_driver().config.command_start)[0]}{command_data.prefix}"
                    if(len(command_data.aliases) > 0):
                        respond += f"({','.join(command_data.aliases)})"
                    if(len(command_data.args) > 0):
                        for arg in command_data.args:
                            respond += f" {'[' if arg.required == False else '<'}{arg.description}{']' if arg.required == False else '>'}"
                    respond += f": {command_data.description}\n"
                break
        await help_spec.finish(respond)
    else:
        await help_spec.finish()