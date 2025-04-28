from typing import Iterable, List, Literal
from pydantic.dataclasses import dataclass
import dataclasses
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionContentPartParam, ChatCompletionSystemMessageParam
from openai.types.chat import ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam, ChatCompletionContentPartTextParam, ChatCompletionContentPartRefusalParam

@dataclass
class UserSetting:
    """
    用户设置类，用于定义用户的基本信息。
    
    Attributes:
        current_model (str): 当前使用的模型名称。
        preset (dict[str, str]): 预设配置，键为模型名称，值为预设内容。
    """
    current_model: str = ""
    preset: dict[str, str] = dataclasses.field(default_factory=lambda: {})

class Messages:
    @classmethod
    def system_message(cls, content: str | Iterable[ChatCompletionContentPartTextParam], name:str = "") -> ChatCompletionSystemMessageParam:
        """
        创建系统消息。
        
        :param content: 消息内容。
        :return: 系统消息对象。
        """
        return ChatCompletionSystemMessageParam(role="system", content=content, name=name)
    
    @classmethod
    def user_message(cls, content: str | Iterable[ChatCompletionContentPartParam], name:str = "") -> ChatCompletionUserMessageParam:
        """
        创建用户消息。
        
        :param content: 消息内容。
        :return: 用户消息对象。
        """
        return ChatCompletionUserMessageParam(role="user", content=content, name=name)
    
    @classmethod
    def assistant_message(cls, content: str | Iterable[ChatCompletionContentPartTextParam], name:str = "") -> ChatCompletionAssistantMessageParam:
        """
        创建助手消息。
        
        :param content: 消息内容。
        :return: 助手消息对象。
        """
        return ChatCompletionAssistantMessageParam(role="assistant", content=content, name=name)

class Conversation():
    model:str = ""
    max_tokens:int
    conversation:List[ChatCompletionMessageParam]
    tokens:List[int]
    current_token:int
    
    def __init__(self, model: str, max_tokens: int):
        self.model = model
        self.max_tokens = max_tokens
        self.tokens = []
        self.conversation = []
        self.current_token = 0

    def add_text_message(self, message: str | Iterable[ChatCompletionContentPartTextParam], role: Literal["user", "assistant", "system"], token:int = 0, name: str = "") -> ChatCompletionMessageParam:
        """
        添加文本消息到会话中。超过最大令牌数时，移除最旧的消息。
        
        :param message: 消息内容，可以是字符串或ChatCompletionContentPartTextParam对象。
        :param role: 消息角色，可以是"user"、"assistant"或"system"。
        :param token: 消息的令牌数。
        :param name: 消息发送者的名称。
        """
        self.tokens.append(token)
        self.current_token += token
        while self.current_token > self.max_tokens:
            self.remove_oldest_message()
        match role:
            case "user":
                msg = Messages.user_message(content=message, name=name)
            case "assistant":
                msg = Messages.assistant_message(content=message, name=name)
            case "system":
                msg = Messages.system_message(content=message, name=name)
        self.conversation.append(msg)
        return msg

    
    def add_rich_message(self, message: str | Iterable[ChatCompletionContentPartParam], role: Literal["user"], token:int = 0, name: str = "") -> ChatCompletionMessageParam:
        """
        添加富文本消息到会话中。超过最大令牌数时，移除最旧的消息。
        
        :param message: 消息内容，可以是字符串或ChatCompletionContentPartParam对象。
        :param role: 消息角色，可以是"user"、"assistant"或"system"。
        :param token: 消息的令牌数。
        :param name: 消息发送者的名称。
        """
        self.tokens.append(token)
        self.current_token += token
        while self.current_token > self.max_tokens:
            self.remove_oldest_message()
        # 暂时不支持assistant和system消息
        match role:
            case "user":
                msg = Messages.user_message(content=message, name=name)
        self.conversation.append(msg)
        return msg

    # TODO: 图片消息
    # def add_image(self, url:str):
    #     local_url = fs.save_file(url)
    #     base64_image = fs.read_file_as_base64(local_url)
    #     self.conversation[self.index]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}})
    #     fs.remove_file(local_url)

    def remove_oldest_message(self):
        """
        移除最旧的消息。
        """
        if len(self.conversation) > 1:
            self.current_token -= self.tokens.pop(1)
            self.conversation.pop(1)

    def get_conversation(self) -> list[ChatCompletionMessageParam]:
        return self.conversation
    
    def set_preset(self, preset:ChatCompletionMessageParam, preset_token:int = 0):
        """
        设置预设消息。
        
        :param preset: 预设消息内容。
        :param preset_token: 预设消息的令牌数。
        """
        if preset_token > self.max_tokens:
            raise ValueError("预设消息的令牌数超过最大令牌数")
        if len(self.conversation) > 0:
            self.current_token -= self.tokens.pop(0)
            self.conversation.pop(0)
        self.conversation.insert(0, preset)
        self.tokens.insert(0, preset_token)
        self.current_token += preset_token

    def get_model(self):
        return self.model

