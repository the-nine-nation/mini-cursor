import asyncio
import json
import time
import traceback
from typing import Dict, Optional, Any, Tuple, List, Set

from mini_cursor.core.config import Colors, TOOL_CALL_TIMEOUT, VERBOSE_LOGGING

class ToolManager:
    def __init__(self):
        self.tool_history = []  # 工具调用历史
        self.server_tools = {}  # 各服务器提供的工具
        self.sessions = {}      # 服务器会话
        self.cached_all_tools = None  # 缓存所有服务器的工具
        self.disabled_tools = set()  # 禁用的工具名称集合
        self.tool_enablement_mode = "all"  # 默认模式: "all"启用所有, "selective"选择性启用
        self.tool_server_cache = {}  # 工具与服务器映射的缓存

    def set_server_tools(self, server_name, tools):
        """设置特定服务器的工具"""
        self.server_tools[server_name] = {tool.name: tool for tool in tools}
        # 清空工具缓存，因为工具列表已变化
        self.cached_all_tools = None
        return self.server_tools
    
    def set_session(self, server_name, session):
        """设置特定服务器的会话"""
        self.sessions[server_name] = session
        return self.sessions
    
    def find_tool_server(self, tool_name: str) -> Tuple[Optional[str], Optional[Any]]:
        """查找提供特定工具的服务器，使用缓存提高性能"""
        # 首先检查缓存
        if tool_name in self.tool_server_cache:
            server_name = self.tool_server_cache[tool_name]
            return server_name, self.server_tools[server_name].get(tool_name)
        
        # 如果缓存中没有，搜索所有服务器
        for server_name, tools in self.server_tools.items():
            if tool_name in tools:
                # 找到后添加到缓存
                self.tool_server_cache[tool_name] = server_name
                return server_name, tools[tool_name]
        
        return None, None
    
    def get_all_tools(self) -> List[Dict]:
        """收集所有服务器的工具列表，用于LLM API，并使用缓存提高性能"""
        # 如果缓存可用，直接返回缓存
        if self.cached_all_tools is not None:
            return self.cached_all_tools
            
        # 重建工具列表
        self.refresh_tools_cache()
        return self.cached_all_tools
    
    def refresh_tools_cache(self) -> List[Dict]:
        """强制刷新工具缓存，并返回最新的工具列表"""
        all_tools = []
        tool_names = set()
        
        # 先检测重复工具
        duplicate_tools = set()
        for server_name, tools_dict in self.server_tools.items():
            for tool_name in tools_dict.keys():
                if tool_name in tool_names:
                    duplicate_tools.add(tool_name)
                tool_names.add(tool_name)
        
        # 如果有重复工具，打印警告
        for tool_name in duplicate_tools:
            print(f"{Colors.YELLOW}Warning: Tool '{tool_name}' is provided by multiple servers{Colors.ENDC}")
        
        # 构建工具列表，根据启用状态过滤
        for server_name, tools_dict in self.server_tools.items():
            for tool_name, tool in tools_dict.items():
                # 检查工具是否应该被包含
                if self.is_tool_enabled(tool_name):
                    all_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": f"[{server_name}] {tool.description}",
                            "parameters": tool.inputSchema
                        }
                    })
        
        # 更新缓存
        self.cached_all_tools = all_tools
        return all_tools
    
    def is_tool_enabled(self, tool_name: str) -> bool:
        """检查工具是否启用"""
        if self.tool_enablement_mode == "all":
            # 在"all"模式下，未被明确禁用的工具都是启用的
            return tool_name not in self.disabled_tools
        else:  # "selective"模式
            # 在"selective"模式下，被明确禁用的工具是禁用的
            return tool_name not in self.disabled_tools
    
    def disable_tool(self, tool_name: str) -> bool:
        """禁用特定工具"""
        # 验证工具是否存在
        found = False
        for server_tools in self.server_tools.values():
            if tool_name in server_tools:
                found = True
                break
        
        if not found:
            print(f"{Colors.YELLOW}Warning: Cannot disable unknown tool '{tool_name}'{Colors.ENDC}")
            return False
        
        # 添加到禁用列表
        self.disabled_tools.add(tool_name)
        # 清除缓存，强制重建
        self.cached_all_tools = None
        print(f"{Colors.GREEN}Tool '{tool_name}' has been disabled{Colors.ENDC}")
        return True
    
    def enable_tool(self, tool_name: str) -> bool:
        """启用特定工具（从禁用列表中移除）"""
        # 验证工具是否存在
        found = False
        for server_tools in self.server_tools.values():
            if tool_name in server_tools:
                found = True
                break
        
        if not found:
            print(f"{Colors.YELLOW}Warning: Cannot enable unknown tool '{tool_name}'{Colors.ENDC}")
            return False
        
        # 从禁用列表中移除
        if tool_name in self.disabled_tools:
            self.disabled_tools.remove(tool_name)
            # 清除缓存，强制重建
            self.cached_all_tools = None
            print(f"{Colors.GREEN}Tool '{tool_name}' has been enabled{Colors.ENDC}")
            return True
        
        print(f"{Colors.CYAN}Tool '{tool_name}' is already enabled{Colors.ENDC}")
        return True
    
    def set_tool_enablement_mode(self, mode: str) -> bool:
        """设置工具启用模式: 'all' (默认所有工具启用) 或 'selective' (选择性启用)"""
        if mode not in ["all", "selective"]:
            print(f"{Colors.RED}Invalid mode '{mode}'. Must be 'all' or 'selective'{Colors.ENDC}")
            return False
        
        self.tool_enablement_mode = mode
        # 清除缓存，强制重建
        self.cached_all_tools = None
        print(f"{Colors.GREEN}Tool enablement mode set to '{mode}'{Colors.ENDC}")
        return True
    
    def get_all_available_tools(self) -> Dict[str, Dict[str, str]]:
        """获取所有可用的工具及其服务器和启用状态"""
        all_tools = {}
        for server_name, tools_dict in self.server_tools.items():
            for tool_name, tool in tools_dict.items():
                all_tools[tool_name] = {
                    "server": server_name,
                    "description": tool.description,
                    "enabled": self.is_tool_enabled(tool_name)
                }
        return all_tools
    
    def disable_all_tools(self) -> None:
        """禁用所有工具"""
        for server_tools in self.server_tools.values():
            for tool_name in server_tools.keys():
                self.disabled_tools.add(tool_name)
        # 清除缓存，强制重建
        self.cached_all_tools = None
        print(f"{Colors.GREEN}All tools have been disabled{Colors.ENDC}")
    
    def enable_all_tools(self) -> None:
        """启用所有工具（清空禁用列表）"""
        self.disabled_tools.clear()
        # 清除缓存，强制重建
        self.cached_all_tools = None
        print(f"{Colors.GREEN}All tools have been enabled{Colors.ENDC}")
    
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
        """解析工具调用参数，简化处理流程提高性能"""
        try:
            # 尝试直接解析
            return json.loads(arguments_str)
        except json.JSONDecodeError:
            # 如果解析失败，使用简单的修复方法
            try:
                # 确保字符串是JSON对象格式
                arguments = arguments_str.strip()
                if not arguments or arguments == "null" or arguments == "undefined":
                    return {}
                if not (arguments.startswith('{') and arguments.endswith('}')):
                    arguments = "{" + arguments + "}"
                return json.loads(arguments)
            except:
                # 如果所有尝试都失败，返回空对象
                return {} 