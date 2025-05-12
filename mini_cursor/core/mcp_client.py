import json
from openai import AsyncOpenAI
import os
import asyncio
import traceback

from mini_cursor.core.config import Colors,init_config, VERBOSE_LOGGING, TOOL_CALL_TIMEOUT
from mini_cursor.core.tool_manager import ToolManager
from mini_cursor.core.message_manager import MessageManager
from mini_cursor.core.server_manager import ServerManager
from mini_cursor.core.tool_history_manager import ToolHistoryManager
from mini_cursor.core.display_utils import display_tool_history, display_servers, display_message_history
from mini_cursor.core.database import get_db_manager


class MCPClient:
    def __init__(self):
        self.server_manager = ServerManager()
        self.tool_manager = ToolManager()
        self.message_manager = MessageManager()
        self.tool_history_manager = ToolHistoryManager()  # 添加工具历史管理器
        self.update_listener = None  # 添加更新监听器字段
        self.tool_history = []  # 初始化工具调用历史
        
        # 初始化数据库管理器
        self.db_manager = get_db_manager()
        self.current_conversation_id = None
        self.OPENAI_MODEL=""
        conf=init_config()
        OPENAI_API_KEY=conf["OPENAI_API_KEY"]
        OPENAI_BASE_URL=conf["OPENAI_BASE_URL"]
        self.client = AsyncOpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        
        
        
        
    
    async def _create_chat_completion(self, messages, tools=None, stream=True, temperature=0.3):
        """封装OpenAI聊天完成API调用的通用方法
        
        Args:
            messages: 对话消息列表
            tools: 可用工具列表，默认为None
            stream: 是否使用流式响应，默认为True
            temperature: 温度参数，控制随机性，默认为0.3
            
        Returns:
            OpenAI API的响应对象
        """
        conf=init_config()
        self.OPENAI_MODEL=conf["OPENAI_MODEL"]
        # 构建基本参数
        params = {
            "model": self.OPENAI_MODEL,
            "messages": messages,
            "temperature": temperature,
        }
        
        # 如果提供了工具，添加到参数中
        if tools:
            params["tools"] = tools
            
        # 设置是否使用流式响应
        params["stream"] = stream
        
        # 调用API并返回结果
        return await self.client.chat.completions.create(**params)
        
    
    async def connect_to_servers(self):
        """连接到配置的所有MCP服务器"""
        await self.server_manager.connect_to_servers(self.tool_manager)
        
    
    
    async def process_query(self, query: str, system_prompt: str, stream=True, conversation_history=None) -> str:
        """使用 LLM 和 多个 MCP 服务器提供的工具处理查询"""
        # 创建一个临时conversation_id变量，但先不立即创建数据库记录
        is_existing_conversation = False
        
        # 如果存在当前对话ID，标记为已有对话
        if self.current_conversation_id and self.message_manager.message_history:
            is_existing_conversation = True
        
        # 如果提供了对话历史记录，则恢复消息历史
        if conversation_history:
            self.message_manager.restore_history(conversation_history)
        
        # 添加新的用户查询到消息历史
        messages = self.message_manager.add_user_message(query, system_prompt)
        
        # 使用工具管理器获取缓存的工具列表（只有在必要时才会重建）
        all_tools = self.tool_manager.get_all_tools()

        # 检查当前模型是否支持显示思考过程（如deepseek-r1）
        from mini_cursor.core.config import OPENAI_MODEL

        final_text = []
        
        # 收集所有对话内容，稍后再一次性存入数据库
        collected_assistant_response = ""
        collected_tool_calls = []
        
        try:
            # 初始化 LLM API 调用
            
            # 处理工具调用循环
            while True:
                # 获取大模型响应

                stream_response = await self._create_chat_completion(
                    messages=messages,
                    tools=all_tools,
                    stream=True,
                    temperature=0.3
                )
                
                # 初始化收集变量
                collected_content = ""
                collected_reasoning = ""
                tool_calls = []
                
                # 处理流式响应
                print(f"\n{Colors.BOLD}{Colors.CYAN}Response:{Colors.ENDC} ", end="", flush=True)
                async for chunk in stream_response:
                    delta = chunk.choices[0].delta
                    
                    # 处理内容部分
                    if delta.content:
                        print(f"{delta.content}", end="", flush=True)
                        collected_content += delta.content
                        # 通知内容更新
                        self.notify_update('assistant_message', delta.content)
                    
                    # 处理 reasoning_content（思考过程）
                    reasoning_chunk = None
                    if hasattr(delta, 'message') and hasattr(delta.message, 'reasoning_content'):
                        reasoning_chunk = delta.message.reasoning_content
                    elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_chunk = delta.reasoning_content
                        
                    # 如果有思考内容，流式显示
                    if reasoning_chunk:
                        # 第一次收到思考内容时显示标题
                        if not collected_reasoning:
                            print(f"\n{Colors.BOLD}{Colors.YELLOW}[思考过程]{Colors.ENDC} ", end="", flush=True)
                        # 显示增量思考内容
                        print(f"{Colors.YELLOW}{reasoning_chunk}{Colors.ENDC}", end="", flush=True)
                        # 累加到收集的思考内容中
                        collected_reasoning += reasoning_chunk
                        # 通知思考过程更新
                        self.notify_update('thinking', reasoning_chunk)
                    
                    # 用于诊断的代码 - 仅在VERBOSE_LOGGING为True时才会执行
                    if VERBOSE_LOGGING and chunk.choices[0] and os.environ.get("DEBUG_CHUNKS", "0") == "1":
                        try:
                            # 尝试将delta转换为字典来查看其结构
                            delta_dict = {}
                            if hasattr(chunk.choices[0], 'model_dump'):
                                delta_dict = json.loads(json.dumps(chunk.choices[0].model_dump()))
                            elif hasattr(chunk.choices[0], 'to_dict'): 
                                delta_dict = chunk.choices[0].to_dict()
                            
                            if delta_dict and 'delta' in delta_dict and delta_dict['delta']:
                                print(f"\n{Colors.DIM}[DEBUG] Chunk structure: {json.dumps(delta_dict)}{Colors.ENDC}", flush=True)
                        except Exception as e:
                            print(f"\n{Colors.DIM}[DEBUG] Failed to dump chunk: {e}{Colors.ENDC}", flush=True)
                    
                    # 处理工具调用部分
                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            # 初始化新的工具调用或更新现有的
                            tool_call_id = tool_call_delta.index
                            while len(tool_calls) <= tool_call_id:
                                tool_calls.append({"id": "","type":"function", "function": {"name": "", "arguments": ""}})
                            
                            if tool_call_delta.id:
                                tool_calls[tool_call_id]["id"] = tool_call_delta.id
                            
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    tool_calls[tool_call_id]["function"]["name"] = tool_call_delta.function.name
                                
                                if tool_call_delta.function.arguments:
                                    tool_calls[tool_call_id]["function"]["arguments"] += tool_call_delta.function.arguments
                    
                    # 完成流式处理，构建最终消息
                    collected_reasoning_content = ""
                    
                    # 用于收集整个流式过程中可能的reasoning_content（针对可能的完整回传情况）
                    for chunk in stream_response.__dict__.get('_response_data', {}).get('choices', []):
                        if chunk.get('delta', {}).get('reasoning_content'):
                            collected_reasoning_content += chunk['delta']['reasoning_content']
                    
                    # 如果前面流式过程中没有收集到reasoning_content但最终数据里有，则显示
                    if not collected_reasoning and collected_reasoning_content:
                        print(f"\n{Colors.BOLD}{Colors.YELLOW}[思考过程]{Colors.ENDC} {Colors.YELLOW}{collected_reasoning_content}{Colors.ENDC}", flush=True)
                        collected_reasoning = collected_reasoning_content
                    
                # 构建消息对象
                message = {
                    'role': 'assistant',
                    'content': collected_content.strip(),
                    'reasoning_content': collected_reasoning if collected_reasoning else None,
                    'tool_calls': [t for t in tool_calls if t["id"]]
                }
                
                # 更新历史和显示结果
                if collected_content or ('tool_calls' in message and message['tool_calls']):
                    if collected_content:
                        final_text.append(collected_content)
                    
                    # 同时添加内容和工具调用到消息历史
                    self.message_manager.add_assistant_message(
                        llm_response=message
                    )
                    
                    if collected_content:
                        collected_assistant_response = collected_content
                
                # 检查是否有工具调用需要处理
                if 'tool_calls' not in message or not message['tool_calls']:
                    messages = self.message_manager.get_messages()
                    # 没有工具调用，结束循环
                    break
                
                print("\n")  # 为工具调用添加一个分隔行
                # 创建一个集合来存储已处理的工具调用ID，防止重复添加
                processed_tool_call_ids = set()
                
                # 处理每个工具调用
                for tool_call in message['tool_calls']:
                    # 跳过已处理的工具调用ID
                    if tool_call["id"] in processed_tool_call_ids:
                        continue
                    
                    # 记录这个工具调用ID已被处理
                    processed_tool_call_ids.add(tool_call["id"])
                    
                    tool_name = tool_call["function"]["name"]
                    
                    # 查找提供该工具的服务器
                    server_name, tool = self.tool_manager.find_tool_server(tool_name)
                    if not server_name:
                        error_msg = f"Tool {tool_name} is not available from any connected MCP server"
                        print(f"\n{Colors.RED}{error_msg}{Colors.ENDC}")
                        # 添加一个工具响应
                        self.message_manager.add_tool_result(tool_call["id"], error_msg)
                        # 通知工具调用错误
                        self.notify_update('tool_error', {'name': tool_name, 'error': error_msg})
                        
                        # 收集工具调用错误
                        collected_tool_calls.append({
                            "tool_name": tool_name,
                            "tool_args": "{}",
                            "tool_result": f"Error: {error_msg}",
                            "is_error": True
                        })
                        continue
                    
                    # 解析工具参数
                    tool_args = self.tool_manager.parse_tool_arguments(tool_call["function"]["arguments"])
                    
                    # 尝试执行工具
                    try:
                        # 记录工具调用到历史管理器
                        call_id = self.tool_history_manager.record_tool_call(tool_name, tool_args)
                        
                        # 通知工具调用开始
                        self.notify_update('tool_call', {'id': call_id, 'name': tool_name, 'arguments': tool_args})
                        
                        # 打印工具调用信息
                        print(f"\n{Colors.GREEN}Calling tool:{Colors.ENDC} {tool_name}")
                        
                        # 执行工具调用，增加额外的超时保护
                        try:
                            # 使用asyncio.wait_for添加额外的超时保护
                            result = await self.server_manager.execute_tool(server_name, tool_name, tool_args)
                        except Exception as ex:
                            error_msg = f"Tool call timeout: {tool_name} exceeded {TOOL_CALL_TIMEOUT} seconds"
                            print(f"\n{Colors.RED}{error_msg}{Colors.ENDC}")
                            
                            # 记录工具调用结果
                            self.tool_history_manager.record_tool_result(call_id, None, error_msg)
                            
                            # 添加超时结果到历史记录
                            self.message_manager.add_tool_result(tool_call["id"], f"Error: {error_msg}")
                            
                            # 收集工具调用错误
                            collected_tool_calls.append({
                                "tool_name": tool_name,
                                "tool_args": json.dumps(tool_args),
                                "tool_result": f"Error: {error_msg}",
                                "is_error": True
                            })
                            
                            # 通知工具调用超时
                            self.notify_update('tool_error', {'id': call_id, 'name': tool_name, 'error': error_msg})
                            continue
                        
                        # 记录工具调用结果
                        self.tool_history_manager.record_tool_result(call_id, result)
                        
                        # 添加工具结果到历史记录
                        self.message_manager.add_tool_result(tool_call["id"], result)
                        
                        # 将工具调用和结果添加到历史
                        self.tool_history.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": str(result)
                        })
                        
                        # 收集工具调用结果
                        collected_tool_calls.append({
                            "tool_name": tool_name,
                            "tool_args": json.dumps(tool_args),
                            "tool_result": str(result),
                            "is_error": False
                        })
                        
                        # 增加延迟以防止过快执行工具调用
                        await asyncio.sleep(0.1)
                        
                        # 将结果发送给客户端
                        tool_result_data = {
                            'id': call_id,
                            'name': tool_name,
                            'result': result
                        }
                        
                        # 打印工具结果
                        print(f"{Colors.GREEN}Tool result:{Colors.ENDC} {result}")
                        # 通知工具调用结果
                        self.notify_update('tool_result', tool_result_data)
                    except Exception as e:
                        error_msg = f"Error calling tool {tool_name}: {str(e)}"
                        print(f"\n{Colors.RED}{error_msg}{Colors.ENDC}")
                        if VERBOSE_LOGGING:
                            traceback.print_exc()  # 打印详细的错误栈
                        
                        # 如果有记录工具调用，记录错误结果
                        if 'call_id' in locals():
                            self.tool_history_manager.record_tool_result(call_id, None, error_msg)
                        
                        # 添加错误结果到历史记录
                        self.message_manager.add_tool_result(tool_call["id"], f"Error: {str(e)}")
                        
                        # 收集工具调用错误
                        collected_tool_calls.append({
                            "tool_name": tool_name,
                            "tool_args": json.dumps(tool_args) if 'tool_args' in locals() else "{}",
                            "tool_result": f"Error: {error_msg}",
                            "is_error": True
                        })
                        
                        # 通知工具调用错误
                        self.notify_update('tool_error', {
                            'id': call_id if 'call_id' in locals() else None,
                            'name': tool_name,
                            'error': error_msg
                        })
                
                # 获取最新的响应消息
                messages = self.message_manager.get_messages()
                
                # 提示再次询问AI
                print("\n\n再次询问AI以获取回复...\n")
            
            # 保存会话到数据库
            if len(self.message_manager.get_messages()) > 2:  
                try:
                    # If it's a new conversation, create the record
                    if not is_existing_conversation:
                        # Create new conversation in DB
                        self.current_conversation_id = self.db_manager.create_conversation()
                        print(f"\n{Colors.YELLOW}Created new conversation with ID: {self.current_conversation_id}{Colors.ENDC}")
                        # Set system prompt if provided
                        if system_prompt:
                            self.db_manager.set_system_prompt(self.current_conversation_id, system_prompt)
                    
                    # Ensure we have a conversation ID before proceeding
                    if not self.current_conversation_id:
                         print(f"{Colors.RED}Error: Cannot save messages, current_conversation_id is not set.{Colors.ENDC}")
                         # Potentially raise an error or handle this case appropriately
                         return "\n".join(final_text) if final_text else "" # Exit early if no ID

                    # Add user query to DB
                    self.db_manager.add_message_to_conversation(self.current_conversation_id, "user", query)
                    
                    # Add assistant response to DB if it exists
                    if collected_assistant_response:
                       self.db_manager.add_message_to_conversation(self.current_conversation_id, "assistant", collected_assistant_response)
                    
                    # Add all tool calls to DB
                    for tool_call in collected_tool_calls:
                        self.db_manager.add_tool_call_to_conversation(
                            self.current_conversation_id,
                            tool_call["tool_name"],
                            tool_call["tool_args"],
                            tool_call["tool_result"],
                            tool_call.get("is_error", False) # Pass is_error if available
                        )
                    
                    # Log successful storage
                    print(f"\n{Colors.GREEN}Conversation saved/updated successfully in DB, ID: {self.current_conversation_id}{Colors.ENDC}")
                    
                except Exception as e:
                    print(f"{Colors.RED}Error saving conversation to database: {e}{Colors.ENDC}")
                    if VERBOSE_LOGGING:
                        traceback.print_exc()
            else:
                 # Log that the conversation was not saved due to insufficient turns
                 print(f"\n{Colors.YELLOW}Conversation not saved: Insufficient turns (<= 1 turn completed).{Colors.ENDC}")
                 pass # No explicit action needed here for now based on the logic structure
            
            # 尝试创建对话摘要
            if self.current_conversation_id:
                try:
                    # 尝试获取前两轮对话作为摘要
                    conversation = self.db_manager.get_conversation(self.current_conversation_id)
                    if conversation and 'content' in conversation:
                        messages = conversation['content'].get('messages', [])
                        if len(messages) >= 2:
                            # 简单摘要：截取用户第一条消息前50个字符
                            for msg in messages:
                                if msg.get('sender') == 'user':
                                    summary = msg.get('content', '')[:50]
                                    if summary:
                                        self.db_manager.update_conversation_summary(
                                            self.current_conversation_id,
                                            summary + ('...' if len(msg.get('content', '')) > 50 else '')
                                        )
                                    break
                except Exception as e:
                    if VERBOSE_LOGGING:
                        print(f"{Colors.YELLOW}Failed to create conversation summary: {e}{Colors.ENDC}")
            
            return "\n".join(final_text) if final_text else ""
            
        except Exception as e:
            error_message = f"\nError processing query: {e}"
            print(error_message)
            # 添加错误跟踪
            if VERBOSE_LOGGING:
                traceback.print_exc()
            return error_message

    def display_tool_history(self):
        """显示工具调用历史"""
        display_tool_history(self.tool_history)
    
    def display_servers(self):
        """显示连接的MCP服务器和它们的工具"""
        display_servers(self.tool_manager.server_tools, self.tool_manager)
    
    def display_message_history(self):
        """显示当前的消息历史"""
        display_message_history(self.message_manager.message_history)
    
    def clear_message_history(self):
        """清除消息历史记录，只保留系统消息"""
        self.message_manager.clear_message_history()
        
        # 创建新的对话
        self.current_conversation_id = None
    
    def enable_tool(self, tool_name):
        """启用特定工具"""
        return self.tool_manager.enable_tool(tool_name)
    
    def disable_tool(self, tool_name):
        """禁用特定工具"""
        return self.tool_manager.disable_tool(tool_name)
    
    def set_tool_enablement_mode(self, mode):
        """设置工具启用模式"""
        return self.tool_manager.set_tool_enablement_mode(mode)
    
    def enable_all_tools(self):
        """启用所有工具"""
        self.tool_manager.enable_all_tools()
    
    def disable_all_tools(self):
        """禁用所有工具"""
        self.tool_manager.disable_all_tools()
    
    def get_all_available_tools(self):
        """获取所有可用工具及其状态"""
        return self.tool_manager.get_all_available_tools()
    
    async def close(self):
        """清理资源"""
        print("\n正在优雅地关闭所有连接和资源...")
        
        try:
            # 1. 首先关闭服务器管理器，这会关闭所有MCP服务器连接
            await self.server_manager.close()
            
            # 2. 清理工具管理器中的任何资源
            if hasattr(self.tool_manager, 'close') and callable(self.tool_manager.close):
                await self.tool_manager.close()
            
            # 3. 关闭OpenAI客户端（如果需要）
            if hasattr(self.client, 'close') and callable(self.client.close):
                await self.client.close()
            
            print("所有资源已成功关闭。")
            
        except Exception as e:
            print(f"关闭时出错: {e}")
            # 即使出错，也不抛出异常，让程序能够退出 

    def set_update_listener(self, listener):
        """设置更新监听器回调函数"""
        self.update_listener = listener
    
    def remove_update_listener(self):
        """移除更新监听器"""
        self.update_listener = None
    
    def notify_update(self, update_type, data=None):
        """通知更新"""
        try:
            if self.update_listener:
                # 确保数据格式正确，避免失败
                if update_type == 'tool_call' and isinstance(data, dict):
                    # 确保tool_call数据包含必要字段
                    if 'name' not in data:
                        data['name'] = 'unknown_tool'
                    if 'arguments' not in data:
                        data['arguments'] = {}
                elif update_type == 'tool_result' and isinstance(data, dict):
                    # 确保tool_result数据包含必要字段
                    if 'name' not in data:
                        data['name'] = 'unknown_tool'
                    if 'result' not in data:
                        data['result'] = 'No result'
                    
                    # 重命名'result'字段为'output'，以与前端SSE处理保持一致
                    if 'result' in data and 'output' not in data:
                        data['output'] = data['result']
                
                # 调用更新监听器
                self.update_listener(update_type, data)
        except Exception as e:
            print(f"Error in notify_update: {e}")
            # 尝试发送错误通知，但避免递归错误
            try:
                if self.update_listener and update_type != 'error':
                    self.update_listener('error', {"content": f"通知更新时出错: {str(e)}"})
            except:
                pass 