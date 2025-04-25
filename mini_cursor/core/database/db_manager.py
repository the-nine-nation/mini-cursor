import os
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class DatabaseManager:
    """
    SQLite数据库管理类，用于存储和检索对话历史
    简化版：使用单一表结构，将对话内容以JSON形式存储
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径，如果为None则使用默认路径
        """
        if db_path is None:
            # 使用项目根目录下的数据文件夹
            base_dir = Path(__file__).parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(exist_ok=True)
            self.db_path = data_dir / "conversations.db"
        else:
            self.db_path = Path(db_path)
        
        self.conn = None
        self.cursor = None
        self.initialize_database()
    
    def initialize_database(self) -> None:
        """初始化数据库连接和表结构"""
        # 检查数据库文件是否存在
        is_new_db = not self.db_path.exists()
        
        # 连接到数据库
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        self.cursor = self.conn.cursor()
        
        # 如果是新数据库，创建表结构
        if is_new_db:
            print(f"Creating new database at {self.db_path}")
            self._create_tables()
        else:
            print(f"Connected to existing database at {self.db_path}")
    
    def _create_tables(self) -> None:
        """创建数据库表结构 - 简化版"""
        # 使用单一的对话表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,         -- 整个对话内容的JSON字符串
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            summary TEXT,
            turns INTEGER         -- 对话轮次数
        )
        ''')
        
        self.conn.commit()
    
    def create_conversation(self, title: Optional[str] = None) -> str:
        """
        创建新的对话会话
        
        Args:
            title: 对话标题，如果为None则使用当前时间
            
        Returns:
            str: 新创建的对话ID
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        
        if title is None:
            title = f"对话 {now.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 初始化空对话内容
        content = json.dumps({
            "messages": [],
            "system_prompt": ""
        })
        
        self.cursor.execute(
            "INSERT INTO conversations (id, title, content, created_at, updated_at, turns) VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, title, content, now, now, 0)
        )
        self.conn.commit()
        
        return conversation_id
    
    def add_message_to_conversation(self, conversation_id: str, sender: str, message: str) -> bool:
        """
        向对话中添加新消息
        
        Args:
            conversation_id: 对话ID
            sender: 消息发送者（"user" 或 "assistant"）
            message: 消息内容
            
        Returns:
            bool: 是否成功添加
        """
        now = datetime.now()
        
        # 获取当前对话内容
        self.cursor.execute(
            "SELECT content, turns FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            return False
        
        content = json.loads(result['content'])
        turns = result['turns']
        
        # 添加新消息
        content['messages'].append({
            "sender": sender,
            "content": message,
            "timestamp": now.isoformat()
        })
        
        # 如果是用户消息，增加轮次计数
        if sender == "user":
            turns += 1
        
        # 更新对话内容
        self.cursor.execute(
            "UPDATE conversations SET content = ?, updated_at = ? WHERE id = ?",
            (json.dumps(content), now, conversation_id)
        )
        self.conn.commit()
        
        return True
    
    def add_tool_call_to_conversation(self, conversation_id: str, tool_name: str, tool_args: str, tool_result: str, is_error: bool = False) -> bool:
        """
        向对话中添加工具调用记录
        
        Args:
            conversation_id: 对话ID
            tool_name: 工具名称
            tool_args: 工具参数
            tool_result: 工具调用结果
            is_error: 是否为错误结果
            
        Returns:
            bool: 是否成功添加
        """
        now = datetime.now()
        
        # 获取当前对话内容
        self.cursor.execute(
            "SELECT content FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            return False
        
        content = json.loads(result['content'])
        
        # 添加工具调用记录
        content['messages'].append({
            "sender": "tool",
            "tool_name": tool_name,
            "tool_args": tool_args,
            "tool_result": tool_result,
            "is_error": is_error,
            "timestamp": now.isoformat()
        })
        
        # 更新对话内容
        self.cursor.execute(
            "UPDATE conversations SET content = ?, updated_at = ? WHERE id = ?",
            (json.dumps(content), now, conversation_id)
        )
        self.conn.commit()
        
        return True
    
    def set_system_prompt(self, conversation_id: str, system_prompt: str) -> bool:
        """
        设置对话的系统提示
        
        Args:
            conversation_id: 对话ID
            system_prompt: 系统提示内容
            
        Returns:
            bool: 是否成功设置
        """
        # 获取当前对话内容
        self.cursor.execute(
            "SELECT content FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            return False
        
        content = json.loads(result['content'])
        content['system_prompt'] = system_prompt
        
        # 更新对话内容
        self.cursor.execute(
            "UPDATE conversations SET content = ? WHERE id = ?",
            (json.dumps(content), conversation_id)
        )
        self.conn.commit()
        
        return True
    
    def update_conversation_summary(self, conversation_id: str, summary: str) -> bool:
        """
        更新对话摘要
        
        Args:
            conversation_id: 对话ID
            summary: 对话摘要
            
        Returns:
            bool: 是否成功更新
        """
        self.cursor.execute(
            "UPDATE conversations SET summary = ? WHERE id = ?",
            (summary, conversation_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        获取对话详情
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Dict[str, Any] 或 None: 对话详情
        """
        self.cursor.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            return None
        
        # 转换为字典
        conversation_dict = dict(result)
        
        # 解析JSON内容
        if 'content' in conversation_dict:
            conversation_dict['content'] = json.loads(conversation_dict['content'])
        
        return conversation_dict
    
    def get_recent_conversations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的对话列表
        
        Args:
            limit: 返回的最大对话数量
            
        Returns:
            List[Dict[str, Any]]: 对话列表，按更新时间倒序排列
        """
        self.cursor.execute(
            "SELECT id, title, created_at, updated_at, summary, turns FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        )
        results = self.cursor.fetchall()
        
        return [dict(row) for row in results]
    
    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """
        获取所有对话列表
        
        Returns:
            List[Dict[str, Any]]: 所有对话列表，按更新时间倒序排列
        """
        self.cursor.execute(
            "SELECT id, title, created_at, updated_at, summary, turns FROM conversations ORDER BY updated_at DESC"
        )
        results = self.cursor.fetchall()
        
        return [dict(row) for row in results]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除一个对话
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            bool: 是否成功删除
        """
        try:
            self.cursor.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None


# 单例模式，提供全局访问点
_db_instance = None

def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器实例（单例模式）
    
    Returns:
        DatabaseManager: 数据库管理器实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance 