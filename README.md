[English](README.md) | [中文说明 (Chinese)](README_zh.md)

# mini-cursor

Cursor costs $20 per month, which is a week's worth of food for many people. Its closed-source nature has been a pain for the community for too long!

Therefore, we open-sourced a super lightweight command-line project for Cursor-like programming, for everyone to learn and use.You can use mini-cursor cli in any directory to write programs using AI agents with this directory as the workspace!

You can use the high-quality tool call data collected by this project.

## Features

- Nearly 1:1 reimplementation of Cursor's MCP and Prompt, supports using these MCP services in other VSCode plugins.
- Supports local/remote multi-tool (MCP) invocation
- Supports multiple LLMs: OpenAI/Claude/GLM, etc.
- Interactive parameter and server configuration
- One-click pip install, globally available CLI
- Great for secondary development and custom extensions

---

## Installation

### Method 1: pip install (not supported temporarily)

```bash
pip install mini_cursor
```

### Method 2: Source install (for developers/customization)

```bash
git clone https://github.com/the-nine-nation/mini-cursor.git
cd mini_cursor
pip install -e .
```

---

## Quick Start

### 1. Initialize MCP Config (Highly Recommended, Do This First)

```bash
mini-cursor cli init
```
This command will automatically generate `mini_cursor/core/mcp_config.json` with the correct Python and MCP script paths.

> **Note:** After generation, be sure to use `mini-cursor cli mcp-config` or directly edit `mcp_config.json` to fill in your `BOCHAAI_API_KEY`. Without it, online query tools will not work!

**Example mcp_config.json snippet:**
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

### 2. Configure API Key (Required/Recommended)

```bash
mini-cursor cli config
```
Follow the prompts to enter your OpenAI-compatible API Key, Base URL, model name, etc. The config will be saved to `.env`.

### 3. Interactively Edit MCP Servers (Optional)

```bash
mini-cursor cli mcp-config
```
Interactively add/edit/delete MCP servers. The config is saved to `mini_cursor/core/mcp_config.json`.
You can also copy this config and use it in Cursor, etc.

### 4. Start Chat Agent

```bash
mini-cursor cli chat
```
- Supports natural language Q&A, code generation, tool invocation, etc.
- Type `help` at any time during chat for available commands.

---

## Common Commands

| Command                      | Description                        |
|------------------------------|------------------------------------|
| `mini-cursor cli init`       | Initialize MCP config (recommended) |
| `mini-cursor cli config`     | Interactive API param config (.env) |
| `mini-cursor cli mcp-config` | Interactive MCP config editor       |
| `mini-cursor cli chat`       | Start chat agent                   |
| `mini-cursor-server`         | Start MCP server (dev/extension)   |

**In chat mode, you can use:**
- `history`             View tool call history
- `message history`     View message history
- `clear history`       Clear message history
- `servers`             View available MCP servers
- `config`              Edit API params
- `mcp-config`          Edit MCP config
- `help`                Show help
- `quit`                Exit chat

---

## .env Example

```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

---

## Advanced Usage

- **Support for multiple LLMs:** Just change `OPENAI_MODEL` and `OPENAI_BASE_URL` in `.env`.
- **Custom tools/servers:** Use `mini-cursor cli mcp-config` to add local or remote Python services.
- **Tool extension:** Supports file read/write, code editing, terminal commands, web search, etc. See `mini_cursor/core/tool_specs.json` for details.

---

## FAQ

- **Command not found after pip install?**
  - Make sure Python's bin directory is in your PATH, or restart your terminal.
- **API Key leak risk?**
  - Only configure your API Key in the local `.env` file. Do not upload it to public repos.
- **How to switch workspace?**
  - Change to your target directory before running `mini-cursor cli chat`. The workspace is the current directory.

---

## Contribution & Development

PRs, issues, and secondary development are welcome!
For custom prompts, tools, MCP services, see code comments and `mini_cursor/prompt.py`.

---

## License

MIT
