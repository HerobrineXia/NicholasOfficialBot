# 项目概览

## 运行路径
- 入口脚本 `src/bot.py` 初始化 NoneBot，注册 OneBot V12 适配器后加载 `./plugins`，并在启动前切换到 `src` 目录。
- `.env` 提供 HOST/PORT/DRIVER 等环境变量；`config/settings.yaml` 存放结构化默认配置。
- 依赖通过 `scripts/Requirement.bat` 安装；DeepSeek 模型的 tokenizer 放在 `external/deepseek`（按需下载）。

### 核心配置与数据模型
- `src/config/config.py` 定义 Args、CommandData、DefaultPluginConfig，作为所有插件的配置基类。
- `src/config/settings.py` 只负责全局基础设置（运行端口、命令起始符等），插件配置各自按需加载。

### 辅助层
- `src/util/commands.py` 暴露 get_command/get_metadata，将命令描述映射到 matcher 与 PluginMetadata。
- `src/util/file_system.py` 封装下载、Base64 转换、文件删除等 I/O，调用时需注意目录安全。

### 功能插件
- **chat**：`config.py` 管理模型；`AI.py` 实现 DeepSeek 客户端；`chat.py` 处理会话与用户状态；`command_handler.py` 负责命令调度，初始化 ConversationManager/ClientManager 并加载模型/预设。
- **help**：读取插件 metadata，生成帮助文本，支持按命令/别名/插件名称查询。
- **dice**：当前只是 on() matcher 的占位实现，收到消息仅打印日志。

### 运行流程
1. 通过 `scripts/Run.bat` 调用 `python src/bot.py` 启动。
2. NoneBot 初始化并读取 `.env` 与 `.env.local`，注册适配器后加载 `plugins`。
3. 插件加载时构建各自的 metadata/命令 matcher；Help 直接基于这些元数据回复。
4. OneBot 收到消息后触发匹配的 matcher；Chat 使用 ConversationManager/ClientManager 调用 DeepSeek/OpenAI 并返回回复。

## 优化建议
1. **配置集中管理**：已通过 `src/config/settings.py` 统一全局设置，插件配置由各插件自加载（YAML + 可选 env），减轻 Settings 的耦合。
2. **职责拆分（已完成）**：原 util 同时负责命令元数据和文件 I/O，已拆成 `util/commands.py` 与 `util/file_system.py`，并更新引用避免 `from util import *`。
3. **Chat 职责再细分**：建议将客户端管理、消息预处理、会话逻辑拆到 service/domain 层，handler 仅做协议转换与调用。
4. **优化 Help 递归**：可重构 generate_help_message，缓存或按需生成，避免每次遍历全量元数据。
5. **状态持久化方案**：将会话/用户设置持久化到 Redis/SQLite/文件，支持多实例和重启恢复。
6. **路径与存储安全**：`file_system.save_file` 优先使用绝对 Path 拼装并校验合法目录，避免依赖 chdir 导致的相对路径风险。
7. **开发者体验**：补充跨平台脚本（如 Makefile/Invoke/Poetry）与 lint/format 任务，降低上手成本。***
