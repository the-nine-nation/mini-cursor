[English](README.md) | [中文说明 (Chinese)](README_zh.md)

# mini-cursor

cursor一个月20美金,对于很多人而言,这是一个星期的饭食.cursor的闭源伤害了我们,天下苦其久已!

基于此,我们开源了一个使用命令行进行类cursor编程的超轻量级项目,以供各位学习使用.你可以在任意目录下使用mini-cursor ***以该目录为工作区使用AI agent编写程序!

本项目支持全本地/内网部署,不会存在任何泄露数据给外部的可能.你既可以使用外部api,也可以使用本地vllm或ollama启动的兼容openai api服务.

你可以使用该项目收集到优质的tool call数据,也可以在任何地方使用本项目准备好的与cursor基本一致的mcp服务(除却一个检索code的mcp,个人使用时发现效果不大),例如trea或自定义的程序中,以及中国境内可使用的检索服务.

## 更新

**20250422**: 新增Web界面，可直接通过命令行使用 `mini-cursor web` 启动。

**20250421**: 增加了对推理模型如deepseek-r1的支持。

**20250418**: 额外添加了web搜索以及安全连接sql和clickhouse数据库,经过测试,发现诸多模型皆有危险操作可能,因此与数据库相关操作均限制为只读.

## 特点

