import nonebot
from nonebot.adapters.onebot import V12Adapter as NoneBotAdapter # type: ignore
from nonebot.adapters.console import Adapter as ConsoleAdapter # type: ignore
from nonebot.adapters.qq import Adapter as QQAdapter # type: ignore
from pathlib import Path
from os import chdir

if __name__ == "__main__":
    # 初始化NoneBot
    nonebot.init()

    # 初始化配置
    driver = nonebot.get_driver()
    driver.register_adapter(NoneBotAdapter)
    driver.register_adapter(QQAdapter)

    # 修改当前工作目录为该文件所在目录
    chdir(Path(__file__).parent)

    # 加载插件
    nonebot.load_plugins("./plugins")
    
    nonebot.run()
