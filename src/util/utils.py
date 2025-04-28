from config.config import DefaultPluginConfig, CommandData
from nonebot import CommandGroup, on_message
from nonebot.rule import command
from nonebot.internal.matcher import Matcher
from nonebot.plugin.model import PluginMetadata

def get_command_from_data(name:str, command_data: CommandData, priority:int, parent_keyword: tuple | None) -> dict[str, type[Matcher]]:
    """
    获取命令列表
    
    :param command_data: 命令数据对象，包含命令的基本信息。
    :return: 命令列表，键为命令名称，值为命令匹配器类型。

    """
    command_list: dict[str, type[Matcher]] = {}
    child_keywords = tuple([command_data.prefix] + command_data.aliases)
    command_keywords = child_keywords if parent_keyword is None else tuple((pkey, ckey) for pkey in parent_keyword for ckey in child_keywords)
    command_list[name] = on_message(command(*command_keywords,force_whitespace=True),block=True)
    if len(command_data.subcommands) > 0:
        for subcommand_name, subcommand_data in command_data.subcommands.items():
            subcommand_list = get_command_from_data(name + "." + subcommand_name, subcommand_data, priority - 1, command_keywords)
            command_list.update(subcommand_list)
    return command_list


def get_command(cmd: dict[str,CommandData]) -> dict[str, type[Matcher]]:
    """
    获取命令列表
    
    :param cmd: 命令数据字典，键为命令名称，值为命令数据对象。
    :return: 命令列表，键为命令名称，值为命令匹配器类型。

    """
    command_list: dict[str, type[Matcher]] = {}
    for command_name, command_data in cmd.items():
        command_list.update(get_command_from_data(command_name, command_data, 10, None))
    return command_list

def get_metadata(plugin_config: DefaultPluginConfig) -> PluginMetadata:
    """
    获取插件的元数据
    
    :param plugin_config: 插件配置对象，包含插件的基本信息和命令列表。
    :return: 插件元数据对象，包含插件的名称、描述、使用方法和命令列表。
    """
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