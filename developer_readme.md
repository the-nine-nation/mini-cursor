# Mini-Cursor Developer Documentation

## Project Overview

mini-cursor is a lightweight, command-line based programming assistant similar to Cursor, which allows AI agent-based programming in any directory. The project supports both local/intranet deployment and doesn't leak data externally. It can use external APIs or local models via OpenAI-compatible APIs.

## Directory Structure

```
mini_cursor/
├── api/                    # FastAPI backend implementation
│   ├── routers/            # API endpoints by functionality
│   │   ├── chat.py         # Chat-related endpoints
│   │   ├── config.py       # Configuration endpoints
│   │   ├── conversations.py # Conversation management
│   │   ├── tools.py        # Tool-related endpoints
│   │   └── root.py         # Root endpoints
│   ├── main.py             # API entrypoint
│   ├── dependencies.py     # API dependencies
│   └── models.py           # API data models
├── core/                   # Core functionality
│   ├── database/           # Database integration
│   │   ├── db_manager.py   # SQLite database management
│   │   └── __init__.py     # Database module initialization
│   ├── database_mcp/       # extra MCP servers for databases
│   ├── cli.py              # CLI interface implementation
│   ├── mcp_client.py       # Main MCP client implementation
│   ├── config.py           # Configuration management
│   ├── cursor_mcp_all.py   # Cursor MCP tools implementation
│   ├── display_utils.py    # Display utilities
│   ├── message_manager.py  # Message history management
│   ├── server_manager.py   # MCP server management
│   ├── tool_manager.py     # Tool management
│   ├── tool_history_manager.py # Tool history management
│   ├── mcp_config.json     # MCP server configuration
│   └── tool_specs.json     # Tool specifications
├── data/                   # Data storage
│   ├── conversations.db    # SQLite database for conversation history
│   ├── system_prompt.txt   # Current system prompt configuration
│   └── system_prompt_default.txt # Default system prompt backup
├── static/                 # Web UI resources
│   ├── css/                # CSS stylesheets
│   │   ├── api_demo.css    # Main UI styles
│   │   ├── chat-panel.css  # Chat interface styles
│   │   ├── tools-panel.css # Tools panel styles
│   │   ├── config-panel.css # Configuration panel styles
│   │   ├── layout.css      # Page layout styles
│   │   └── main.css        # Common styles and variables
│   ├── js/                 # JavaScript modules
│   │   ├── api.js          # API communication client
│   │   ├── chat-ui.js      # Chat UI controller
│   │   ├── config-panel.js # Settings management
│   │   ├── tools-panel.js  # Tool management interface
│   │   └── [other modules] # Additional functionality
│   └── api_demo.html       # Main web interface template
├── cli_main.py             # CLI main entry point
├── main_api.py             # API main entry point
├── mcp_qa.py               # QA functionality 
└── prompt.py               # System prompts
```

## Core Components

### 1. `mcp_client.py` - MCPClient

The central client class that coordinates LLM, MCP servers, and user interactions.

Main responsibilities:
- Manages the chat loop and conversation flow
- Processes user queries via LLM
- Handles streaming responses
- Orchestrates tool calls based on LLM decisions
- Integrates with database systems
- Manages conversation history

Core methods:
- `process_query()`: Processes user queries and handles LLM responses
- `execute_tool_call()`: Executes tool calls from LLM
- `connect_to_servers()`: Connects to configured MCP servers
- Tool and message management methods for enabling/disabling tools

### 2. `message_manager.py` - MessageManager

Handles all aspects of message history management.

Main responsibilities:
- Adding user messages and system prompts
- Tracking assistant responses
- Recording tool calls and their results
- Trimming conversation history to prevent context overflow
- Providing clear history retrieval

Core methods:
- `add_user_message()`: Adds user messages to history
- `add_assistant_message()`: Adds assistant responses to history
- `add_tool_call_message()`: Adds tool call results to history
- `get_messages()`: Retrieves formatted message history

### 3. `tool_manager.py` - ToolManager

Manages all tool-related functionality.