class ConversationManager():
    """
    ConversationManager类用于管理多个会话。
    它提供了添加、获取和删除会话的方法。
    """
    conversations: dict[str, List[Conversation]]
    user_setting: dict[str,UserSetting]

    def __init__(self):
        self.conversations: dict[str, List[Conversation]] = {}
        self.user_setting: dict[str, UserSetting] = {}

    def get_user_setting(self, user_id: str) -> UserSetting | None:
        """
        获取指定用户的设置。
        
        :param user_id: 用户ID。
        :return: 用户设置对象，如果没有设置，则返回None。
        """
        return self.user_setting.get(user_id, None)
    
    def change_model(self, user_id: str, model: str):
        """
        更改指定用户的模型。
        
        :param user_id: 用户ID。
        :param model: 新模型名称。
        """
        if user_id in self.user_setting:
            self.user_setting[user_id].current_model = model
        else:
            self.user_setting[user_id] = UserSetting(current_model=model)
    
    def change_preset(self, user_id: str, model: str, preset: str):
        """
        更改指定用户的预设。
        
        :param user_id: 用户ID。
        :param model: 模型名称。
        :param preset: 新预设内容。
        """
        if user_id in self.user_setting:
            self.user_setting[user_id].preset[model] = preset
        else:
            self.user_setting[user_id] = UserSetting(preset={model: preset})
    
    def add_conversation(self, user_id: str, conversation: Conversation):
        if user_id in self.conversations:
            self.conversations[user_id].append(conversation)
            # 仅保留最近10条会话记录
            if len(self.conversations[user_id]) > 10:
                self.conversations[user_id].pop(0)
        else:
            self.conversations[user_id] = [conversation]
    
    def current_conversation(self, user_id: str) -> Conversation | None:
        """
        获取指定用户的最新会话。
        如果没有会话，则返回None。

        :param user_id: 用户ID
        :return: 会话对象，如果没有会话，则返回None。
        """
        if user_id in self.conversations and len(self.conversations[user_id]) > 0:
            return self.conversations[user_id][-1]
        return None

    def get_conversation(self, user_id: str, index: int = -1, update: bool = False) -> Conversation | None:
        """
        获取指定用户的最新会话。
        如果没有会话，则返回None。

        :param user_id: 用户ID
        :param index: 会话索引，默认为-1，表示获取最新会话。
        :param update: 是否更新会话，默认为False。
        :return: 会话对象，如果没有会话，则返回None。
        """
        if user_id in self.conversations and len(self.conversations[user_id]) > 0 and index < len(self.conversations[user_id]):
            if not update:
                return self.conversations[user_id][index]
            conversation = self.conversations[user_id].pop(index)
            self.conversations[user_id].append(conversation)
            return conversation
        return None
