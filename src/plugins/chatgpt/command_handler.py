from .config import Config
from util import get_command
from nonebot.adapters import Message, Event
from nonebot.params import CommandArg
from nonebot import get_plugin_config
from nonebot.internal.matcher import Matcher
from .chatgpt import Session
from openai import OpenAI
from nonebot import logger

# Get the plugin config
plugin_config = get_plugin_config(Config).chatgpt
command_list: dict[str, type[Matcher]] = get_command(plugin_config.commands)

chat = command_list["ChatGPT"]

session_list:dict[str,Session] = {}
client = OpenAI(
    api_key=plugin_config.key
)
@chat.handle()
async def _(event: Event, args: Message = CommandArg()):
    id = str(event.get_user_id())
    if id not in session_list:
        session_list[id] = Session(plugin_config.model, plugin_config.preset)
    session = session_list[id]
    session.new_message("user")
    for msgSegment in args:
        if msgSegment.type == "image":
            url = msgSegment.data["url"]
            session.add_image(url)
        elif msgSegment.type == "text":
            session.add_text(msgSegment.data["text"])
    completion = client.chat.completions.create(model=session.get_model(), messages=session.get_conversation())
    if(completion.choices[0].message.content != None):
        session.new_message(completion.choices[0].message.role)
        session.add_text(completion.choices[0].message.content)
    else:
        logger.info(completion)
    await chat.finish(completion.choices[0].message.content)
    
