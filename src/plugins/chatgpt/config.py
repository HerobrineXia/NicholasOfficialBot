from config import DefaultPluginConfig as DConfig
from pydantic import BaseModel

class GPTConfig(DConfig):
    model: str
    key: str
    preset: str

class Config(BaseModel):
    chatgpt: GPTConfig