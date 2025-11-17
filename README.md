# NicholasOfficialBot

一个基于 NoneBot 的多功能 QQ/聊天机器人，支持多模型对话、掷骰子、帮助查询等能力。

## 快速开始
1. **准备环境**
   - Python 3.10+，建议创建虚拟环境。
   - `pip install -r requirements.txt`
2. **配置环境变量**
   - 复制 `.env.example` 为 `.env`，填写 `HOST/PORT/DRIVER`、`SETTINGS_FILE`（默认 `config/settings.yaml`）等基础配置。
   - 在 `.env` 或 `.env.<env>` 中填写敏感信息：`QQ_BOTS`、各模型的密钥（如 `CHAT__KEY`）、OPENAI/DeepSeek 的 API Key 等。
3. **配置 YAML**
   - `config/settings.yaml` 中定义插件命令、默认模型、骰子默认参数等。模型配置（base_url、tokenizer_dir、max_tokens）也在此维护。
4. **启动**
   - `python src/bot.py`
   - 通过 QQ 机器人或命令行适配器与之交互。

## 主要功能
- **Chat 对话**
  - 支持 DeepSeek、ChatGPT（gpt-5.1）等模型，图片会自动编码；历史会话持久化，短 ID 查询/分页查看。
  - 常用指令：`/bbm` 发起对话，`/bbm-c` 继续，`/bbm-m` 切换模型，`/bbm-p` 设置预设，`/bbm-i` 查看配置，`/bbm-l` 列历史，`/bbm-lc` 翻页，`/bbm-r` 重置预设。
- **Dice 掷骰**
  - 命令：`/r <公式>`，支持重复、优势/劣势、默认骰面、昵称。
  - 示例：`/r d20`，`/r 2d20h+3`，`/r 2#d20+3`；子指令 `/r-f <面数>` 设置默认骰面，`/r-nn <昵称>` 设置昵称。
- **Help 帮助**
  - `/help` 查看插件列表或具体命令用法。

## 配置要点
- `.env`：基础运行参数与敏感凭据；`SETTINGS_FILE` 指定 YAML。
- `config/settings.yaml`：插件命令树、默认模型/骰子参数、模型列表与限额；可为 Dice 配置 `default_sides/max_sides/max_repeat/max_count_per_term`。
- 数据存储：
  - Chat：`data/chat.db`（会话与历史），`data/temp_img`（临时图片，老会话清理时同步删除）。
  - Dice：`data/dice.db`（用户默认骰面与昵称）。

## 脚本
- `scripts/Requirement.bat` 安装依赖
- `scripts/Setup.bat` 初始化环境
- `scripts/Run.bat` 运行

## 扩展
- 新插件遵循命令注册与配置方式（见 Chat/Dice/Help），配置放入 `config/settings.yaml`，命令处理放入 `command_handler.py`。
- 持久化统一使用 `data` 目录的 SQLite，并在插件加载时初始化表。
