from __future__ import annotations

from typing import Any, Dict, List, Tuple

from nonebot import logger
from nonebot.adapters import Event, Message
from openai.types.chat import ChatCompletionContentPartParam

from .AI import (
    AIClientProtocol,
    ClientManager,
    DeepSeekClient,
    chat_completion,
    get_message_token,
)
from .chat import Messages
from .config import ChatConfig
from . import store


def _to_dict(message: Any) -> Dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump()
    if hasattr(message, "dict"):
        return message.dict()
    return message


class ChatService:
    """聊天业务层，使用共享 SQLite 持久化设置与会话。"""

    def __init__(self, config: ChatConfig):
        self.config = config
        store.init_tables()
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
                    client.init_tokenizer(data.extra.get("tokenizer_dir", ""))
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

    def _scope_from_event(self, event: Event) -> Tuple[str, str]:
        group_id = ""
        if hasattr(event, "group_id"):
            group_id = str(getattr(event, "group_id"))
        elif hasattr(event, "detail_type") and getattr(event, "detail_type") == "group":
            group_id = str(getattr(event, "group_id", ""))
        scope = "group_user" if group_id else "direct"
        return scope, group_id

    def _resolve_model(self, scope: str, group_id: str, user_id: str) -> str:
        chain = [
            ("group_user", group_id, user_id),
            ("group_default", group_id, "ALL"),
            ("direct", "", user_id),
        ]
        for sc, gid, uid in chain:
            model = store.get_setting(sc, gid, uid)
            if model:
                return model
        return self.config.default_model

    def _resolve_preset(self, model: str, scope: str, group_id: str, user_id: str) -> str:
        chain = [
            ("group_user", group_id, user_id),
            ("group_default", group_id, "ALL"),
            ("direct", "", user_id),
        ]
        for sc, gid, uid in chain:
            presets = store.get_presets(sc, gid, uid)
            if model in presets:
                return presets[model]
        for data in self.config.model.values():
            if model in data.models:
                idx = data.models.index(model)
                if idx < len(data.preset):
                    return data.preset[idx]
        return ""

    def _max_tokens_for_model(self, model: str) -> int:
        for data in self.config.model.values():
            if model in data.models:
                idx = data.models.index(model)
                if idx < len(data.max_input_tokens):
                    return data.max_input_tokens[idx]
        return 4096

    def start_chat(self, event: Event, user_id: str, args: Message) -> str:
        scope, group_id = self._scope_from_event(event)
        model = self._resolve_model(scope, group_id, user_id)
        client = self.client_manager.get_client_with_model(model)
        if not isinstance(client, AIClientProtocol):
            raise ValueError(f"模型 {model} 暂未支持")

        preset = self._resolve_preset(model, scope, group_id, user_id)
        max_tokens = self._max_tokens_for_model(model)
        conv_id = store.create_conversation(scope, group_id, user_id, model, max_tokens)
        store.trim_conversations(scope, group_id, user_id, keep=3)

        messages: List[Dict[str, Any]] = []
        if preset:
            system_msg = _to_dict(Messages.system_message(preset))
            messages.append({"role": system_msg.get("role", "system"), "content": system_msg.get("content")})
            store.append_message(conv_id, "system", system_msg.get("content"), client.get_token(preset))

        rich_message = self._process_message(args)
        user_msg_obj = Messages.user_message(content=rich_message, name=user_id)
        user_msg = _to_dict(user_msg_obj)
        messages.append({"role": user_msg.get("role", "user"), "content": user_msg.get("content")})
        store.append_message(conv_id, "user", user_msg.get("content"), get_message_token(client, user_msg_obj))

        result = chat_completion(client, messages, model)
        respond = result.choices[0].message.content
        token = result.usage.completion_tokens if result.usage is not None else 0
        if respond is None:
            raise ValueError("模型返回空消息")
        assistant_msg = _to_dict(Messages.assistant_message(respond, name=user_id))
        store.append_message(conv_id, "assistant", assistant_msg.get("content"), token or 0)
        return respond

    def continue_chat(self, event: Event, user_id: str, args: Message) -> str:
        scope, group_id = self._scope_from_event(event)
        conv = store.get_latest_conversation(scope, group_id, user_id)
        if conv is None:
            raise ValueError("未找到上次的会话，请先开始新的会话")
        model = conv["model"]
        client = self.client_manager.get_client_with_model(model)
        if not isinstance(client, AIClientProtocol):
            raise ValueError(f"模型 {model} 暂未支持")

        messages = [{"role": m["role"], "content": m["content"]} for m in conv["messages"]]

        rich_message = self._process_message(args)
        user_msg_obj = Messages.user_message(content=rich_message, name=user_id)
        user_msg = _to_dict(user_msg_obj)
        messages.append({"role": user_msg.get("role", "user"), "content": user_msg.get("content")})
        store.append_message(conv["id"], "user", user_msg.get("content"), get_message_token(client, user_msg_obj))

        result = chat_completion(client, messages, model)
        respond = result.choices[0].message.content
        token = result.usage.completion_tokens if result.usage is not None else 0
        if respond is None:
            raise ValueError("模型返回空消息")
        assistant_msg = _to_dict(Messages.assistant_message(respond, name=user_id))
        store.append_message(conv["id"], "assistant", assistant_msg.get("content"), token or 0)
        return respond

    def set_model(self, event: Event, user_id: str, model: str) -> str:
        if model not in self.client_manager.all_models:
            raise ValueError(f"未找到 {model} 模型")
        scope, group_id = self._scope_from_event(event)
        store.upsert_setting(scope, group_id, user_id, model)
        return f"默认使用模型修改为 {model}"

    def set_preset(self, event: Event, user_id: str, preset: str) -> str:
        scope, group_id = self._scope_from_event(event)
        model = self._resolve_model(scope, group_id, user_id)
        store.upsert_preset(scope, group_id, user_id, model, preset)
        return f"修改 {model} 的默认系统消息为 {preset}"

    def get_status(self, event: Event, user_id: str) -> str:
        """查看当前使用的模型和预设（不展示群号）。"""
        scope, group_id = self._scope_from_event(event)
        model = self._resolve_model(scope, group_id, user_id)
        preset = self._resolve_preset(model, scope, group_id, user_id) or "（未设置，使用默认）"
        location = "群聊" if group_id else "私聊"
        return f"{location} 当前模型：{model}\n当前预设：{preset}"

    def reset_presets(self, user_id: str) -> str:
        """清空该用户的所有预设（群/私聊）。"""
        store.clear_presets_for_user(user_id)
        return "已清空你的所有预设"
