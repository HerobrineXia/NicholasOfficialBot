# Chatbot
一个由 Python 驱动的多功能聊天机器人。

## 配置说明
- 运行参数（如 `HOST`、`PORT`、驱动、命令前缀分隔符等）仍保留在 `.env` 中，通过 `SETTINGS_FILE` 指向需要读取的结构化配置文件（默认 `config/settings.yaml`）。
- 插件元数据、命令树以及模型预设集中描述在 `config/settings.yaml` 内；程序会先读取该文件，再由环境变量或 `.env.<env>` 覆盖，便于将敏感信息与版本库隔离。
- 模型密钥、QQ Bot 凭据等敏感内容应写在 `.env.dev`、`.env.prod` 或由 `ENVIRONMENT` 指定的文件里，Settings 初始化前会自动加载这些文件。

## 迁移步骤
1. 将旧 `.env` 里的 JSON 块（命令配置、模型配置等）复制进 `config/settings.yaml` 对应位置，本仓库已提供示例。
2. 保持 `.env` 只存放标量配置，删除原来的大段 `CHAT__*`、`HELP__*` JSON 字符串，避免编辑冲突。
3. 将模型密钥、机器人令牌等敏感字段写入对应环境的 `.env.<env>`，它们会覆盖 YAML 中的默认值且不会被提交。
4. 运行 `scripts/Run.bat`（或你的常用入口）验证 NoneBot 是否成功加载统一配置。
