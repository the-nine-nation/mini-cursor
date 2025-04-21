import json
from openai import AsyncOpenAI
import os

from mini_cursor.core.config import Colors, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, VERBOSE_LOGGING
from mini_cursor.core.tool_manager import ToolManager
from mini_cursor.core.message_manager import MessageManager
from mini_cursor.core.server_manager import ServerManager
from mini_cursor.core.display_utils import display_tool_history, display_servers, display_message_history


class MCPClient:
    def __init__(self):
        self.server_manager = ServerManager()
        self.tool_manager = ToolManager()
        self.message_manager = MessageManager()
        self.init_openai_client()
    
    def init_openai_client(self):
        """初始化OpenAI客户端，使用当前配置的API密钥和基础URL"""
        self.client = AsyncOpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
    
    def update_config(self):
        """更新客户端配置，从环境变量重新加载设置并重新初始化客户端"""
        from mini_cursor.core.config import init_config, OPENAI_MODEL, OPENAI_BASE_URL
        config = init_config()
        print(f"\n{Colors.GREEN}重新加载配置成功{Colors.ENDC}")
        print(f"{Colors.CYAN}OpenAI API Base URL: {config['OPENAI_BASE_URL']}{Colors.ENDC}")
        print(f"{Colors.CYAN}Using model: {config['OPENAI_MODEL']}{Colors.ENDC}")
        
        # 重新初始化OpenAI客户端
        self.init_openai_client()
    
    async def connect_to_servers(self):
        """连接到配置的所有MCP服务器"""
        await self.server_manager.connect_to_servers(self.tool_manager)
    
    async def process_query(self, query: str, system_prompt: str, stream=True) -> str:
        """使用 LLM 和 多个 MCP 服务器提供的工具处理查询"""
        # 添加新的用户查询到消息历史
        messages = self.message_manager.add_user_message(query, system_prompt)
        
        # 使用工具管理器获取缓存的工具列表（只有在必要时才会重建）
        all_tools = self.tool_manager.get_all_tools()

        # 检查当前模型是否支持显示思考过程（如deepseek-r1）
        from mini_cursor.core.config import OPENAI_MODEL

        final_text = []
        
        try:
            # 初始化 LLM API 调用，使用流式响应
            if stream:
                # 确保使用最新的模型配置
                from mini_cursor.core.config import OPENAI_MODEL
                
                stream_response = await self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    tools=all_tools,
                    stream=True
                )
                
                # 处理流式响应
                collected_content = ""
                collected_reasoning = ""
                tool_calls = []
                
                print(f"\n{Colors.BOLD}{Colors.CYAN}Response:{Colors.ENDC} ", end="", flush=True)
                async for chunk in stream_response:
                    delta = chunk.choices[0].delta
                    
                    # 处理内容部分
                    if delta.content:
                        print(f"{delta.content}", end="", flush=True)
                        collected_content += delta.content
                    
                    # 处理 reasoning_content（思考过程，deepseek-r1等模型会返回）
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
                                tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                            
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
                
                message = type('obj', (object,), {
                    'content': collected_content,
                    'reasoning_content': collected_reasoning if collected_reasoning else None,
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
                    self.message_manager.add_assistant_message(collected_content)
            else:
                # 非流式处理
                # 确保使用最新的模型配置
                from mini_cursor.core.config import OPENAI_MODEL
                    
                response = await self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    tools=all_tools
                )
                message = response.choices[0].message
                
                # 处理content内容
                if message.content:
                    print(f"\nResponse: {message.content}")
                    final_text.append(message.content)
                    # 将结果添加到消息历史
                    self.message_manager.add_assistant_message(message.content)
                
                # 处理思考过程（不管有没有content，都处理reasoning_content）  
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    print(f"\n{Colors.BOLD}{Colors.YELLOW}[思考过程]{Colors.ENDC} {Colors.YELLOW}{message.reasoning_content}{Colors.ENDC}", flush=True)
            
            # 处理工具调用
            while hasattr(message, 'tool_calls') and message.tool_calls:
                print("\n")  # 为工具调用添加一个分隔行
                # 处理每个工具调用
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    
                    # 查找提供该工具的服务器
                    server_name, tool = self.tool_manager.find_tool_server(tool_name)
                    if not server_name:
                        error_msg = f"Tool {tool_name} is not available from any connected MCP server"
                        print(f"\n{Colors.RED}{error_msg}{Colors.ENDC}")
                        # 添加一个工具响应
                        self.message_manager.add_tool_result(tool_call.id, error_msg)
                        continue
                    
                    # 解析工具参数
                    tool_args = self.tool_manager.parse_tool_arguments(tool_call.function.arguments)
                    
                    print(f"\n{Colors.BOLD}{Colors.BLUE}[Calling tool {server_name}/{tool_name}...]{Colors.ENDC}")
                    # 执行工具调用
                    try:
                        # 使用带超时的工具调用，指定服务器
                        result = await self.tool_manager.call_tool_with_timeout(server_name, tool_name, tool_args)
                        print(f"{Colors.BLUE}[Tool {server_name}/{tool_name} completed]{Colors.ENDC}")
                        final_text.append(f"[Called tool {server_name}/{tool_name}]")
                        
                        # 将工具调用和结果添加到消息历史
                        self.message_manager.add_tool_call(tool_call, tool_name, json.dumps(tool_args))
                        
                        # 检查result是否为字典（超时情况下的处理）
                        result_content = result.content if hasattr(result, 'content') else result.get('content', f"Tool {server_name}/{tool_name} completed with unknown result")
                        
                        self.message_manager.add_tool_result(tool_call.id, result_content)
                    except Exception as e:
                        error_message = f"Error executing tool {server_name}/{tool_name}: {e}"
                        print(error_message)
                        self.message_manager.add_tool_result(tool_call.id, error_message)

                # 将工具调用的结果交给 LLM
                print(f"\n{Colors.BOLD}{Colors.BLUE}Processing tool results...{Colors.ENDC}", flush=True)
                messages = self.message_manager.get_messages()
                
                if stream:
                    # 确保使用最新的模型配置
                    from mini_cursor.core.config import OPENAI_MODEL
                    
                    stream_response = await self.client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=messages,
                        tools=all_tools,
                        stream=True
                    )
                    
                    collected_content = ""
                    collected_reasoning = ""
                    tool_calls = []
                    
                    print(f"\n{Colors.BOLD}{Colors.CYAN}Response:{Colors.ENDC} ", end="", flush=True)
                    async for chunk in stream_response:
                        delta = chunk.choices[0].delta
                        
                        # 处理内容部分
                        if delta.content:
                            print(f"{delta.content}", end="", flush=True)
                            collected_content += delta.content
                        
                        # 处理 reasoning_content（思考过程，deepseek-r1等模型会返回）
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
                                    tool_calls.append({"id": "", "function": {"name": "", "arguments": ""}})
                                
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
                    
                    message = type('obj', (object,), {
                        'content': collected_content,
                        'reasoning_content': collected_reasoning if collected_reasoning else None,
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
                        self.message_manager.add_assistant_message(collected_content)
                else:
                    # 非流式处理
                    # 确保使用最新的模型配置
                    from mini_cursor.core.config import OPENAI_MODEL
                    
                    response = await self.client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=messages,
                        tools=all_tools
                    )
                    message = response.choices[0].message
                    
                    # 处理content内容
                    if message.content:
                        print(f"\nResponse: {message.content}")
                        final_text.append(message.content)
                        # 将结果添加到消息历史
                        self.message_manager.add_assistant_message(message.content)
                    
                    # 处理思考过程（不管有没有content，都处理reasoning_content）  
                    if hasattr(message, 'reasoning_content') and message.reasoning_content:
                        print(f"\n{Colors.BOLD}{Colors.YELLOW}[思考过程]{Colors.ENDC} {Colors.YELLOW}{message.reasoning_content}{Colors.ENDC}", flush=True)
            
            return "\n".join(final_text)
            
        except Exception as e:
            error_message = f"\nError processing query: {e}"
            print(error_message)
            return error_message

    def display_tool_history(self):
        """显示工具调用历史"""
        display_tool_history(self.tool_manager.tool_history)
    
    def display_servers(self):
        """显示连接的MCP服务器和它们的工具"""
        display_servers(self.tool_manager.server_tools, self.tool_manager)
    
    def display_message_history(self):
        """显示当前的消息历史"""
        display_message_history(self.message_manager.message_history)
    
    def clear_message_history(self):
        """清除消息历史记录，只保留系统消息"""
        self.message_manager.clear_message_history()
    
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