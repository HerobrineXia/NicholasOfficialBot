from config import DefaultPluginConfig as DConfig
from pydantic import BaseModel
from typing import List
from pydantic.dataclasses import dataclass
import dataclasses

@dataclass
class ModelData:
    """
    模型数据类，用于定义模型的基本信息。

    Attributes:
        models (List[str]): 可用模型列表。
        base_url (str): 基础URL。
    """
    models: List[str] = dataclasses.field(default_factory=lambda: [])
    preset: List[str] = dataclasses.field(default_factory=lambda: [])
    base_url: str = ""
    max_input_tokens: List[int] = dataclasses.field(default_factory=lambda: [])
    max_output_tokens: List[int] = dataclasses.field(default_factory=lambda: [])
    extra: dict[str,str] = dataclasses.field(default_factory=lambda: {})

@dataclass
class KeyData:
    """
    密钥数据类，用于定义密钥的基本信息。

    Attributes:
        key (str): 密钥。
    """
    key: str = ""

class ChatConfig(DConfig):
    """
    聊天配置类，继承自默认插件配置类。
    
    Attributes:
        model (dict[str, ModelData]): 模型列表，键为模型名称，值为ModelData对象。
        key (dict[str, KeyData]): 密钥列表，键为密钥名称，值为KeyData对象。
        preset (str): 预设配置。
    """
    model: dict[str, ModelData] = {}
    key: dict[str, KeyData] = {}
    default_model: str = ""

class Config(BaseModel):
    chat: ChatConfig