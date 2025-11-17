# Chatbot
一个由 Python 驱动的多功能聊天机器人。

## 配置说明
- 运行参数（如 `HOST`、`PORT`、驱动、命令前缀分隔符等）仍保留在 `.env` 中，通过 `SETTINGS_FILE` 指向需要读取的结构化配置文件（默认 `config/settings.yaml`）。
- 插件元数据、命令树以及模型预设集中描述在 `config/settings.yaml` 内；程序会先读取该文件，再由环境变量或 `.env.<env>` 覆盖，便于将敏感信息与版本库隔离。
- 模型密钥、QQ Bot 凭据等敏感内容应写在 `.env.dev`、`.env.prod` 或由 `ENVIRONMENT` 指定的文件里，Settings 初始化前会自动加载这些文件。
