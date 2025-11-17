from config.config import DefaultPluginConfig, CommandData
from nonebot import CommandGroup, on_message
from nonebot.rule import command
from nonebot.internal.matcher import Matcher
from nonebot.plugin.model import PluginMetadata


def get_command_from_data(
    name: str, command_data: CommandData, priority: int, parent_keyword: tuple | None
) -> dict[str, type[Matcher]]:
    """递归构建命令列表，包含子命令。"""
    command_list: dict[str, type[Matcher]] = {}
    child_keywords = tuple([command_data.prefix] + command_data.aliases)
    command_keywords = (
        child_keywords
        if parent_keyword is None
        else tuple((pkey, ckey) for pkey in parent_keyword for ckey in child_keywords)
    )
    command_list[name] = on_message(command(*command_keywords, force_whitespace=True), block=True)
    if len(command_data.subcommands) > 0:
        for subcommand_name, subcommand_data in command_data.subcommands.items():
            subcommand_list = get_command_from_data(
                name + "." + subcommand_name, subcommand_data, priority - 1, command_keywords
            )
            command_list.update(subcommand_list)
    return command_list


def get_command(cmd: dict[str, CommandData]) -> dict[str, type[Matcher]]:
    """将插件命令配置转换为 matcher 字典。"""
    command_list: dict[str, type[Matcher]] = {}
    for command_name, command_data in cmd.items():
        command_list.update(get_command_from_data(command_name, command_data, 10, None))
    return command_list


def get_metadata(plugin_config: DefaultPluginConfig) -> PluginMetadata:
    """根据插件配置生成 PluginMetadata。"""
    return PluginMetadata(
        name=plugin_config.name,
        description=plugin_config.description,
        usage=plugin_config.usage,
        type="application",
        config=DefaultPluginConfig,
        extra={
            "commands": plugin_config.commands,
        },
    )


__all__ = ["get_command_from_data", "get_command", "get_metadata"]
