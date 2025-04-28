from .config import Config
from util import get_command
from nonebot.adapters import Message, Event
from nonebot.params import CommandArg
from nonebot import get_plugin_config
from nonebot.internal.matcher import Matcher
from .chat import ConversationManager, Messages
from .AI import ClientManager, DeepSeekClient, AIClientProtocol, new_chat, chat_completion, get_message_token
from nonebot import logger
from util import file_system as fs
from typing import List
from openai.types.chat import ChatCompletionContentPartParam 

# Get the plugin config
plugin_config = get_plugin_config(Config).chat
command_list: dict[str, type[Matcher]] = get_command(plugin_config.commands)


conversation_manager = ConversationManager()
client_manager = ClientManager()
# 初始化管理器
for name, data in plugin_config.model.items():
    if plugin_config.key.get(name) is None:
        logger.warning(f"模型 {name} 没有密钥，无法使用")
        continue
    match name:
        case "DeepSeek":
            client = DeepSeekClient(data.models, data.preset, data.max_input_tokens, data.max_output_tokens, plugin_config.key[name].key, data.base_url)
            client.init_tokenizer(data.extra["tokenizer_dir"])
            client_manager.add_client(name, client)
        case _:
            logger.warning(f"模型 {name} 不支持，无法使用")
            continue

def process_message(args: Message) -> List[ChatCompletionContentPartParam]:
    """
    处理消息，将消息转换为ChatCompletionContentPartParam格式。
    
    :param args: 消息对象。
    :return: 处理后的消息列表。
    """
    message:List[ChatCompletionContentPartParam] = []
    for msgSegment in args:
        match msgSegment.type:
            case "image":
                # TODO: 图片消息
                url = msgSegment.data["url"]
                # local_url = fs.save_file(url)
                # base64_image = fs.read_file_as_base64(local_url)
                # fs.remove_file(local_url)
            case "text":
                message.append({"type":"text", "text":msgSegment.data.get("text")})
    return message

# 默认聊天指令
chat = command_list["Chat"]
@chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    id = str(event.get_user_id())
    # 获取用户设置
    setting = conversation_manager.get_user_setting(id)
    model = setting.current_model if setting is not None and setting.current_model != "" else plugin_config.default_model
    client = client_manager.get_client_with_model(model)
    # 检查模型是否支持
    if not isinstance(client,AIClientProtocol):
        await chat.finish(f"模型 {model} 暂未支持")
    preset = setting.preset[model] if setting is not None and model in setting.preset else ""
    # 创建会话
    conversation = new_chat(client, model, preset)
    conversation_manager.add_conversation(id, conversation)
    message = process_message(args)
    conversation.add_rich_message(message, "user", get_message_token(client,Messages.user_message(content=message)), id)
    # 处理消息
    try:
    # 获取返回消息
        result = chat_completion(client, conversation.get_conversation(), model)
    except Exception as e:
    # 处理异常
        logger.error(f"调用模型失败: {e}")
        await chat.finish(f"调用模型失败，请截图此报错给开发者: {e}")
    # 处理返回消息
    respond = result.choices[0].message.content
    token = result.usage.completion_tokens if result.usage is not None else 0
    if respond is None:
        await chat.finish("模型返回空消息，请让开发者检查")
    conversation.add_text_message(respond, "assistant", token, id)
    await chat.finish(respond)
    
# 继续聊天指令
continue_chat = command_list["Chat.Continue"]
@continue_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    id = str(event.get_user_id())
    conversation = conversation_manager.current_conversation(id)
    if conversation is None:
        await continue_chat.finish("未找到上次的会话，请先使用指令开始新的会话")
    client = client_manager.get_client_with_model(conversation.model)
    if not isinstance(client,AIClientProtocol):
        await continue_chat.finish(f"模型 {conversation.model} 暂未支持")
    message = process_message(args)
    conversation.add_rich_message(message, "user", get_message_token(client,Messages.user_message(content=message)), id)
    # 处理消息
    try:
        # 获取返回消息
        result = chat_completion(client, conversation.get_conversation(), conversation.model)
    except Exception as e:
        # 处理异常
        logger.error(f"调用模型失败: {e}")
        await continue_chat.finish(f"调用模型失败，请截图此报错给开发者: {e}")
    # 处理返回消息
    respond = result.choices[0].message.content
    token = result.usage.completion_tokens if result.usage is not None else 0
    if respond is None:
        await continue_chat.finish("模型返回空消息，请让开发者检查")
    conversation.add_text_message(respond, "assistant", token, id)
    await continue_chat.finish(respond)
    
model_chat = command_list["Chat.Model"]
@model_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    """
    设置模型指令。
    
    :param args: 消息对象。
    """
    id = str(event.get_user_id())
    # 获取用户设置
    model = args.extract_plain_text().strip()
    if model not in client_manager.all_models:
        await model_chat.finish(f"未找到 {model} 模型")
    conversation_manager.change_model(id, model)
    await model_chat.finish(f"默认使用模型修改为 {model}")

preset_chat = command_list["Chat.Preset"]
@preset_chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    """
    设置模型指令。
    
    :param args: 消息对象。
    """
    id = str(event.get_user_id())
    # 获取用户设置
    preset = args.extract_plain_text().strip()
    setting = conversation_manager.get_user_setting(id)
    model = setting.current_model if setting is not None else plugin_config.default_model
    conversation_manager.change_preset(id, model, preset)
    await model_chat.finish(f"修改{model}的默认系统消息为 {preset}")