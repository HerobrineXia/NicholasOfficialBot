from __future__ import annotations
from pydantic import BaseModel
from pydantic.dataclasses import dataclass
import dataclasses
from typing import List

@dataclass
class Args:
    """
    参数类，用于定义命令的参数。

    Attributes:
        description (str): 参数描述。
        required (bool): 是否为必需参数，默认为False。
    """
    description: str
    required: bool = False

@dataclass
class CommandData:
    """
    命令数据类，用于定义命令的基本信息和参数。

    Attributes:
        prefix (str): 命令前缀。
        description (str): 命令描述。
        aliases (List[str]): 命令别名（缩写）。
        subcommands (List): 子命令列表。
        args (List[Args]): 命令参数列表。
    """
    prefix: str = 'Prefix'
    description: str = 'Default Description'
    aliases: List[str] = dataclasses.field(default_factory=lambda: [])
    subcommands: dict[str,CommandData] = dataclasses.field(default_factory=lambda: {})
    args: List[Args] = dataclasses.field(default_factory=lambda: [])


class DefaultPluginConfig(BaseModel):
    """
    默认插件配置类，用于定义插件的基本信息和命令列表。

    Attributes:
        name (str): 插件名称。
        description (str): 插件描述。
        usage (str): 插件使用方法。
        commands (dict[str, CommandData]): 命令列表，键为命令名称，值为CommandData对象。
    """
    name: str = 'Default Name'
    description: str = 'Default Description'
    usage: str = 'Default Usage'
    commands: dict[str,CommandData] = {}