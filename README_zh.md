[English](README.md) | [中文说明 (Chinese)](README_zh.md)

# mini-cursor

cursor一个月20美金,对于很多人而言,这是一个星期的饭食.cursor的闭源伤害了我们,天下苦其久已!

基于此,我们开源了一个使用命令行进行类cursor编程的超轻量级项目,以供各位学习使用.你可以在任意目录下使用mini-cursor cli ***以该目录为工作区使用AI agent编写程序!

你可以使用该项目收集到优质的tool call数据

## 特点

- 几乎1:1 复刻 cursor的 MCP 及 Prompt 实现,支持在vscode的其它插件中使用此处的若干mcp服务.
- 支持本地/远程多工具（MCP）调用
- 支持 OpenAI/Claude/GLM 等多种大模型
- 交互式参数和服务器配置
- 一键 pip 安装，命令行全局可用
- 适合二次开发和自定义扩展

---

## 安装方法

### 方式一：pip 安装（暂时未支持,现在处于测试阶段）

```bash
pip install mini_cursor
```

### 方式二：源码安装（开发者/自定义）

```bash
git clone https://github.com/the-nine-nation/mini-cursor.git
cd mini_cursor
pip install -e .
```

---

## 快速开始

### 1. 初始化 MCP 配置（强烈推荐，首次使用必做）

```bash
mini-cursor cli init
```
此命令会自动生成 `mini_cursor/core/mcp_config.json`，并自动填充正确的 Python 路径和 MCP 脚本路径。

> **注意：** 生成后请务必使用`mini-cursor cli mcp-config`或直接编辑 `mcp_config.json`，填写你的 `BOCHAAI_API_KEY`，否则联网查询工具无法使用！

**示例 mcp_config.json 片段：**
```json
{
  "mcpServers": {
    "default": {
      "command": "/usr/bin/python3",
      "args": ["/your/abs/path/mini_cursor/core/cursor_mcp_all.py"],
      "env": {
        "BOCHAAI_API_KEY": "sk-xxxx"
      }
    }
  }
}
```
如果你想要智能体自动web搜索,可前往 [BochaAI](https://open.bochaai.com/) 获取对应api_key,以支持检索

### 2. 配置 API Key（必选，推荐）


```bash
mini-cursor cli config
```
按提示输入兼容 OpenAI 格式的  API Key、Base URL、模型名等，配置会写入 `.env` 文件。

### 3. 交互式编辑 MCP 服务器（可选）

```bash
mini-cursor cli mcp-config
```
可交互式添加/编辑/删除 MCP 服务器，配置会写入 `mini_cursor/core/mcp_config.json`。
你也可以复制这个config,粘贴到如cursor等

### 4. 启动智能体聊天

```bash
mini-cursor cli chat
```
- 支持自然语言提问、代码生成、工具调用等。
- 聊天过程中可随时输入 `help` 查看命令。

---

## 常用命令一览

| 命令                        | 说明                         |
|-----------------------------|------------------------------|
| `mini-cursor cli init`       | 初始化生成 MCP 配置（推荐）   |
| `mini-cursor cli config`     | 交互式修改 API 参数（写入.env）|
| `mini-cursor cli mcp-config` | 交互式生成/编辑 MCP 配置      |
| `mini-cursor cli chat`       | 启动智能体聊天                |

**聊天模式下支持的命令：**
- `history`             查看工具调用历史
- `message history`     查看消息历史
- `clear history`       清空消息历史
- `servers`             查看可用 MCP 服务器
- `config`              修改 API 参数
- `mcp-config`          编辑 MCP 配置
- `help`                显示帮助
- `quit`                退出聊天

---

## .env 配置示例

```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

---

## 进阶用法

- **支持多种大模型**：只需在 `.env` 里切换 `OPENAI_MODEL` 和 `OPENAI_BASE_URL`。
- **自定义工具/服务器**：编辑 `mini-cursor cli mcp-config`，可添加本地或远程 Python 服务。
- **工具扩展**：支持文件读写、代码编辑、终端命令、Web 搜索等多种工具，详见 `mini_cursor/core/tool_specs.json`。

---

## 常见问题

- **pip 安装后命令不可用？**
  - 请确认 Python 的 bin 目录已加入 PATH，或重启终端。
- **API Key 泄露风险？**
  - 推荐只在本地 `.env` 文件中配置，勿上传到公开仓库。
- **如何切换工作区？**
  - 进入目标目录后再运行 `mini-cursor cli chat`，工作区即为当前目录。

---

## 贡献与开发

欢迎 PR、Issue、二次开发！  
如需自定义 prompt、工具、MCP 服务等，详见源码注释和 `mini_cursor/prompt.py`。

---

## License

MIT 