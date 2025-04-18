import json
import os
import traceback
import logging
from typing import Dict
from contextlib import AsyncExitStack

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from mini_cursor.core.config import Colors, MCP_CONFIG_FILE, VERBOSE_LOGGING

# 设置日志
logger = logging.getLogger(__name__)

class ServerManager:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.sessions = {}  # 存储多个MCP server会话
        
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
                print(f"{Colors.YELLOW}No MCP servers configured. Falling back to default terminal server.{Colors.ENDC}")
                # 回退到默认配置
                server_configs = {
                    "terminal": {
                        "command": "/Volumes/AppData/opt/anaconda3/envs/mcp_env/bin/python",
                        "args": ["/Volumes/AppData/guanan/lzy/mcp_lzy/core/mcp_data_all/terminal_server.py"],
                        "env": None
                    }
                }
            
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
            
            # 创建所有工具的合并列表用于调试
            all_tools = {}
            for server_name, tools in tool_manager.server_tools.items():
                for tool_name, tool in tools.items():
                    if tool_name in all_tools:
                        print(f"{Colors.YELLOW}Warning: Tool '{tool_name}' is provided by multiple servers{Colors.ENDC}")
                    all_tools[tool_name] = (server_name, tool)
            
            print(f"Total available tools: {len(all_tools)}")
            
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