- 几乎1:1 复刻 cursor的 MCP 及 Prompt 实现,支持在vscode的其它插件中使用此处的若干mcp服务.
- 支持本地/远程多工具（MCP）调用.
- 支持 OpenAI api,允许使用本地模型,保障数据安全.
- **选择性工具启用**: 可以为每个会话选择要使用的工具
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
conda create -n mini-cursor python=3.10
conda activate mini-cursor
git clone https://github.com/the-nine-nation/mini-cursor.git
cd mini_cursor
pip install -e .
```

---

## 使用方法

### 1. 初始化 MCP 配置（强烈推荐，首次使用必做）

```bash
mini-cursor init
```
此命令会自动生成 `mini_cursor/core/mcp_config.json`，并自动填充正确的 Python 路径和 MCP 脚本路径,但部分参数需自行填写。
命令行会显示生成的json位置,若要给其它程序使用,复制该json内容即可.

> **注意：** 若要使用联网工具,生成后请务必使用`mini-cursor mcp-config`或直接编辑 `mcp_config.json`，填写你的 `BOCHAAI_API_KEY`.

####使用方法1: 直接使用mcp server

**示例 mcp_config.json 片段：**
```json
{
  "mcpServers": {
    "cursor_mcp": {
        "command": sys.executable,
        "args": [cursor_mcp_py],
        "env": {
            "BOCHAAI_API_KEY": "bochaai的api,请进入https://open.bochaai.com/获取api,使模型能够进行web搜索"
        }
    },
    "mysql": {
        "command": sys.executable,
        "args": [mysql_mcp_py],
        "env": {
            "MYSQL_ENABLED": "true",
            "MYSQL_HOST": "mysql数据库的ip",
            "MYSQL_PORT": "mysql数据库的端口",
            "MYSQL_DATABASE": "mysql数据库的名称",
            "MYSQL_USERNAME": "mysql数据库的用户名",
            "MYSQL_PASSWORD": "mysql数据库的密码",
            "MYSQL_POOL_MINSIZE": "1",
            "MYSQL_POOL_MAXSIZE": "10",
            "MYSQL_RESOURCE_DESC_FILE": "mysql数据库的资源描述文件路径"
        }
    },
    "clickhouse": {
        "command": sys.executable,
        "args": [clickhouse_mcp_py],
        "env": {
            "CLICKHOUSE_ENABLED": "true",
            "CLICKHOUSE_HOST": "clickhouse数据库的ip",
            "CLICKHOUSE_PORT": "clickhouse数据库的端口",
            "CLICKHOUSE_DATABASE": "clickhouse数据库的名称",
            "CLICKHOUSE_USERNAME": "clickhouse数据库的用户名",
            "CLICKHOUSE_PASSWORD": "clickhouse数据库的密码",
            "CLICKHOUSE_RESOURCE_DESC_FILE": "clickhouse数据库的资源描述文件路径"
            }
    }
  }
}
```
如果你想要智能体自动web搜索,可前往 [BochaAI](https://open.bochaai.com/) 获取对应api_key,以支持检索

### 2. 配置 API Key（必选，推荐）


```bash
mini-cursor config
```
按提示输入兼容 OpenAI 格式的  API Key、Base URL、模型名等，配置会写入 `.env` 文件。

### 3. 交互式编辑 MCP 服务器（默认自带全部cursor的mcp和一个web search,可不用改动）

```bash
mini-cursor mcp-config
```
可交互式添加/编辑/删除 MCP 服务器，配置会写入 `mini_cursor/core/mcp_config.json`。
你也可以复制这个config,粘贴到如cursor等

### 4. 启动智能体聊天

```bash
mini-cursor chat
```
- 支持自然语言提问、代码生成、工具调用等。
- 聊天过程中可随时输入 `help` 查看命令。

### 5. 启动Web界面

```bash
mini-cursor web
```
该命令会启动Web服务器并自动在浏览器中打开Web界面。Web界面提供了更加可视化和用户友好的方式与mini-cursor交互：

- 完整的聊天功能和流式响应
- 可视化工具调用展示
- 配置管理
- 对话历史查看

使用完毕后，可以在终端按下Ctrl+C停止Web服务器。

---

## 常用命令一览

| 命令                        | 说明                         |
|-----------------------------|------------------------------|
| `mini-cursor init`       | 初始化生成 MCP 配置（推荐）   |
| `mini-cursor config`     | 交互式修改 API 参数（写入.env）|
| `mini-cursor mcp-config` | 交互式生成/编辑 MCP 配置      |
| `mini-cursor chat`       | 启动智能体聊天                |
| `mini-cursor web`        | 启动Web界面                  |
| `mini-cursor help`       | 查看帮助              |

**聊天模式下支持的命令：**
- `history`             查看工具调用历史
- `message history`     查看消息历史
- `clear history`       清空消息历史
- `servers`             查看可用 MCP 服务器
- `config`              修改 API 参数
- `mcp-config`          编辑 MCP 配置
- `help`                显示帮助
- `quit`                退出聊天

**工具管理命令：**
- `enable <tool>`       启用特定工具
- `disable <tool>`      禁用特定工具
- `enable-all`          启用所有工具
- `disable-all`         禁用所有工具
- `mode <all|selective>` 设置工具启用模式（all:默认全部启用，selective:选择性启用）

---

## 开发指南

### 添加新工具

向MCP系统添加新工具的步骤：

1. 在`cursor_mcp_all.py`中定义工具或创建新的MCP服务器
2. 使用唯一名称和模式注册工具
3. 在`mcp_config.json`中配置服务器

### 扩展客户端

模块化架构使扩展功能变得简单：

1. UI更改：修改`display_utils.py`
2. 新消息处理：扩展`message_manager.py`
3. 增强工具功能：更新`tool_manager.py`，包括**工具启用/禁用管理**
4. 额外服务器类型：修改`server_manager.py`

### 自定义提示

自定义系统提示的方法：
1. 在传递给`process_query`之前修改`cli.py`中的提示
2. 为不同功能或工具使用不同提示

---

## Shell 自动补全

mini-cursor 支持命令自动补全（bash/zsh/fish）。

生成并加载补全脚本示例：

### Zsh
```sh
eval "$(mini-cursor completion zsh)"
```

### Bash
```sh
eval "$(mini-cursor completion bash)"
```

### Fish
```sh
eval (mini-cursor completion fish)
```

你也可以将补全脚本输出到对应配置文件，实现永久补全。 

---

## 项目结构

项目已经模块化重构，以提高代码的可读性和可维护性。以下是核心架构：

### 核心组件

- **`mcp_client.py`**：主客户端类，整合所有模块并作为入口点
- **`message_manager.py`**：管理对话历史，包括用户/系统/助手消息
- **`tool_manager.py`**：处理工具发现、工具调用，并维护工具调用历史
- **`server_manager.py`**：管理MCP服务器连接和配置
- **`display_utils.py`**：用于显示工具历史、服务器和消息历史的实用函数
- **`config.py`**：API密钥、URL和其他设置的中央配置管理

### 模块功能

#### MCPClient (mcp_client.py)
主客户端类，协调LLM、MCP服务器和用户之间的交互：
- 管理聊天循环和对话流程
- 通过LLM处理用户查询
- 处理流式响应
- 根据LLM决策编排工具调用

#### MessageManager (message_manager.py)
负责消息历史管理的所有方面：
- 添加用户消息和系统提示
- 跟踪助手响应
- 记录工具调用及其结果
- 修剪对话历史以防止上下文溢出
- 提供清晰的历史记录检索

#### ToolManager (tool_manager.py)
管理所有与工具相关的功能：
- 发现并编目所有MCP服务器的可用工具
- 为每个工具找到合适的服务器
- 使用超时处理执行工具调用
- 维护详细的工具调用历史
- 格式化API调用的工具参数
- **管理工具的启用/禁用状态**，实现选择性工具使用

#### ServerManager (server_manager.py)
处理与MCP服务器的连接和通信：
- 从配置文件加载服务器配置
- 建立与指定服务器的连接
- 初始化与每个服务器的会话
- 管理服务器资源和清理

#### DisplayUtils (display_utils.py)
提供用户友好的显示功能：
- 工具调用历史的格式化输出
- 服务器和工具列表
- 消息历史可视化

---

## 进阶用法

- **支持多种大模型**：只需在 `.env` 里切换 `OPENAI_MODEL` 和 `OPENAI_BASE_URL`。
- **自定义工具/服务器**：编辑 `mini-cursor mcp-config`，可添加本地或远程 Python 服务。
- **工具扩展**：支持文件读写、代码编辑、终端命令、Web 搜索等多种工具，详见 `mini_cursor/core/tool_specs.json`。
- **选择性工具使用**：通过 `enable <tool>`、`disable <tool>` 控制工具启用状态，或使用 `mode <all|selective>` 设置启用模式。这允许更受控、更安全、更专注的工具使用体验。

---

## 常见问题

- **pip 安装后命令不可用？**
  - 请确认 Python 的 bin 目录已加入 PATH，或重启终端。
- **API Key 泄露风险？**
  - 推荐只在本地 `.env` 文件中配置，勿上传到公开仓库。
- **如何切换工作区？**
  - 进入目标目录后再运行 `mini-cursor chat`，工作区即为当前目录。

---

## 贡献与开发

欢迎 PR、Issue、二次开发！  
如需自定义 prompt、工具、MCP 服务等，详见源码注释和 `mini_cursor/prompt.py`。

---

## License

MIT 

## FastAPI 后端

Mini-Cursor 现在包含一个带有 SSE 流式传输支持的 FastAPI 后端。这提供了一个用于聊天功能的 Web API。

### 安装

安装所需的依赖项：

```bash
pip install -r requirements.txt
```

### 运行 API 服务器

启动 FastAPI 服务器：

```bash
python -m mini_cursor.main_api
```

默认情况下，服务器将在 `http://0.0.0.0:8000` 上运行。你可以通过设置 `HOST` 和 `PORT` 环境变量来自定义主机和端口。

### API 端点

#### GET /

返回有关 API 的基本信息。

#### POST /chat

用于聊天功能的端点，支持 SSE 流式传输。接受包含以下内容的 JSON 负载：

- `query`（必需）：发送给 AI 的消息
- `system_prompt`（可选）：自定义系统提示
- `workspace`（可选）：工作空间路径

请求示例：

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "你能做什么？"}'
```

此端点返回具有以下事件类型的服务器发送事件（SSE）：

- `start`：表示开始处理
- `message`：AI 助手的文本响应
- `thinking`：支持思考过程的模型的推理过程
- `tool_call`：正在进行的工具调用信息
- `tool_result`：工具调用的结果
- `tool_error`：工具调用期间发生的错误
- `done`：表示处理完成
- `error`：处理期间发生的任何错误

