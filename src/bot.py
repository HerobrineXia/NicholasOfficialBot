import nonebot
from nonebot.adapters.onebot import V12Adapter as NoneBotAdapter # type: ignore
from nonebot.adapters.console import Adapter as ConsoleAdapter # type: ignore
from nonebot.adapters.qq import Adapter as QQAdapter # type: ignore
from pathlib import Path

import nonebot.plugins 
from os import chdir

# Initialize
nonebot.init()

print(nonebot.get_driver().config)

# Register Driver
driver = nonebot.get_driver()
driver.register_adapter(NoneBotAdapter)
# driver.register_adapter(ConsoleAdapter)
driver.register_adapter(QQAdapter)

# Change working directory to the directory of this file
chdir(Path(__file__).parent)

# Load Plugins
nonebot.load_plugins("./plugins")

if __name__ == "__main__":
    nonebot.run()
