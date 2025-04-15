import asyncio
import json
import os
import time
import traceback
from typing import Dict, List, Optional, Any, Tuple
from contextlib import AsyncExitStack

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import mcp.types as types
from openai import AsyncOpenAI

from mini_cursor.core.config import Colors, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, TOOL_CALL_TIMEOUT, VERBOSE_LOGGING, MCP_CONFIG_FILE


class MCPClient:
    def __init__(self):
        self.sessions = {}  # 存储多个MCP server会话
        self.server_tools = {}  # 存储每个服务器的工具
        self.exit_stack = AsyncExitStack()
        self.client = AsyncOpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        # 添加工具调用历史记录
        self.tool_history = []
        # 添加消息历史记录
        self.message_history = []
    
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
    
    async def connect_to_servers(self):
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
                    self.server_tools[server_name] = {tool.name: tool for tool in tools}
                    
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
            for server_name, tools in self.server_tools.items():
                for tool_name, tool in tools.items():
                    if tool_name in all_tools:
                        print(f"{Colors.YELLOW}Warning: Tool '{tool_name}' is provided by multiple servers{Colors.ENDC}")
                    all_tools[tool_name] = (server_name, tool)
            
            print(f"Total available tools: {len(all_tools)}")
            
        except Exception as e:
            print(f"\n{Colors.RED}Error connecting to MCP servers: {e}{Colors.ENDC}")
            raise
    
    async def call_tool_with_timeout(self, server_name: str, tool_name: str, tool_args: Dict):
        """使用指定服务器带超时机制调用工具"""
        # 记录到工具历史
        call_record = {
            "server": server_name,
            "tool": tool_name,
            "args": tool_args,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "success": False,
            "result": None,
            "error": None
        }
            
        try:
            # 显示工具参数
            print(f"\n{Colors.BOLD}{Colors.CYAN}[🔧 Tool Parameters for {server_name}/{tool_name}]{Colors.ENDC}")
            for key, value in tool_args.items():
                print(f"  {Colors.YELLOW}{key}{Colors.ENDC}: {value}")
            print(f"{Colors.CYAN}{'=' * 40}{Colors.ENDC}")
            
            session = self.sessions.get(server_name)
            
            if not session:
                raise ValueError(f"No session found for server {server_name}")
            
            start_time = time.time()
            # 设置超时
            result = await asyncio.wait_for(
                session.call_tool(tool_name, tool_args),
                timeout=TOOL_CALL_TIMEOUT
            )
            elapsed = time.time() - start_time
            
            # 显示工具执行结果
            print(f"{Colors.BOLD}{Colors.GREEN}[🔄 Tool Result ({elapsed:.2f}s)]{Colors.ENDC}")
            if hasattr(result, 'content'):
                result_content = result.content
            else:
                result_content = result.get('content', f"Tool {server_name}/{tool_name} completed with unknown result")
            
            # 记录结果到历史
            call_record["success"] = True
            call_record["result"] = result_content
            call_record["duration"] = elapsed
            
            # 如果结果太长，截断显示
            MAX_DISPLAY_LENGTH = 1000
            if len(str(result_content)) > MAX_DISPLAY_LENGTH:
                print(f"{str(result_content)[:MAX_DISPLAY_LENGTH]}\n{Colors.YELLOW}... (结果太长已截断){Colors.ENDC}")
            else:
                print(result_content)
            print(f"{Colors.GREEN}{'=' * 40}{Colors.ENDC}")
            
            return result
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            error_msg = f"Tool call timed out after {TOOL_CALL_TIMEOUT} seconds"
            print(f"\n{Colors.BOLD}{Colors.RED}[❌ {error_msg}]{Colors.ENDC}")
            
            # 记录错误到历史
            call_record["success"] = False
            call_record["error"] = error_msg
            call_record["duration"] = elapsed
            
            # 创建超时响应对象
            timeout_content = f"执行超时 (>{TOOL_CALL_TIMEOUT}秒)。对于长时间运行的命令，请考虑添加超时或使用后台执行方式。"
            return dict(content=timeout_content)
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Error calling tool {server_name}/{tool_name}: {str(e)}"
            print(f"\n{Colors.BOLD}{Colors.RED}[❌ {error_msg}]{Colors.ENDC}")
            
            # 记录错误到历史
            call_record["success"] = False
            call_record["error"] = str(e)
            call_record["duration"] = elapsed
            
            if VERBOSE_LOGGING:
                print(f"{Colors.RED}详细错误信息:{Colors.ENDC}")
                traceback.print_exc()
                
            return dict(content=f"Error: {str(e)}")
            
        finally:
            # 无论成功或失败，都记录到历史
            self.tool_history.append(call_record)
    
    def find_tool_server(self, tool_name: str) -> Tuple[Optional[str], Optional[Any]]:
        """查找提供特定工具的服务器"""
        for server_name, tools in self.server_tools.items():
            if tool_name in tools:
                return server_name, tools[tool_name]
        return None, None
    
    async def process_query(self, query: str, system_prompt: str, stream=True) -> str:
        """使用 LLM 和 多个 MCP 服务器提供的工具处理查询"""
        # 创建系统信息
        system_message = {
            "role": "system",
            "content": system_prompt
        }
        
        # 添加新的用户查询到消息历史
        user_message = {
            "role": "user",
            "content": query
        }
        
        # 如果历史为空，添加系统消息；否则保持现有历史并只添加用户消息
        if not self.message_history:
            self.message_history = [system_message, user_message]
        else:
            # 检查第一条消息是否为系统消息，如果是则更新它
            if self.message_history[0]["role"] == "system":
                self.message_history[0] = system_message
                self.message_history.append(user_message)
            else:
                # 如果没有系统消息，则添加一个
                self.message_history = [system_message] + self.message_history + [user_message]
        
        # 裁剪消息历史以控制上下文窗口大小
        self._trim_message_history()
        
        # 使用完整的消息历史
        messages = self.message_history

        # 收集所有服务器的工具
        all_tools = []
        for server_name, tools_dict in self.server_tools.items():
            for tool_name, tool in tools_dict.items():
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"[{server_name}] {tool.description}",
                        "parameters": tool.inputSchema
                    }
                })

        final_text = []
        
        try:
            # 初始化 LLM API 调用，使用流式响应
            if stream:
                stream_response = await self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    tools=all_tools,
                    stream=True
                )
                
                # 处理流式响应
                collected_messages = []
                collected_content = ""
                tool_calls = []
                
                print(f"\n{Colors.BOLD}{Colors.CYAN}Response:{Colors.ENDC} ", end="", flush=True)
                async for chunk in stream_response:
                    delta = chunk.choices[0].delta
                    
                    # 处理内容部分
                    if delta.content:
                        print(f"{delta.content}", end="", flush=True)
                        collected_content += delta.content
                    
                    # 处理工具调用部分
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            # 初始化新的工具调用或更新现有的
                            tool_call_id = tool_call_delta.index
                            while len(tool_calls) <= tool_call_id:
                                tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                            
                            if tool_call_delta.id:
                                tool_calls[tool_call_id]["id"] = tool_call_delta.id
                            
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    tool_calls[tool_call_id]["function"]["name"] = tool_call_delta.function.name
                                
                                if tool_call_delta.function.arguments:
                                    tool_calls[tool_call_id]["function"]["arguments"] += tool_call_delta.function.arguments
                
                # 完成流式处理，构建最终消息
                message = type('obj', (object,), {
                    'content': collected_content,
                    'tool_calls': [type('obj', (object,), {
                        'id': t["id"],
                        'function': type('obj', (object,), {
                            'name': t["function"]["name"],
                            'arguments': t["function"]["arguments"]
                        })
                    }) for t in tool_calls if t["id"]]
                })
                
                if collected_content:
                    final_text.append(collected_content)
                    # 将结果添加到消息历史
                    self.message_history.append({
                        "role": "assistant",
                        "content": collected_content
                    })
            else:
                # 非流式处理
                response = await self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    tools=all_tools
                )
                message = response.choices[0].message
                if message.content:
                    print(f"\nResponse: {message.content}")
                    final_text.append(message.content or "")
                    
                    # 将结果添加到消息历史
                    self.message_history.append({
                        "role": "assistant",
                        "content": message.content or ""
                    })
            
            # 处理工具调用
            while hasattr(message, 'tool_calls') and message.tool_calls:
                print("\n")  # 为工具调用添加一个分隔行
                # 处理每个工具调用
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    
                    # 查找提供该工具的服务器
                    server_name, tool = self.find_tool_server(tool_name)
                    if not server_name:
                        error_msg = f"Tool {tool_name} is not available from any connected MCP server"
                        print(f"\n{Colors.RED}{error_msg}{Colors.ENDC}")
                        # 添加一个工具响应
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": error_msg
                        })
                        continue
                    
                    tool_args = {}
                    try:
                        # 检查和修复不完整或格式不正确的JSON
                        arguments = tool_call.function.arguments.strip()
                        # 检查是否是空JSON或格式不正确
                        if not arguments or arguments == "null" or arguments == "undefined":
                            arguments = "{}"
                        # 确保它是有效的JSON对象
                        if not (arguments.startswith('{') and arguments.endswith('}')):
                            arguments = "{}"
                        tool_args = json.loads(arguments)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing tool arguments: {tool_call.function.arguments}")
                        print(f"JSON parsing error: {e}")
                        # 尝试修复常见的JSON错误
                        try:
                            # 有时模型会生成不完整的JSON，尝试将其包装为有效的JSON对象
                            if not tool_call.function.arguments.strip().startswith('{'):
                                fixed_args = "{" + tool_call.function.arguments.strip() + "}"
                                tool_args = json.loads(fixed_args)
                                print("Successfully fixed JSON format.")
                            else:
                                # 如果无法修复，使用空对象
                                tool_args = {}
                        except:
                            # 如果所有尝试都失败，使用空对象
                            tool_args = {}
                    
                    print(f"\n{Colors.BOLD}{Colors.BLUE}[Calling tool {server_name}/{tool_name}...]{Colors.ENDC}")
                    start_time = time.time()
                    # 执行工具调用
                    try:
                        # 使用带超时的工具调用，指定服务器
                        result = await self.call_tool_with_timeout(server_name, tool_name, tool_args)
                        elapsed = time.time() - start_time
                        print(f"{Colors.BLUE}[Tool {server_name}/{tool_name} completed in {elapsed:.2f}s]{Colors.ENDC}")
                        final_text.append(f"[Called tool {server_name}/{tool_name}]")
                        
                        # 将工具调用和结果添加到消息历史
                        messages.append({
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": tool_call.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_name,
                                        "arguments": json.dumps(tool_args)
                                    }
                                }
                            ]
                        })
                        
                        # 检查result是否为字典（超时情况下的处理）
                        result_content = result.content if hasattr(result, 'content') else result.get('content', f"Tool {server_name}/{tool_name} completed with unknown result")
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result_content)
                        })
                        
                        # 更新消息历史
                        self.message_history = messages
                    except Exception as e:
                        error_message = f"Error executing tool {server_name}/{tool_name}: {e}"
                        print(error_message)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": error_message
                        })

                # 将工具调用的结果交给 LLM
                print(f"\n{Colors.BOLD}{Colors.BLUE}Processing tool results...{Colors.ENDC}", flush=True)
                
                if stream:
                    stream_response = await self.client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=messages,
                        tools=all_tools,
                        stream=True
                    )
                    
                    collected_content = ""
                    tool_calls = []
                    
                    print(f"\n{Colors.BOLD}{Colors.CYAN}Response:{Colors.ENDC} ", end="", flush=True)
                    async for chunk in stream_response:
                        delta = chunk.choices[0].delta
                        
                        # 处理内容部分
                        if delta.content:
                            print(f"{delta.content}", end="", flush=True)
                            collected_content += delta.content
                        
                        # 处理工具调用部分
                        if delta.tool_calls:
                            for tool_call_delta in delta.tool_calls:
                                # 初始化新的工具调用或更新现有的
                                tool_call_id = tool_call_delta.index
                                while len(tool_calls) <= tool_call_id:
                                    tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                                
                                if tool_call_delta.id:
                                    tool_calls[tool_call_id]["id"] = tool_call_delta.id
                                
                                if tool_call_delta.function:
                                    if tool_call_delta.function.name:
                                        tool_calls[tool_call_id]["function"]["name"] = tool_call_delta.function.name
                                    
                                    if tool_call_delta.function.arguments:
                                        tool_calls[tool_call_id]["function"]["arguments"] += tool_call_delta.function.arguments
                    
                    # 完成流式处理，构建最终消息
                    message = type('obj', (object,), {
                        'content': collected_content,
                        'tool_calls': [type('obj', (object,), {
                            'id': t["id"],
                            'function': type('obj', (object,), {
                                'name': t["function"]["name"],
                                'arguments': t["function"]["arguments"]
                            })
                        }) for t in tool_calls if t["id"]]
                    })
                    
                    if collected_content:
                        final_text.append(collected_content)
                        # 将结果添加到消息历史
                        self.message_history.append({
                            "role": "assistant",
                            "content": collected_content
                        })
                else:
                    # 非流式处理
                    response = await self.client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=messages,
                        tools=all_tools
                    )
                    message = response.choices[0].message
                    if message.content:
                        print(f"\nResponse: {message.content}")
                        final_text.append(message.content)
                    
                    # 将结果添加到消息历史
                    self.message_history.append({
                        "role": "assistant",
                        "content": message.content or ""
                    })
            
            return "\n".join(final_text)
            
        except Exception as e:
            error_message = f"\nError processing query: {e}"
            print(error_message)
            return error_message

    def _display_tool_history(self):
        """显示工具调用历史"""
        if not self.tool_history:
            print(f"{Colors.YELLOW}No tool call history available{Colors.ENDC}")
            return
            
        print(f"\n{Colors.BOLD}{Colors.CYAN}===== Tool Call History ====={Colors.ENDC}")
        for i, record in enumerate(self.tool_history, 1):
            status = f"{Colors.GREEN}✓{Colors.ENDC}" if record["success"] else f"{Colors.RED}✗{Colors.ENDC}"
            server = record.get("server", "unknown")
            print(f"{i}. [{status}] {record['timestamp']} - {server}/{record['tool']}")
            if 'duration' in record:
                print(f"   Duration: {record['duration']:.2f}s")
            if not record["success"] and record["error"]:
                print(f"   {Colors.RED}Error: {record['error']}{Colors.ENDC}")
        print(f"{Colors.CYAN}{'=' * 30}{Colors.ENDC}")
    
    def _display_servers(self):
        """显示连接的MCP服务器和它们的工具"""
        if not self.sessions:
            print(f"{Colors.YELLOW}No MCP servers connected{Colors.ENDC}")
            return
            
        print(f"\n{Colors.BOLD}{Colors.CYAN}===== Connected MCP Servers ====={Colors.ENDC}")
        for server_name, tools in self.server_tools.items():
            print(f"{Colors.BOLD}{server_name}{Colors.ENDC} ({len(tools)} tools)")
            for tool_name in sorted(tools.keys()):
                tool = tools[tool_name]
                print(f"  • {Colors.YELLOW}{tool_name}{Colors.ENDC}: {tool.description[:60]}...")
        print(f"{Colors.CYAN}{'=' * 30}{Colors.ENDC}")
    
    def _trim_message_history(self, max_messages=20):
        """限制消息历史的大小以防止上下文窗口过大"""
        if len(self.message_history) <= max_messages:
            return
        
        # 始终保留系统消息（如果存在）
        if self.message_history and self.message_history[0]["role"] == "system":
            system_message = self.message_history[0]
            # 保留最近的消息，但确保总数不超过max_messages
            self.message_history = [system_message] + self.message_history[-(max_messages-1):]
        else:
            # 如果没有系统消息，只保留最近的消息
            self.message_history = self.message_history[-max_messages:]
    
    def _display_message_history(self):
        """显示当前的消息历史"""
        if not self.message_history:
            print(f"{Colors.YELLOW}No message history available{Colors.ENDC}")
            return
            
        print(f"\n{Colors.BOLD}{Colors.CYAN}===== Message History ({len(self.message_history)} messages) ====={Colors.ENDC}")
        for i, msg in enumerate(self.message_history):
            role = msg["role"]
            # 根据角色使用不同颜色
            if role == "system":
                role_color = f"{Colors.MAGENTA}system{Colors.ENDC}"
            elif role == "user":
                role_color = f"{Colors.GREEN}user{Colors.ENDC}"
            elif role == "assistant":
                role_color = f"{Colors.BLUE}assistant{Colors.ENDC}"
            elif role == "tool":
                role_color = f"{Colors.YELLOW}tool{Colors.ENDC}"
            else:
                role_color = role
                
            # 消息内容截断显示
            content = msg.get("content", "")
            if content and len(content) > 60:
                content = content[:57] + "..."
                
            print(f"{i+1}. [{role_color}] {content}")
        print(f"{Colors.CYAN}{'=' * 30}{Colors.ENDC}")
        print(f"Use '{Colors.BOLD}clear history{Colors.ENDC}' to clear the conversation history.")
    
    def clear_message_history(self):
        """清除消息历史记录，只保留系统消息"""
        if self.message_history and self.message_history[0]["role"] == "system":
            # 保留系统消息
            self.message_history = [self.message_history[0]]
        else:
            self.message_history = []
        print(f"{Colors.GREEN}Message history cleared.{Colors.ENDC}")
    
    async def close(self):
        """清理资源"""
        await self.exit_stack.aclose()
        print("\nMCP Client closed.") 