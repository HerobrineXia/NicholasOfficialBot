from __future__ import annotations

from config.config import CommandData
from util.commands import get_command
from nonebot import get_driver, logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import get_loaded_plugins
from nonebot.plugin.model import PluginMetadata
from nonebot.internal.matcher import Matcher

from .config import get_config

# 获取 help 插件配置
plugin_config = get_config()
command_list: dict[str, type[Matcher]] = get_command(plugin_config.commands)


def _format_command(prefix: str, cmd: CommandData) -> str:
    """格式化单条命令，包含别名/参数。"""
    start = list(get_driver().config.command_start)[0]
    sep = list(get_driver().config.command_sep)[0]
    name = f"{prefix}{sep if prefix else ''}{cmd.prefix}"
    if cmd.aliases:
        name += f"({','.join(cmd.aliases)})"
    parts = [f"{start}{name}"]
    if cmd.args:
        for arg in cmd.args:
            wrapper = ("<", ">") if arg.required else ("[", "]")
            parts.append(f" {wrapper[0]}{arg.description}{wrapper[1]}")
    parts.append(f": {cmd.description}")
    return "".join(parts)


def _format_commands_tree(commands: dict[str, CommandData], parent_prefix: str = "") -> str:
    """递归生成帮助文本，分层展示命令与子命令。"""
    lines: list[str] = []
    for cmd_data in commands.values():
        lines.append(_format_command(parent_prefix, cmd_data))
        if cmd_data.subcommands:
            child_prefix = f"{parent_prefix}{' ' if parent_prefix else ''}{cmd_data.prefix}"
            lines.append(_format_commands_tree(cmd_data.subcommands, child_prefix))
    return "\n".join(lines)


def find_plugin_help(keyword: str) -> str | None:
    """根据关键字查找插件或命令的帮助文本。"""
    keyword = keyword.lower().strip()
    for plugin in get_loaded_plugins():
        meta = plugin.metadata
        if meta is None:
            continue
        cmds: dict = meta.extra.get("commands", {})
        if (
            keyword == meta.name.lower()
            or keyword in [cmd.prefix.lower() for cmd in cmds.values()]
            or keyword in [alias.lower() for cmd in cmds.values() for alias in cmd.aliases]
        ):
            lines = [f"{meta.name}: {meta.description}"]
            if meta.usage:
                lines.append(f"用法: {meta.usage}")
            lines.append("命令列表(含别名):")
            lines.append(_format_commands_tree(cmds))
            return "\n".join(lines)
    return None


# help指令
help = command_list["Help"]


@help.handle()
async def _(args: Message = CommandArg()):
    logger.info("Help指令被调用")
    raw_command = args.extract_plain_text().strip()
    if raw_command:
        respond = find_plugin_help(raw_command) or f"没有找到名为{raw_command}的插件或指令，请检查拼写或使用help查看插件列表。"
        await help.finish(respond)
    else:
        plugins: dict[str, PluginMetadata] = {
            plugin.metadata.name: plugin.metadata for plugin in get_loaded_plugins() if plugin.metadata
        }
        respond = "插件列表:\n" + "\n".join(f"{name}: {meta.description}" for name, meta in plugins.items())
        respond += f"\n\n{plugin_config.usage}"
        await help.finish(respond)
