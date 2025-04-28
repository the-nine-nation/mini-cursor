[English](README.md) | [中文说明 (Chinese)](README_zh.md)

# mini-cursor

Cursor costs $20 per month, which is a week's worth of food for many people. Its closed-source nature has been a pain for the community for too long!

Therefore, we open-sourced a super lightweight command-line project for Cursor-like programming, for everyone to learn and use. You can use mini-cursor in any directory to write programs using AI agents with this directory as the workspace!

This project supports fully local/intranet deployment with no possibility of data leakage to external parties. You can use external APIs or local vllm/ollama services that are compatible with the OpenAI API.

## Update

**2025-04-28**: MCP services for MySQL and ClickHouse will no longer be included as default MCP services.
- MySQL MCP repository: [mysql-mcp](https://github.com/the-nine-nation/mysql-mcp)
- ClickHouse MCP repository: [clickhouse-mcp](https://github.com/the-nine-nation/clickhouse-mcp)

**20250422**: Added web interface that can be launched directly from the CLI with `mini-cursor web`.

**20250421**: Added support for inference models like deepseek-r1.

**20250418**: You can use this project to collect high-quality tool call data, or use the MCP services prepared by this project that are essentially identical to Cursor's (except for a code retrieval MCP, which I found to be not very effective in personal use). Additionally, this project adds web search and secure connections to SQL and ClickHouse databases. After testing, it was found that many models may have dangerous operations, so all database-related operations are restricted to read-only.

## Features

- Nearly 1:1 reimplementation of Cursor's MCP and Prompt, supports using these MCP services in other VSCode plugins.
- Supports local/remote multi-tool (MCP) invocation
- Supports OpenAI API, allows using local models, ensuring data security.
- **Selective tool enablement**: Choose which tools to use for each session
- Interactive parameter and server configuration
- One-click pip install, globally available CLI
- Great for secondary development and custom extensions

---

## Installation

### Method 1: pip install (not supported temporarily, currently in testing phase)

```bash
pip install mini_cursor
```

### Method 2: Source install (for developers/customization)

```bash
conda create -n mini-cursor python=3.10
conda activate mini-cursor
git clone https://github.com/the-nine-nation/mini-cursor.git
cd mini_cursor
pip install -e .
```

---

## Usage

### 1. Initialize MCP Config (Highly Recommended, Do This First)

```bash
mini-cursor init
```
This command will automatically generate `mini_cursor/core/mcp_config.json` with the correct Python and MCP script paths, but some parameters need to be filled in manually.
The command line will show the location of the generated JSON file. If you want to use it with other programs, you can copy the JSON content.

> **Note:** If you want to use the web search tool, after generation, be sure to use `mini-cursor mcp-config` or directly edit `mcp_config.json` to fill in your `BOCHAAI_API_KEY`.

#### Usage Method 1: Use MCP Server Directly

**Example mcp_config.json snippet:**
```json
{
  "mcpServers": {
    "cursor_mcp": {
        "command": sys.executable,
        "args": [cursor_mcp_py],
        "env": {
            "BOCHAAI_API_KEY": "API key from https://open.bochaai.com/ to enable web search for the model"
        }
    }
  }
}
```
If you want the agent to perform automatic web search, you can go to [BochaAI](https://open.bochaai.com/) to obtain the corresponding api_key to support retrieval.

### 2. Configure API Key (Required, Recommended)

```bash
mini-cursor config
```
Follow the prompts to enter your OpenAI-compatible API Key, Base URL, model name, etc. The config will be saved to `.env`.

### 3. Interactively Edit MCP Servers (Comes with all Cursor MCPs and web search by default, no need to modify)

```bash
mini-cursor mcp-config
```
Interactively add/edit/delete MCP servers. The config is saved to `mini_cursor/core/mcp_config.json`.
You can also copy this config and use it in Cursor, etc.

### 4. Start Chat Agent

```bash
mini-cursor chat
```
- Supports natural language Q&A, code generation, tool invocation, etc.
- Type `help` at any time during chat for available commands.

### 5. Launch Web Interface

```bash
mini-cursor web
```
This command starts the web server and automatically opens your default browser to access the web interface. The web interface provides a more visual and user-friendly way to interact with mini-cursor:

- Full chat capabilities with streaming responses
- Visual tool call display
- Configuration management
- Conversation history viewing

You can press Ctrl+C in the terminal to stop the web server when you're done.

---

## Common Commands

| Command                      | Description                        |
|------------------------------|------------------------------------|
| `mini-cursor init`       | Initialize MCP config (recommended) |
| `mini-cursor config`     | Interactive API param config (.env) |
| `mini-cursor mcp-config` | Interactive MCP config editor       |
| `mini-cursor chat`       | Start chat agent                   |
| `mini-cursor web`        | Launch the web interface           |
| `mini-cursor help`       | Show help                          |

**In chat mode, you can use:**
- `history`             View tool call history
- `message history`     View message history
- `clear history`       Clear message history
- `servers`             View available MCP servers
- `config`              Edit API params
- `mcp-config`          Edit MCP config
- `help`                Show help
- `quit`                Exit chat

**Tool management commands:**
- `enable <tool>`       Enable a specific tool
- `disable <tool>`      Disable a specific tool
- `enable-all`          Enable all tools
- `disable-all`         Disable all tools
- `mode <all|selective>` Set the tool enablement mode

---

## Project Structure

The project has been modularized to improve code readability and maintainability. Here's the core architecture:

### Core Components

- **`mcp_client.py`**: Main client class that integrates all modules and serves as the entry point
- **`message_manager.py`**: Manages conversation history, including user/system/assistant messages
- **`tool_manager.py`**: Handles tool discovery, tool calls, and maintains tool call history
- **`server_manager.py`**: Manages MCP server connections and configurations
- **`display_utils.py`**: Utility functions for displaying tool histories, servers, and message histories
- **`config.py`**: Central configuration management for API keys, URLs, and other settings

### Module Functionality

#### MCPClient (mcp_client.py)
The main client class that coordinates interactions between the LLM, MCP servers, and user. It:
- Manages the chat loop and conversation flow
- Processes user queries through the LLM
- Handles streaming responses
- Orchestrates tool calls based on LLM decisions

#### MessageManager (message_manager.py)
Responsible for all aspects of message history management:
- Adding user messages and system prompts
- Tracking assistant responses
- Recording tool calls and their results
- Trimming conversation history to prevent context overflow
- Providing clean history retrieval

#### ToolManager (tool_manager.py)
Manages all tool-related functionality:
- Discovers and catalogs available tools from all MCP servers
- Finds the appropriate server for each tool
- Executes tool calls with timeout handling
- Maintains detailed tool call history
- Formats tool parameters for API calls
- **Manages tool enablement/disablement** for selective tool usage

#### ServerManager (server_manager.py)
Handles connection and communication with MCP servers:
- Loads server configurations from config files
- Establishes connections to specified servers
- Initializes sessions with each server
- Manages server resources and cleanup

#### DisplayUtils (display_utils.py) 
Provides user-friendly display functions:
- Formatted output for tool call history
- Server and tool listings
- Message history visualization

---

## Development Guide

### Adding New Tools

To add new tools to the MCP system:

1. Define the tool in `cursor_mcp_all.py` or create a new MCP server
2. Register the tool with a unique name and schema
3. Configure the server in `mcp_config.json`

### Extending the Client

The modular architecture makes it easy to extend functionality:

1. For UI changes: modify `display_utils.py`
2. For new message handling: extend `message_manager.py`
3. For enhanced tool capabilities: update `tool_manager.py`
4. For additional server types: modify `server_manager.py`

### Custom Prompts

To customize the system prompt:
1. Modify the prompt in `cli.py` before passing to `process_query`
2. Use different prompts for different functionalities or tools

---

## Shell Autocompletion

mini-cursor supports command autocompletion (bash/zsh/fish).

Generate and load the completion script:

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

You can also output the completion script to the corresponding config file for permanent autocompletion.

---

## Advanced Usage

- **Support for multiple LLMs:** Just change `OPENAI_MODEL` and `OPENAI_BASE_URL` in `.env`.
- **Custom tools/servers:** Use `mini-cursor mcp-config` to add local or remote Python services.
- **Tool extension:** Supports file read/write, code editing, terminal commands, web search, etc. See `mini_cursor/core/tool_specs.json` for details.
- **Selective tool usage:** Control which tools are enabled using `enable <tool>`, `disable <tool>`, or set the mode with `mode <all|selective>`. This allows for more controlled, secure, and focused tool usage.

---

## FAQ

- **Command not found after pip install?**
  - Make sure Python's bin directory is in your PATH, or restart your terminal.
- **API Key leak risk?**
  - Only configure your API Key in the local `.env` file. Do not upload it to public repos.
- **How to switch workspace?**
  - Change to your target directory before running `mini-cursor chat`. The workspace is the current directory.

---

## Contribution & Development

PRs, issues, and secondary development are welcome!
For custom prompts, tools, MCP services, see code comments and `mini_cursor/prompt.py`.

---

## License

MIT

## Fast API Backend

Mini-Cursor now includes a FastAPI backend with SSE streaming support. This provides a web API for chat functionality.

### Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the API Server

To start the FastAPI server:

```bash
python -m mini_cursor.main_api
```

By default, the server will run on `http://0.0.0.0:8000`. You can customize the host and port by setting the `HOST` and `PORT` environment variables.

### API Endpoints

#### GET /

Returns basic information about the API.

#### POST /chat

Endpoint for chat functionality with SSE streaming. Accepts a JSON payload with:

- `query` (required): The message to send to the AI
- `system_prompt` (optional): Custom system prompt
- `workspace` (optional): Workspace path

Example request:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "What can you do?"}'
```

This endpoint returns Server-Sent Events (SSE) with the following event types:

- `start`: Indicates the start of processing
- `message`: AI assistant's text responses
- `thinking`: Reasoning process from models that support it
- `tool_call`: Information about tool calls being made
- `tool_result`: Results of tool calls
- `tool_error`: Errors that occur during tool calls
- `done`: Indicates the completion of processing
- `error`: Any errors that occur during processing
