#!/usr/bin/env python3

import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ToolCall:
    """工具调用记录"""
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    result: Any = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

    def to_dict(self):
        """将对象转换为字典"""
        return asdict(self)


class ToolHistoryManager:
    """工具调用历史记录管理器"""
    
    def __init__(self, max_history: int = 1000):
        """初始化管理器
        
        Args:
            max_history: 保存的最大历史记录数量
        """
        self.tool_calls: Dict[str, ToolCall] = {}  # 工具调用记录，键为调用ID
        self.max_history = max_history
    
    def record_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """记录工具调用
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            调用ID
        """
        # 生成唯一ID
        call_id = str(uuid.uuid4())
        
        # 记录调用
        self.tool_calls[call_id] = ToolCall(
            id=call_id,
            tool_name=tool_name,
            arguments=arguments
        )
        
        # 如果历史记录超过最大数量，删除最早的记录
        if len(self.tool_calls) > self.max_history:
            oldest_key = min(self.tool_calls.keys(), key=lambda k: self.tool_calls[k].timestamp)
            del self.tool_calls[oldest_key]
        
        return call_id
    
    def record_tool_result(self, call_id: str, result: Any, error: Optional[str] = None) -> bool:
        """记录工具调用结果
        
        Args:
            call_id: 调用ID
            result: 调用结果
            error: 错误信息，如果有
            
        Returns:
            是否成功记录
        """
        if call_id not in self.tool_calls:
            return False
        
        tool_call = self.tool_calls[call_id]
        tool_call.result = result
        tool_call.error = error
        tool_call.execution_time = time.time() - tool_call.timestamp
        
        return True
    
    def get_tool_call(self, call_id: str) -> Optional[Dict]:
        """获取工具调用记录
        
        Args:
            call_id: 调用ID
            
        Returns:
            工具调用记录字典，如果不存在则返回None
        """
        tool_call = self.tool_calls.get(call_id)
        if tool_call:
            return tool_call.to_dict()
        return None
    
    def get_recent_tool_calls(self, limit: int = 10) -> List[Dict]:
        """获取最近的工具调用记录
        
        Args:
            limit: 返回记录的最大数量
            
        Returns:
            工具调用记录列表，按时间倒序排列
        """
        # 按时间戳倒序排序
        sorted_calls = sorted(
            self.tool_calls.values(),
            key=lambda call: call.timestamp,
            reverse=True
        )
        
        # 返回前limit个
        return [call.to_dict() for call in sorted_calls[:limit]]
    
    def clear_history(self):
        """清除所有历史记录"""
        self.tool_calls.clear() 