from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletion
from typing import Protocol, List, runtime_checkable
from transformers import AutoTokenizer # type: ignore

from .chat import Conversation, Messages

@runtime_checkable
class AIClientProtocol(Protocol):
    """
    AIClientProtocol接口定义了与AI客户端交互的方法。
    """
    
    def chat_completion(self, messages: List[ChatCompletionMessageParam], model:str) -> ChatCompletion:
        ...

    def get_token(self, messages: str) -> int:
        ...

    def new_chat(self, model: str, preset: str = "") -> Conversation:
        ...

class AIClient():
    """
    AIClient类用于与AI API进行交互的客户端。
    它包含API密钥、模型和基本URL等信息。
    会初始化OpenAI客户端。
    """
    models: List[str] = []
    preset: List[str] = []
    max_input_tokens: List[int] = []
    max_output_tokens: List[int] = []
    api_key: str = ""
    base_url: str = ""
    client: OpenAI

    def __init__(self, models: List[str], preset: List[str], max_input_tokens: List[int], max_output_tokens: List[int], api_key: str, base_url: str):
        """
        初始化AIClient实例。

        Args:
            model (str): AI模型的名称。
            preset (str): 预设消息。
            max_tokens (int): 最大令牌数。
            api_key (str): API密钥。
            base_url (str): API的基本URL。
        """
        self.models = models
        self.preset = preset
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self.api_key = api_key
        self.base_url = base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def get_models(self) -> List[str]:
        return self.models

class DeepSeekClient(AIClient):
    """
    DeepSeekClient类用于与DeepSeek AI API进行交互。
    它继承自AIClient类，并实现了get_model和chat_completion方法。
    """
    tokenizer = None

    def __init__(self, models: List[str], preset: List[str], max_input_tokens: List[int], max_output_tokens: List[int], api_key: str, base_url: str):
        super().__init__(models, preset, max_input_tokens, max_output_tokens, api_key, base_url)
    
    def init_tokenizer(self, chat_tokenizer_dir: str):
        self.tokenizer = AutoTokenizer.from_pretrained(chat_tokenizer_dir, trust_remote_code=True)

    def new_chat(self, model: str, preset: str = "") -> Conversation:
        if model not in self.models:
            raise ValueError(f"模型 {model} 不在可用模型列表中。")
        conversation = Conversation(model, self.max_input_tokens[self.models.index(model)])
        preset_text = self.preset[self.models.index(model)] if preset == "" else preset
        conversation.set_preset(Messages.system_message(preset_text), self.get_token(preset_text))
        return conversation
        
    def chat_completion(self, messages: List[ChatCompletionMessageParam], model: str) -> ChatCompletion:
        if model not in self.models:
            raise ValueError(f"模型 {model} 不在可用模型列表中。")
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=self.max_output_tokens[self.models.index(model)]
        )
        return response
    
    def get_token(self, message: str) -> int:
        if self.tokenizer is None:
            raise ValueError("Tokenizer未初始化，请先调用init_tokenizer方法。")
        result = self.tokenizer.encode(message)
        return len(result)

class ClientManager:
    """
    ClientManager类用于管理AI客户端实例。
    它提供了获取模型名称、与AI进行对话和获取令牌数的方法。
    """
    clients: dict[str, AIClient] = {}
    all_models: List[str]

    def __init__(self):
        self.clients = {}
        self.all_models = []
    
    def add_client(self, name: str, client: AIClient):
        """
        添加一个新的AI客户端实例。

        :params name: 客户端名称。
        :params client: AIClient实例。
        """
        self.clients[name] = client
        self.all_models.extend(client.get_models())
    
    def get_client_with_model(self, model: str) -> AIClient | None:
        """
        获取具有指定模型的AI客户端实例。

        :params model: 模型名称。
        :return: AIClient实例或None。
        """
        if model not in self.all_models:
            return None
        for client in self.clients.values():
            if model in client.get_models():
                return client
        return None

def chat_completion(client: AIClientProtocol, messages: list[ChatCompletionMessageParam], model:str) -> ChatCompletion:
    """
    与AI进行对话并获取响应。
    
    :params client: 实现了AIClientProtocol的客户端实例。
    :params messages: 消息列表，包含用户和AI的消息。
    :return: AI的响应。
    """
    return client.chat_completion(messages, model)

def new_chat(client: AIClientProtocol, model: str, preset: str = "") -> Conversation:
    """
    创建一个新的对话实例。
    
    :params client: 实现了AIClientProtocol的客户端实例。
    :params model: 模型名称。
    :params preset: 预设消息，默认为空字符串。
    :return: Conversation实例。
    """
    return client.new_chat(model, preset)

def get_text_token(client: AIClientProtocol, messages: str) -> int:
    """
    获取消息的令牌数。
    
    :params client: 实现了AIClientProtocol的客户端实例。
    :params messages: 消息列表，包含用户和AI的消息。
    :return: 消息的令牌数。
    """
    return client.get_token(messages)

def get_message_token(client: AIClientProtocol, messages: ChatCompletionMessageParam) -> int:
    """
    获取消息的令牌数。
    
    :params client: 实现了AIClientProtocol的客户端实例。
    :params messages: 消息列表，包含用户和AI的消息。
    :return: 消息的令牌数。
    """
    token = 0
    content = messages.get("content")
    match content:
        # 获取单段消息的令牌数
        case str():
            token += client.get_token(content)
        # 获取多段消息的令牌数
        case list():
            for message in content:
                text =  message.get("text")
                if text is not None:
                    token += client.get_token(text)
    return token