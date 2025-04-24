import os
import json
import asyncio
import traceback
import logging
from typing import Dict
from contextlib import AsyncExitStack
import time

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from mini_cursor.core.config import Colors, MCP_CONFIG_FILE, VERBOSE_LOGGING

# 设置日志
logger = logging.getLogger(__name__)

class ServerManager:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions = {}  # 存储多个MCP server会话
        self.main_loop = None  # 存储主事件循环的引用
    
    def set_main_loop(self, loop):
        """设置主事件循环的引用，用于在线程中执行工具调用"""
        self.main_loop = loop
        
    def load_mcp_config(self) -> Dict[str, Dict]:
        """从配置文件加载MCP服务器配置"""
        try:
            with open(MCP_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('mcpServers', {})
        except FileNotFoundError:
            print(f"{Colors.YELLOW}Warning: MCP config file {MCP_CONFIG_FILE} not found.{Colors.ENDC}")
            return {}
        except json.JSONDecodeError:
            print(f"{Colors.RED}Error: MCP config file {MCP_CONFIG_FILE} contains invalid JSON.{Colors.ENDC}")
            return {}
    
    async def connect_to_servers(self, tool_manager):
        """连接到配置的所有MCP服务器"""
        try:
            # 加载MCP服务器配置
            server_configs = self.load_mcp_config()
            
            if not server_configs:
                raise RuntimeError("No MCP servers configured in mcp_config.json")
            
            connected_servers = []
            
            # 连接到每个配置的服务器
            for server_name, config in server_configs.items():
                try:
                    print(f"\n{Colors.CYAN}Connecting to MCP server: {server_name}...{Colors.ENDC}")
                    
                    # 创建环境变量字典
                    env_vars = os.environ.copy()
                    if isinstance(config.get('env'), dict):
                        env_vars.update(config['env'])
                    
                    server_params = StdioServerParameters(
                        command=config['command'],
                        args=config['args'],
                        env=env_vars
                    )

                    stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                    stdin, stdout = stdio_transport
                    session = await self.exit_stack.enter_async_context(ClientSession(stdin, stdout))
                    
                    # 初始化会话
                    await session.initialize()
                    
                    # 列出可用工具
                    response = await session.list_tools()
                    tools = response.tools
                    
                    # 保存会话和工具信息
                    self.sessions[server_name] = session
                    tool_manager.set_session(server_name, session)
                    tool_manager.set_server_tools(server_name, tools)
                    
                    connected_servers.append(server_name)
                    print(f"{Colors.GREEN}Connected to server {server_name} with {len(tools)} tools{Colors.ENDC}")
                    
                except Exception as e:
                    print(f"{Colors.RED}Error connecting to server {server_name}: {e}{Colors.ENDC}")
                    if VERBOSE_LOGGING:
                        traceback.print_exc()
            
            if not connected_servers:
                raise Exception("Failed to connect to any MCP servers")
                
            print(f"\n{Colors.GREEN}Connected to {len(connected_servers)} MCP servers: {', '.join(connected_servers)}{Colors.ENDC}")
            
            # 构建并缓存所有工具的列表，以便在process_query中使用
            all_tools_count = len(tool_manager.refresh_tools_cache())
            print(f"Total available tools: {all_tools_count}")
            
        except Exception as e:
            print(f"\n{Colors.RED}Error connecting to MCP servers: {e}{Colors.ENDC}")
            raise
    
    async def close(self):
        """清理资源"""
        try:
            # 检查是否有数据库服务器需要特殊处理
            # 某些MCP服务器可能需要额外的清理步骤
            for server_name, session in self.sessions.items():
                if 'mysql' in server_name.lower() or 'clickhouse' in server_name.lower():
                    logger.info(f"Closing database connection for {server_name}")
                    # MCP服务器可能实现了一个特殊的关闭方法
                    if hasattr(session, 'close_connections'):
                        await session.close_connections()
            
            # 最后关闭所有的exit_stack内容
            await self.exit_stack.aclose()
            print("\nMCP servers and database connections closed.")
        except Exception as e:
            print(f"\nError during MCP server shutdown: {e}")
            # 即使出错也尝试关闭exit_stack
            try:
                await self.exit_stack.aclose()
            except:
                pass
                
    async def execute_tool(self, server_name, tool_name, tool_args):
        """执行特定服务器上的工具调用"""
        try:
            # 简化为直接执行工具调用实现
            if server_name not in self.sessions:
                raise Exception(f"Server {server_name} not connected")
            
            session = self.sessions[server_name]
            
            # 记录开始执行的时间（用于日志）
            start_time = time.time()
            
            # 执行工具调用
            try:
                # 直接使用当前会话执行工具调用
                print(f"{Colors.GREEN}Executing tool {tool_name} on server {server_name}...{Colors.ENDC}")
                response = await session.call_tool(tool_name, tool_args)
                elapsed = time.time() - start_time
                print(f"Tool {tool_name} executed in {elapsed:.2f}s")
            except Exception as e:
                # 捕获并改进工具调用过程中的错误
                error_msg = f"Server {server_name} failed to execute tool {tool_name}: {str(e)}"
                print(f"{Colors.RED}{error_msg}{Colors.ENDC}")
                
                if VERBOSE_LOGGING:
                    traceback.print_exc()
                
                return error_msg
            
            # 处理响应
            # 首先尝试常见的属性
            if hasattr(response, 'result'):
                return response.result
            elif hasattr(response, 'output'):
                return response.output
            
            # 使用pydantic的model_dump方法（最常见的情况）
            if hasattr(response, 'model_dump'):
                try:
                    result_dict = response.model_dump()
                    
                    # 从字典中提取结果字段
                    if 'result' in result_dict:
                        return result_dict['result']
                    elif 'output' in result_dict:
                        return result_dict['output']
                    
                    # 如果没有特定字段，尝试获取第一个内容字段
                    for key, value in result_dict.items():
                        if key in ['content', 'text', 'data', 'message', 'response']:
                            return value
                    
                    # 如果没有特定字段，返回整个字典的简化版本
                    return json.dumps(result_dict, ensure_ascii=False)
                except Exception as e:
                    if VERBOSE_LOGGING:
                        print(f"{Colors.YELLOW}Error during result conversion: {str(e)}{Colors.ENDC}")
                    pass  # 静默失败，继续尝试其他方法
            
            # 如果是列表，可能包含TextContent对象（MCP标准格式）
            if isinstance(response, list) and len(response) > 0:
                # 尝试提取第一个元素的文本
                first_item = response[0]
                if hasattr(first_item, 'text'):
                    return first_item.text
                elif hasattr(first_item, 'content'):
                    return first_item.content
                
                # 如果是字典类型的列表元素，尝试提取内容
                if isinstance(first_item, dict):
                    for key in ['text', 'content', 'data', 'message']:
                        if key in first_item:
                            return first_item[key]
            
            # 最后尝试直接转换为字符串
            return str(response)
                
        except Exception as e:
            error_msg = f"Error executing tool {tool_name} on server {server_name}: {str(e)}"
            print(f"{Colors.RED}{error_msg}{Colors.ENDC}")
            
            if VERBOSE_LOGGING:
                traceback.print_exc()
            
            return error_msg 