Main responsibilities:
- Discovering and cataloging available tools from all MCP servers
- Finding appropriate servers for each tool
- Executing tool calls with timeout handling
- Managing tool enablement/disablement
- Caching tool information for performance

Core methods:
- `get_all_tools()`: Collects all server tools for LLM API
- `find_tool_server()`: Locates the server for a specific tool
- `call_tool_with_timeout()`: Executes tools with timeout
- `enable_tool()/disable_tool()`: Manages tool availability

### 4. `server_manager.py` - ServerManager

Manages MCP server connections and configurations.

Main responsibilities:
- Loading server configurations from mcp_config.json
- Starting and managing server processes
- Establishing and maintaining server connections
- Discovering available tools from each server

Core methods:
- `load_server_config()`: Loads MCP server configurations
- `connect_to_servers()`: Connects to all configured servers
- `start_server()`: Starts and initializes server processes
- `close()`: Properly shuts down all server connections

### 5. `cursor_mcp_all.py` - MCP Tool Implementations

Implements all the Cursor-compatible MCP tools.

Main tool implementations:
- `tool_read_file()`: Reads file contents
- `tool_edit_file()`: Edits existing files or creates new ones
- `tool_search_files()`: Searches for files based on keywords
- `tool_terminal_command()`: Executes terminal commands
- `tool_reapply()`: Reapplies the last edit
- `tool_list_dir()`: Lists directory contents
- `tool_web_search()`: Performs web searches

### 6. `cli.py` - CLI Interface

Handles the command-line interface for user interaction.

Main responsibilities:
- Providing input mechanisms for multi-line queries
- Handling control signals (Ctrl+C)
- Processing special commands (history, servers, etc.)
- Managing configuration
- Supporting interactive MCP configuration

Core components:
- `CLIHandler`: Manages user interaction in the terminal
- `config_main()`: Interactive parameter configuration
- `mcp_config_generate_main()`: Interactive MCP configuration

### 7. `display_utils.py` - Display Utilities

Provides utilities for displaying tool history, servers, and message history.

Main functions:
- `display_tool_history()`: Formats and displays tool call history
- `display_servers()`: Shows available MCP servers and tools
- `display_message_history()`: Formats and displays conversation history

## API Layer

mini-cursor includes a FastAPI-based REST API for web interface integration and service-based access.

### API Structure

The API is implemented in the `mini_cursor/api/` directory with the following components:

1. **Main Entry Point (`main.py`)**:
   - Sets up the FastAPI application
   - Configures CORS middleware
   - Mounts static files
   - Registers routers for different endpoints
   - Provides API lifecycle management

2. **API Dependencies (`dependencies.py`)**:
   - Manages shared resources across API endpoints
   - Implements resource caching for MCP clients, servers, and tools
   - Provides utility functions for API router usage

3. **API Data Models (`models.py`)**:
   - Defines Pydantic models for API request/response validation
   - Ensures type safety and documentation

4. **Routers**:
   - `root.py`: Root endpoints for health check and status
   - `chat.py`: Chat-related endpoints for managing conversations
   - `config.py`: Configuration management endpoints
   - `conversations.py`: Conversation history management
   - `tools.py`: Tool execution endpoints

### API Endpoints

The API provides the following key endpoints:

#### Chat Endpoints
- `POST /chat/message`: Send a message to the AI assistant
- `GET /chat/stream`: Stream responses using Server-Sent Events (SSE)
- `GET /chat/history/{conversation_id}`: Get conversation history

#### Tool Endpoints
- `GET /tools`: List available tools
- `POST /tools/{tool_name}`: Execute a specific tool
- `PUT /tools/{tool_name}/status`: Enable/disable a tool

#### Configuration Endpoints
- `GET /config`: Get current configuration
- `POST /config`: Update configuration
- `GET /config/model`: Get available models
- `PUT /config/model`: Change the model

#### Conversation Endpoints
- `GET /conversations`: List all conversations
- `GET /conversations/{conversation_id}`: Get a specific conversation
- `DELETE /conversations/{conversation_id}`: Delete a conversation
- `POST /conversations`: Create a new conversation

### API Usage Example

