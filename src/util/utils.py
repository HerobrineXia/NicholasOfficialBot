from config.config import DefaultPluginConfig, CommandData
from nonebot import on_command
from nonebot.rule import Rule
from nonebot.internal.matcher import Matcher
from nonebot.plugin.model import PluginMetadata
from nonebot.params import CommandArg

async def no_arg(message = CommandArg()) -> bool:
    if(message is None): return False
    return message.extract_plain_text() == ""

async def has_arg(message = CommandArg()) -> bool:
    if(message is None): return False
    return message.extract_plain_text() != ""

def get_command(cmd: dict[str,CommandData]) -> dict[str, type[Matcher]]:
    command_list: dict[str, type[Matcher]] = {}
    for command_name, command_data in cmd.items():
        cmd_rule = Rule()
        if(len(command_data.args) == 0):
            cmd_rule &= no_arg
        else:
            cmd_rule &= has_arg
        command_list[command_name] = on_command(command_data.prefix, aliases=set(command_data.aliases), rule=cmd_rule)
    return command_list

def get_metadata(plugin_config: DefaultPluginConfig) -> PluginMetadata:
    return PluginMetadata(
        name= plugin_config.name,
        description= plugin_config.description,
        usage= plugin_config.usage,
        type= "application",
        config=DefaultPluginConfig,
        extra= {
            "commands": plugin_config.commands
        }
    )