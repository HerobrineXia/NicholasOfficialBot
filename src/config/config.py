from pydantic import BaseModel
from pydantic.dataclasses import dataclass
import dataclasses
from typing import List

@dataclass
class Args:
    description: str
    required: bool = False

@dataclass
class CommandData:
    prefix: str = 'test'
    description: str = 'Default Description'
    aliases: List[str] = dataclasses.field(default_factory=lambda: [])
    subcommands: List = dataclasses.field(default_factory=lambda: [])
    args: List[Args] = dataclasses.field(default_factory=lambda: [])


class DefaultPluginConfig(BaseModel):
    name: str = 'Default Name'
    description: str = 'Default Description'
    usage: str = 'Default Usage'
    commands: dict[str,CommandData] = {}