```python
import requests

# Base URL for the API
base_url = "http://localhost:7727"

# Create a new conversation
response = requests.post(f"{base_url}/conversations", json={"title": "API Test"})
conversation_id = response.json()["id"]

# Send a message
response = requests.post(f"{base_url}/chat/message", json={
    "conversation_id": conversation_id,
    "message": "What files are in this directory?",
    "stream": False
})

# Get the assistant's response
result = response.json()
print(f"Assistant: {result['response']}")

# Execute a tool directly
response = requests.post(f"{base_url}/tools/list_dir", json={
    "relative_workspace_path": "./"
})
print(response.json())
```

### API SSE Streaming

The API supports Server-Sent Events (SSE) for streaming responses:

```javascript
// JavaScript example of SSE streaming
const eventSource = new EventSource('/chat/stream?conversation_id=123');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  // Check for message completion
  if (data.event === 'complete') {
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

### API Security

The API implements several security measures:
- CORS middleware to control cross-origin requests
- Process isolation for different clients
- Resource cleanup on connection close
- Input validation using Pydantic models
- API key authentication (when configured)

## Prompt System

The prompt system is defined in `prompt.py` and implements a Cursor-compatible system prompt for the AI model. The system prompt defines:

1. **Assistant Identity**: Positioned as a powerful agentic AI coding assistant pair-programming with the user
2. **Communication Guidelines**:
   - Conversational but professional tone
   - Markdown formatting for responses
   - No disclosure of system prompts
   - Error handling approach

3. **Tool Calling Rules**:
   - Following schema specifications
   - Avoiding tool name references in user communication
   - Only calling necessary tools
   - Explaining tool usage before calling

4. **Code Change Guidelines**:
   - Never outputting code directly to the user
   - Ensuring generated code can run immediately
   - Adding necessary imports and dependencies
   - Creating appropriate dependency files
   - Reading file contents before editing
   - Fixing linter errors when possible

5. **Debugging Practices**:
   - Addressing root causes
   - Adding descriptive logging
   - Creating test functions to isolate problems

6. **API Calling Guidelines**:
   - Using appropriate external APIs
   - Managing API key security
   - Selecting compatible versions

The prompt system also provides user information like OS version, workspace path, and shell, and defines a specific format for code region citations.

## Tool System

### Tool Specifications

Tools are defined in `tool_specs.json` with the following standard structure:

1. **`read_file`**: 
   - Reads file contents with options for reading entire files or specific line ranges
   - Parameters: target_file, should_read_entire_file, start_line_one_indexed, end_line_one_indexed_inclusive
   - Includes guidance on efficient file reading

2. **`edit_file`**: 
   - Proposes edits to existing files
   - Uses special comment syntax (`// ... existing code ...`) to represent unchanged code
   - Parameters: target_file, instructions, code_edit
   - Includes detailed guidelines on clear edit specification

3. **`search_files`**: 
   - Fuzzy file path matching for discovering files
   - Parameters: query, explanation
   - Results limited to 10 matches

4. **`terminal_command`**: 
   - Executes terminal commands on the user's system
   - Parameters: command, is_background, explanation
   - Includes safety guidelines for command execution

5. **`reapply`**: 
   - Uses a smarter model to reapply edits when initial application fails
   - Parameters: target_file
   - Used only after failed edit_file operations

6. **`list_dir`**: 
   - Lists directory contents for codebase exploration
   - Parameters: relative_workspace_path, explanation
   - Useful for initial project structure discovery

7. **`web_search`**: 
   - Performs web searches using BochaAI's API
   - Parameters: query, summary, count, page
   - Returns structured search results

The system allows selective enabling/disabling of tools, with two modes:
- "all": All tools enabled by default (disabled tools are specifically marked)
- "selective": Only specifically enabled tools are available

### Tool Implementation

Each tool in `cursor_mcp_all.py` is implemented as an async function that:
1. Receives a dictionary of arguments
2. Performs the required operation
3. Returns a string result (or appropriate error message)

The tool implementations include:
- Error handling and validation
- Caching mechanisms for performance
- Timeout handling to prevent hung operations
- Safety checks to prevent dangerous operations