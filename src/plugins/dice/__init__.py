from nonebot.adapters import Bot, Event
from util import get_metadata
from nonebot import on, logger
from .config import get_config

# 插件内部加载配置，便于独立移除
plugin_config = get_config()
__plugin_meta__ = get_metadata(plugin_config)

test = on()
@test.handle()
async def _(bot: Bot, event: Event):
    logger.info("收到消息")
    logger.info(event)
