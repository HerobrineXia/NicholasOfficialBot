# 项目概览

## 运行路径
- 入口脚本 `src/bot.py` 初始化 NoneBot，注册 OneBot V12 适配器后加载 `./plugins`，启动前会切换到 `src` 目录。
- `.env` 提供 HOST/PORT/DRIVER 等环境变量；`config/settings.yaml` 存放结构化默认配置。
- 依赖通过 `scripts/Requirement.bat` 安装；DeepSeek 模型 tokenizer 置于 `external/deepseek`（按需下载）。

### 核心配置与数据模型
- `src/config/config.py` 定义 Args、CommandData、DefaultPluginConfig，作为所有插件的配置基类。
- `src/config/settings.py` 仅承载全局基础设置（端口、命令起始符等），插件配置由各插件自行加载。

### 辅助层
- `src/util/commands.py` 暴露 get_command/get_metadata，将命令描述映射到 matcher 与 PluginMetadata。
- `src/util/file_system.py` 封装下载、Base64 转换、文件删除等 I/O，调用时需注意目录安全。

### 功能插件
- **chat**：`config.py` 管理模型；`AI.py` 实现 DeepSeek 客户端；`chat.py` 处理会话与用户状态；`service.py` 管理客户端/会话及消息预处理，供 handler 调用；`command_handler.py` 只负责指令流转。
- **help**：读取插件 metadata，生成帮助文本，支持按命令/别名/插件名称查询。
- **dice**：当前只是 on() matcher 的占位实现，收到消息仅打印日志。

### 运行流程
1. 通过 `scripts/Run.bat` 调用 `python src/bot.py` 启动。
2. NoneBot 初始化并读取 `.env` 与 `.env.local`，注册适配器后加载 `plugins`。
3. 插件加载时构建各自的 metadata/命令 matcher；Help 基于元数据回复。
4. OneBot 收到消息后触发匹配的 matcher；Chat 使用 ConversationManager/ClientManager 通过客户端调用模型返回回复。

## 优化建议
1. **配置集中管理（已完成）**：全局基础设置放在 `src/config/settings.py`，插件配置由各插件自加载（YAML + 可选 env），解耦 Settings。
2. **职责拆分（已完成）**：util 已拆为 `util/commands.py` 与 `util/file_system.py`，避免 `from util import *`。
3. **Chat 职责细分（已完成）**：新增 `chat/service.py`，封装客户端初始化、消息预处理、会话与调用流程；handler 只做协议层转发。
4. **优化 Help 递归（已完成）**：重写 Help 格式化与查找逻辑，避免重复遍历全量元数据，递归输出命令树（见 `plugins/help/command_handler.py`）。
5. **状态持久化方案（已完成）**：将会话/用户设置持久化到 Redis/SQLite/文件，支持多实例与重启恢复。
6. **路径与存储安全**：`file_system.save_file` 建议使用绝对 Path 组装并校验合法目录，避免依赖 chdir 导致的相对路径风险。
