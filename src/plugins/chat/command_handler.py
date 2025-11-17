from nonebot.adapters import Message, Event
from nonebot.params import CommandArg
from nonebot.internal.matcher import Matcher
from nonebot import logger

from util.commands import get_command
from .config import get_config
from .service import ChatService

# 插件配置与服务实例
plugin_config = get_config()
chat_service = ChatService(plugin_config)
command_list: dict[str, type[Matcher]] = get_command(plugin_config.commands)

# 默认聊天指令
chat = command_list["Chat"]


@chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    user_id = str(event.get_user_id())
    try:
        respond = chat_service.start_chat(user_id, args)
    except Exception as e:
        logger.error(f"调用模型失败: {e}")
        await chat.finish(f"调用模型失败，请截图此报错给开发者：{e}")
    await chat.finish(respond)


# 继续聊天指令
continue_chat = command_list["Chat.Continue"]


@continue_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    user_id = str(event.get_user_id())
    try:
        respond = chat_service.continue_chat(user_id, args)
    except Exception as e:
        await continue_chat.finish(str(e))
    await continue_chat.finish(respond)


model_chat = command_list["Chat.Model"]


@model_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    """设置模型指令。"""
    user_id = str(event.get_user_id())
    model = args.extract_plain_text().strip()
    try:
        respond = chat_service.set_model(user_id, model)
    except Exception as e:
        await model_chat.finish(str(e))
    await model_chat.finish(respond)


preset_chat = command_list["Chat.Preset"]


@preset_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    """设置模型预设指令。"""
    user_id = str(event.get_user_id())
    preset = args.extract_plain_text().strip()
    respond = chat_service.set_preset(user_id, preset)
    await preset_chat.finish(respond)
