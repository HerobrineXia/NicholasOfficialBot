from pydantic import BaseModel
from config import DefaultPluginConfig as DConfig

class Config(BaseModel):
    help: DConfig