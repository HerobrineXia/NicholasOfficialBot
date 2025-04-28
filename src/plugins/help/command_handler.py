
from typing import Iterable
from config.config import CommandData
from .config import Config
from util import get_command
from nonebot import get_driver, logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import get_plugin_config, get_loaded_plugins, Plugin
from nonebot.plugin.model import PluginMetadata
from nonebot.internal.matcher import Matcher

# 获取help插件配置
plugin_config = get_plugin_config(Config).help
command_list: dict[str, type[Matcher]] = get_command(plugin_config.commands)

def generate_help_message(commands: dict[str,CommandData], cmd_prefix:str="") -> str:
    """
    生成指令帮助信息。
    
    :param command: 指令数据对象，包含指令的基本信息。
    :return: 帮助信息字符串。
    """
    # 获取插件的元数据
    respond = ""
    for command_data in commands.values():
        respond += f"{list(get_driver().config.command_start)[0]}"
        prefix = f"{cmd_prefix}{list(get_driver().config.command_sep)[0] if cmd_prefix != "" else ""}{command_data.prefix}"
        if(len(command_data.aliases) > 0):
            prefix += f"({','.join(command_data.aliases)})"
        respond += prefix
        if(len(command_data.args) > 0):
            for arg in command_data.args:
                respond += f" {'[' if arg.required == False else '<'}{arg.description}{']' if arg.required == False else '>'}"
        respond += f": {command_data.description}\n"
    if len(command_data.subcommands) > 0:
        respond += generate_help_message(command_data.subcommands, prefix)
    return respond

# help指令
# 该指令用于获取插件列表和介绍
help = command_list["Help"]
@help.handle()
async def _(args: Message = CommandArg()):
    logger.info("Help指令被调用")
    # 如果有参数，则返回该插件的介绍
    if raw_command := args.extract_plain_text():
        respond = ""
        # 小写化指令
        command = raw_command.lower().strip()
        for plugin in get_loaded_plugins():
            if(plugin.metadata is None): continue
            # 检查指令是否匹配
            commands:dict = plugin.metadata.extra.get("commands", {})
            if(command == plugin.metadata.name.lower()
                    or command in [cmd.prefix.lower() for cmd in commands.values()]
                    or command in [alias.lower() for cmd in commands.values() for alias in cmd.aliases]):
                respond += f"{plugin.metadata.name}:{plugin.metadata.description}\n{plugin.metadata.usage}\n"
                respond += f"使用方法(缩写):\n"
                respond += generate_help_message(plugin.metadata.extra["commands"])

                break
        # 如果没有找到该插件，则返回错误信息
        if(respond == ""):
            respond = f"没有找到名为{raw_command}的插件或指令，请检查拼写或使用help指令查看插件列表。"
        await help.finish(respond)
    # 如果没有参数，则返回插件列表
    else:
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
        await help.finish(respond)