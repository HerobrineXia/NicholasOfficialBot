from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from nonebot import logger
from nonebot.adapters import Event, Message
from openai.types.chat import ChatCompletionContentPartParam

from .AI import (
    AIClientProtocol,
    ClientManager,
    DeepSeekClient,
    ChatGPTClient,
    chat_completion,
    get_message_token,
)
from .chat import Messages
from .config import ChatConfig
from . import store
from util import file_system


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
        self._history_cache: dict[str, list[str]] = {}
        # 过滤 http/https 及裸域名链接，避免 QQ 拦截
        self._url_pattern = re.compile(r"(https?://\S+|\b[\w.-]+\.[a-zA-Z]{2,}\S*)")

    def _sanitize_response(self, text: str | None) -> str:
        if not text:
            return ""
        return self._url_pattern.sub("[链接已移除]", text)

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
                case "ChatGPT":
                    client = ChatGPTClient(
                        data.models,
                        data.preset,
                        data.max_input_tokens,
                        data.max_output_tokens,
                        key.key,
                        data.base_url,
                    )
                    self.client_manager.add_client(name, client)
                case _:
                    logger.warning(f"模型 {name} 不支持，无法使用")

    def _process_message(self, args: Message, model: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        返回 (store_parts, send_parts)
        store_parts：完整记录（包含图片的本地 file:// 路径）
        send_parts：根据模型能力裁剪后发送给模型的内容，gpt-5.* 使用 data:URL 传图，其它模型用文本占位
        """
        store_parts: List[Dict[str, Any]] = []
        send_parts: List[Dict[str, Any]] = []
        support_image = model.startswith("gpt-5")
        text_type = "input_text" if support_image else "text"
        for msg_segment in args:
            match msg_segment.type:
                case "image":
                    url = msg_segment.data.get("url")
                    if not url:
                        continue
                    local_path = file_system.save_file(url, storage_dir=file_system.PROJECT_ROOT / "data" / "temp_img")
                    if not local_path:
                        continue
                    store_parts.append({"type": "image_url", "image_url": {"url": f"file://{local_path}"}})
                    if support_image:
                        b64 = file_system.read_file_as_base64(local_path)
                        if b64:
                            send_parts.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"})
                        else:
                            send_parts.append({"type": "text", "text": "[image:load failed]"})
                    else:
                        send_parts.append({"type": "text", "text": f"[image:{local_path}]"})
                case "text":
                    text = msg_segment.data.get("text")
                    if text:
                        store_parts.append({"type": "text", "text": text})
                        send_parts.append({"type": text_type, "text": text})
        return store_parts, send_parts

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
        conv_sid, conv_id = store.create_conversation(scope, group_id, user_id, model, max_tokens)
        store.trim_conversations(scope, group_id, user_id, keep=3)

        messages: List[Dict[str, Any]] = []
        if preset:
            system_msg = _to_dict(Messages.system_message(preset))
            messages.append({"role": system_msg.get("role", "system"), "content": system_msg.get("content")})
            store.append_message(conv_id, "system", system_msg.get("content"), client.get_token(preset))

        store_parts, send_parts = self._process_message(args, model)
        user_msg_obj = Messages.user_message(content=send_parts, name=user_id)
        user_msg = _to_dict(user_msg_obj)
        messages.append({"role": user_msg.get("role", "user"), "content": user_msg.get("content")})
        store.append_message(conv_id, "user", store_parts, get_message_token(client, user_msg_obj))

        result = chat_completion(client, messages, model)
        respond = self._sanitize_response(result.choices[0].message.content)
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

        store_parts, send_parts = self._process_message(args, model)
        user_msg_obj = Messages.user_message(content=send_parts, name=user_id)
        user_msg = _to_dict(user_msg_obj)
        messages.append({"role": user_msg.get("role", "user"), "content": user_msg.get("content")})
        store.append_message(conv["id"], "user", store_parts, get_message_token(client, user_msg_obj))

        result = chat_completion(client, messages, model)
        respond = self._sanitize_response(result.choices[0].message.content)
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

    def list_conversations(self, event: Event, user_id: str) -> str:
        scope, group_id = self._scope_from_event(event)
        conversations = store.list_conversations(scope, group_id, user_id)
        if not conversations:
            return "没有历史会话"
        lines: list[str] = []
        for conv in conversations:
            conv_meta = store.get_conversation_by_short_id(conv["short_id"], user_id)
            if not conv_meta:
                continue
            msgs = store.get_conversation_messages(conv_meta["id"])
            title = ""
            for msg in msgs:
                if msg["role"] == "user":
                    content = msg["content"]
                    if isinstance(content, list):
                        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                        title = "".join(parts)
                    elif isinstance(content, str):
                        title = content
                    title = title.strip()
                    break
            if not title:
                title = "(无标题)"
            if len(title.encode("utf-8")) > 60:
                # 60 字节截断
                truncated = ""
                total = 0
                for ch in title:
                    b = len(ch.encode("utf-8"))
                    if total + b > 60:
                        break
                    truncated += ch
                    total += b
                title = truncated + "..."
            lines.append(f"{conv['short_id']}:{title}")
        return "\n".join(lines)

    def get_conversation_chunks(self, event: Event, user_id: str, conv_sid: str, chunker) -> str | None:
        """返回该会话的第一段文本，并缓存剩余分段，供后续继续查看。仅允许该用户自己的会话。"""
        conv_meta = store.get_conversation_by_short_id(conv_sid, user_id)
        if not conv_meta:
            return None
        messages = store.get_conversation_messages(conv_meta["id"])
        if not messages:
            return None
        text_parts: list[str] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, list):
                text = "".join([c.get("text", "") for c in content if isinstance(c, dict)])
            else:
                text = str(content)
            text_parts.append(f"{role}: {text}")
        full_text = "\n".join(text_parts)
        chunks = chunker(full_text)
        if not chunks:
            return None
        if len(chunks) > 1:
            self._history_cache[user_id] = [conv_sid] + chunks[1:]
        return chunks[0]

    def get_conversation_next_chunk(self, user_id: str) -> str | None:
        cache = self._history_cache.get(user_id, [])
        if not cache:
            return None
        # cache[0] 是 sid，之后是剩余 chunk
        if len(cache) <= 1:
            self._history_cache.pop(user_id, None)
            return None
        rest = cache[1:]
        if not rest:
            return None
        chunk = rest.pop(0)
        if rest:
            self._history_cache[user_id] = [cache[0]] + rest
        else:
            self._history_cache.pop(user_id, None)
        return chunk

    def has_more_history(self, user_id: str) -> bool:
        cache = self._history_cache.get(user_id, [])
        return len(cache) > 1

    def reset_presets(self, user_id: str) -> str:
        """清空该用户的所有预设（群/私聊）。"""
        store.clear_presets_for_user(user_id)
        return "已清空你的所有预设"
