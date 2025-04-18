import asyncio
import json
import time
import traceback
from typing import Dict, Optional, Any, Tuple, List

from mini_cursor.core.config import Colors, TOOL_CALL_TIMEOUT, VERBOSE_LOGGING

class ToolManager:
    def __init__(self):
        self.tool_history = []  # 工具调用历史
        self.server_tools = {}  # 各服务器提供的工具
        self.sessions = {}      # 服务器会话

    def set_server_tools(self, server_name, tools):
        """设置特定服务器的工具"""
        self.server_tools[server_name] = {tool.name: tool for tool in tools}
        return self.server_tools
    
    def set_session(self, server_name, session):
        """设置特定服务器的会话"""
        self.sessions[server_name] = session
        return self.sessions
    
    def find_tool_server(self, tool_name: str) -> Tuple[Optional[str], Optional[Any]]:
        """查找提供特定工具的服务器"""
        for server_name, tools in self.server_tools.items():
            if tool_name in tools:
                return server_name, tools[tool_name]
        return None, None
    
    def get_all_tools(self) -> List[Dict]:
        """收集所有服务器的工具列表，用于LLM API"""
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
        return all_tools
    
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
    
    def parse_tool_arguments(self, arguments_str: str) -> Dict:
        """解析工具调用参数，并处理可能的错误"""
        try:
            # 检查和修复不完整或格式不正确的JSON
            arguments = arguments_str.strip()
            # 检查是否是空JSON或格式不正确
            if not arguments or arguments == "null" or arguments == "undefined":
                arguments = "{}"
            # 确保它是有效的JSON对象
            if not (arguments.startswith('{') and arguments.endswith('}')):
                arguments = "{}"
            return json.loads(arguments)
        except json.JSONDecodeError as e:
            print(f"Error parsing tool arguments: {arguments_str}")
            print(f"JSON parsing error: {e}")
            # 尝试修复常见的JSON错误
            try:
                # 有时模型会生成不完整的JSON，尝试将其包装为有效的JSON对象
                if not arguments_str.strip().startswith('{'):
                    fixed_args = "{" + arguments_str.strip() + "}"
                    tool_args = json.loads(fixed_args)
                    print("Successfully fixed JSON format.")
                    return tool_args
                else:
                    # 如果无法修复，使用空对象
                    return {}
            except:
                # 如果所有尝试都失败，使用空对象
                return {} 