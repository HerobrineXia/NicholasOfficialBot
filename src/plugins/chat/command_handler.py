from nonebot.adapters import Message, Event
from nonebot.params import CommandArg
from nonebot.internal.matcher import Matcher
from nonebot import logger

from util.commands import get_command
from util import send_text_in_chunks, chunk_text_by_bytes
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
    if not args.extract_plain_text().strip():
        await chat.finish("请输入聊天内容")
    try:
        respond = chat_service.start_chat(event, user_id, args)
    except Exception as e:
        logger.error(f"调用模型失败: {e}")
        await chat.finish(f"调用模型失败，请截图此报错给开发者：{e}")
    await send_text_in_chunks(chat, respond)


# 继续聊天指令
continue_chat = command_list["Chat.Continue"]


@continue_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    user_id = str(event.get_user_id())
    if not args.extract_plain_text().strip():
        await continue_chat.finish("请输入聊天内容")
    try:
        respond = chat_service.continue_chat(event, user_id, args)
    except Exception as e:
        await continue_chat.finish(str(e))
    await send_text_in_chunks(continue_chat, respond)


model_chat = command_list["Chat.Model"]


@model_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    """设置模型指令。"""
    user_id = str(event.get_user_id())
    model = args.extract_plain_text().strip()
    if not model:
        await model_chat.finish("请输入模型名称")
    try:
        respond = chat_service.set_model(event, user_id, model)
    except Exception as e:
        await model_chat.finish(str(e))
    await model_chat.finish(respond)


preset_chat = command_list["Chat.Preset"]


@preset_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    """设置模型预设指令。"""
    user_id = str(event.get_user_id())
    preset = args.extract_plain_text().strip()
    if not preset:
        await preset_chat.finish("请输入预设消息")
    respond = chat_service.set_preset(event, user_id, preset)
    await preset_chat.finish(respond)


reset_preset_chat = command_list.get("Chat.Reset")
if reset_preset_chat:
    @reset_preset_chat.handle()
    async def _(event: Event):
        """重置当前用户的所有预设。"""
        user_id = str(event.get_user_id())
        respond = chat_service.reset_presets(user_id)
        await reset_preset_chat.finish(respond)

info_chat = command_list.get("Chat.Info")
if info_chat:
    @info_chat.handle()
    async def _(event: Event):
        """查看当前模型和预设。"""
        user_id = str(event.get_user_id())
        respond = chat_service.get_status(event, user_id)
        await send_text_in_chunks(info_chat, respond)

list_chat = command_list.get("Chat.List")
if list_chat:
    @list_chat.handle()
    async def _(event: Event, args: Message = CommandArg()):
        """查看历史会话列表或具体会话。"""
        user_id = str(event.get_user_id())
        arg = args.extract_plain_text().strip()
        if not arg:
            respond = chat_service.list_conversations(event, user_id)
            await send_text_in_chunks(list_chat, respond)
        else:
            conv_sid = arg.strip()
            if not conv_sid:
                await list_chat.finish("会话编号不能为空")
            first = chat_service.get_conversation_chunks(event, user_id, conv_sid, chunk_text_by_bytes)
            if first is None:
                await list_chat.finish("未找到该会话或无内容")
            if chat_service.has_more_history(user_id):
                await list_chat.send(first)
                await list_chat.finish("已显示第一段，使用 /bbm-lc 查看下一段")
            else:
                await list_chat.finish(first)

list_continue_chat = command_list.get("Chat.ListContinue")
if list_continue_chat:
    @list_continue_chat.handle()
    async def _(event: Event):
        """继续查看上一段会话内容。"""
        user_id = str(event.get_user_id())
        next_chunk = chat_service.get_conversation_next_chunk(user_id)
        if not next_chunk:
            await list_continue_chat.finish("没有更多内容")
        if chat_service._history_cache.get(user_id):
            await list_continue_chat.send(next_chunk)
            await list_continue_chat.finish("使用 /bbm-lc 继续")
        else:
            await list_continue_chat.finish(next_chunk)
