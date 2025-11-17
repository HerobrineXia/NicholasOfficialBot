from __future__ import annotations

from typing import List

from nonebot import logger
from nonebot.adapters import Message
from openai.types.chat import ChatCompletionContentPartParam

from .AI import (
    AIClientProtocol,
    ClientManager,
    DeepSeekClient,
    chat_completion,
    get_message_token,
    new_chat,
)
from .chat import ConversationManager, Messages
from .config import ChatConfig


class ChatService:
    """
    聊天业务层：负责客户端初始化、消息预处理、会话与模型调用。
    """

    def __init__(self, config: ChatConfig):
        self.config = config
        self.conversation_manager = ConversationManager()
        self.client_manager = ClientManager()
        self._init_clients()

    def _init_clients(self) -> None:
        for name, data in self.config.model.items():
            key = self.config.key.get(name)
            if key is None:
                logger.warning(f"模型 {name} 没有密钥，无法使用")
                continue
            match name:
                case "DeepSeek":
                    client = DeepSeekClient(
                        data.models,
                        data.preset,
                        data.max_input_tokens,
                        data.max_output_tokens,
                        key.key,
                        data.base_url,
                    )
                    client.init_tokenizer(data.extra.get("tokenizer_dir", ""))  # 需要预先准备 tokenizer 目录
                    self.client_manager.add_client(name, client)
                case _:
                    logger.warning(f"模型 {name} 不支持，无法使用")

    def _process_message(self, args: Message) -> List[ChatCompletionContentPartParam]:
        """将 NoneBot Message 转为 ChatCompletionContentPartParam 列表。"""
        message: List[ChatCompletionContentPartParam] = []
        for msg_segment in args:
            match msg_segment.type:
                case "image":
                    # TODO: 支持图片消息
                    _ = msg_segment.data.get("url")
                case "text":
                    message.append({"type": "text", "text": msg_segment.data.get("text")})
        return message

    def start_chat(self, user_id: str, args: Message) -> str:
        setting = self.conversation_manager.get_user_setting(user_id)
        model = setting.current_model if setting and setting.current_model else self.config.default_model
        client = self.client_manager.get_client_with_model(model)
        if not isinstance(client, AIClientProtocol):
            raise ValueError(f"模型 {model} 暂未支持")

        preset = setting.preset[model] if setting and model in setting.preset else ""
        conversation = new_chat(client, model, preset)
        self.conversation_manager.add_conversation(user_id, conversation)

        rich_message = self._process_message(args)
        conversation.add_rich_message(
            rich_message, "user", get_message_token(client, Messages.user_message(content=rich_message)), user_id
        )

        result = chat_completion(client, conversation.get_conversation(), model)
        respond = result.choices[0].message.content
        token = result.usage.completion_tokens if result.usage is not None else 0
        if respond is None:
            raise ValueError("模型返回空消息")
        conversation.add_text_message(respond, "assistant", token, user_id)
        return respond

    def continue_chat(self, user_id: str, args: Message) -> str:
        conversation = self.conversation_manager.current_conversation(user_id)
        if conversation is None:
            raise ValueError("未找到上次的会话，请先开始新的会话")
        client = self.client_manager.get_client_with_model(conversation.model)
        if not isinstance(client, AIClientProtocol):
            raise ValueError(f"模型 {conversation.model} 暂未支持")

        rich_message = self._process_message(args)
        conversation.add_rich_message(
            rich_message,
            "user",
            get_message_token(client, Messages.user_message(content=rich_message)),
            user_id,
        )

        result = chat_completion(client, conversation.get_conversation(), conversation.model)
        respond = result.choices[0].message.content
        token = result.usage.completion_tokens if result.usage is not None else 0
        if respond is None:
            raise ValueError("模型返回空消息")
        conversation.add_text_message(respond, "assistant", token, user_id)
        return respond

    def set_model(self, user_id: str, model: str) -> str:
        if model not in self.client_manager.all_models:
            raise ValueError(f"未找到 {model} 模型")
        self.conversation_manager.change_model(user_id, model)
        return f"默认使用模型修改为 {model}"

    def set_preset(self, user_id: str, preset: str) -> str:
        setting = self.conversation_manager.get_user_setting(user_id)
        model = setting.current_model if setting else self.config.default_model
        self.conversation_manager.change_preset(user_id, model, preset)
        return f"修改 {model} 的默认系统消息为 {preset}"
