#!/usr/bin/env python3

import os
import platform
import traceback
from pathlib import Path

from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.core.server_manager import ServerManager
from mini_cursor.core.tool_manager import ToolManager
from mini_cursor.core.message_manager import MessageManager
from mini_cursor.core.database import get_db_manager

# 获取操作系统版本
os_version = platform.platform()

# 获取shell路径
shell_path = os.environ.get('SHELL', '未知')

# 服务器和管理器缓存
server_manager_cache = {}
tool_manager_cache = {}
client_cache = {}
# 错误状态缓存
configuration_errors = {}

# 当前模块路径，用于静态文件
current_dir = Path(__file__).parent.parent
static_dir = current_dir / "static"

async def get_managers():
    """获取或创建服务器管理器和工具管理器实例"""
    # 使用进程 ID 作为缓存键，确保每个进程使用独立的管理器实例
    pid = os.getpid()
    
    if pid not in server_manager_cache:
        # 创建服务器管理器和工具管理器
        server_manager = ServerManager()
        tool_manager = ToolManager()
        
        try:
            # 连接到MCP服务器
            await server_manager.connect_to_servers(tool_manager)
            # 成功连接，清除可能存在的错误
            if pid in configuration_errors:
                configuration_errors[pid].pop('mcp_servers', None)
        except Exception as e:
            # 捕获所有异常，但仍然返回部分功能的管理器
            error_msg = f"MCP服务器连接失败: {str(e)}"
            traceback_str = traceback.format_exc()
            if pid not in configuration_errors:
                configuration_errors[pid] = {}
            configuration_errors[pid]['mcp_servers'] = {
                'error': error_msg,
                'traceback': traceback_str
            }
            print(f"警告: {error_msg}")
        
        # 无论连接是否成功，都缓存管理器
        server_manager_cache[pid] = server_manager
        tool_manager_cache[pid] = tool_manager
    
    return server_manager_cache[pid], tool_manager_cache[pid]

async def get_client():
    """获取或创建 MCP 客户端实例"""
    # 使用进程 ID 作为缓存键，确保每个进程使用独立的客户端实例
    pid = os.getpid()
    
    if pid not in client_cache:
        # 获取服务器管理器和工具管理器
        server_manager, tool_manager = await get_managers()
        
        # 创建消息管理器
        message_manager = MessageManager()
        
        # 创建客户端实例
        client = MCPClient()
        client.server_manager = server_manager
        client.tool_manager = tool_manager
        client.message_manager = message_manager
        
        try:
            if pid in configuration_errors:
                configuration_errors[pid].pop('openai_api', None)
        except Exception as e:
            # 捕获所有异常，但仍然返回部分功能的客户端
            error_msg = f"OpenAI客户端初始化失败: {str(e)}"
            traceback_str = traceback.format_exc()
            if pid not in configuration_errors:
                configuration_errors[pid] = {}
            configuration_errors[pid]['openai_api'] = {
                'error': error_msg,
                'traceback': traceback_str
            }
            print(f"警告: {error_msg}")
        
        # 无论初始化是否成功，都缓存客户端
        client_cache[pid] = client
    
    return client_cache[pid]

def get_configuration_errors():
    """获取当前进程的配置错误"""
    pid = os.getpid()
    return configuration_errors.get(pid, {})

def get_enabled_tool_names(tool_manager):
    """辅助函数：获取已启用的工具名称列表"""
    enabled_tools = []
    try:
        all_tools = tool_manager.get_all_tools()
        enabled_tools = [tool["function"]["name"] for tool in all_tools if "function" in tool and "name" in tool["function"]]
    except Exception as e:
        print(f"Error getting enabled tools: {e}")
    return enabled_tools 