"""
MCP QA Core Package

This package contains the core functionality for the MCP QA CLI application.

mini_cursor.core: MCP核心功能模块
"""

from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.core.message_manager import MessageManager
from mini_cursor.core.tool_manager import ToolManager
from mini_cursor.core.server_manager import ServerManager
from mini_cursor.core.display_utils import display_tool_history, display_servers, display_message_history

__all__ = [
    'MCPClient',
    'MessageManager', 
    'ToolManager',
    'ServerManager',
    'display_tool_history',
    'display_servers',
    'display_message_history'
]

__version__ = "0.1.0" 