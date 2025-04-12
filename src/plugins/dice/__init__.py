from nonebot import get_plugin_config

from .config import Config
from nonebot.adapters import Bot, Event
from util import get_metadata
from nonebot import on, logger

__plugin_meta__ = get_metadata(get_plugin_config(Config).dice)

test = on()
@test.handle()
async def _(bot: Bot, event: Event):
    logger.info("收到消息")
    logger.info(event)