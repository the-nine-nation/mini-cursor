from mini_cursor.core.config import Colors

class MessageManager:
    def __init__(self):
        self.message_history = []
        
    def add_user_message(self, query, system_prompt=None):
        """添加用户消息，可选择更新系统提示"""
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
                if system_prompt:
                    self.message_history[0] = system_message
                self.message_history.append(user_message)
            else:
                # 如果没有系统消息，则添加一个
                self.message_history = [system_message] + self.message_history + [user_message]
        
        # 裁剪消息历史以控制上下文窗口大小
        self.trim_message_history()
        
        return self.message_history
    
    def add_assistant_message(self, content):
        """添加助手消息到历史记录"""
        if content:
            self.message_history.append({
                "role": "assistant",
                "content": content
            })
        return self.message_history
    
    def add_tool_call(self, tool_call, tool_name, tool_args):
        """添加工具调用到历史记录"""
        self.message_history.append({
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": tool_args
                    }
                }
            ]
        })
        return self.message_history
    
    def add_tool_result(self, tool_call_id, result_content):
        """添加工具调用结果到历史记录"""
        self.message_history.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": str(result_content)
        })
        return self.message_history
    
    def trim_message_history(self, max_messages=20):
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
        
        return self.message_history
    
    def clear_message_history(self):
        """清除消息历史记录，只保留系统消息"""
        if self.message_history and self.message_history[0]["role"] == "system":
            # 保留系统消息
            self.message_history = [self.message_history[0]]
        else:
            self.message_history = []
        print(f"{Colors.GREEN}Message history cleared.{Colors.ENDC}")
        return self.message_history
    
    def get_messages(self):
        """获取完整的消息历史"""
        return self.message_history 