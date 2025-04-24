#!/usr/bin/env python3

from fastapi import APIRouter, Depends, Query
from typing import List

from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.api.dependencies import get_client, get_db_manager
from mini_cursor.api.models import ConversationResponse, LoadConversationRequest

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)

@router.get("", response_model=List[ConversationResponse])
async def get_conversations(limit: int = Query(10, ge=1, le=50)):
    """
    获取最近的对话历史列表
    
    Args:
        limit: 返回的最大对话数量，默认10条，最大50条
    """
    db = get_db_manager()
    conversations = db.get_recent_conversations(limit)
    
    return conversations

@router.get("/all", response_model=List[ConversationResponse])
async def get_all_conversations():
    """
    获取全部历史对话列表，不分页
    
    返回所有历史对话记录，按更新时间倒序排列，包含对话ID、时间、摘要等信息
    """
    db = get_db_manager()
    conversations = db.get_all_conversations()
    
    return conversations

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    获取特定对话的详细信息
    
    Args:
        conversation_id: 对话ID
    """
    db = get_db_manager()
    conversation = db.get_conversation(conversation_id)
    
    if not conversation:
        return {
            "status": "error",
            "message": f"找不到ID为 {conversation_id} 的对话记录"
        }
    
    return {
        "status": "ok",
        "conversation": conversation
    }

@router.post("/load")
async def load_conversation(request: LoadConversationRequest, client: MCPClient = Depends(get_client)):
    """
    加载指定的历史对话到当前会话
    
    Args:
        conversation_id: 要加载的对话ID
    """
    try:
        db = get_db_manager()
        conversation = db.get_conversation(request.conversation_id)
        
        if not conversation:
            return {
                "status": "error",
                "message": f"找不到ID为 {request.conversation_id} 的对话记录"
            }
        
        # 清空当前会话历史
        client.message_manager.clear_message_history()
        
        # 设置当前对话ID
        client.current_conversation_id = request.conversation_id
        
        # 从数据库中的JSON加载对话历史
        if 'content' in conversation:
            content = conversation['content']
            
            # 设置系统提示
            if content.get('system_prompt'):
                # 添加系统消息
                system_message = {
                    "role": "system", 
                    "content": content.get('system_prompt')
                }
                client.message_manager.message_history = [system_message]
            
            # 加载消息历史
            for msg in content.get('messages', []):
                if msg.get('sender') == 'user':
                    # 添加用户消息
                    client.message_manager.add_user_message(
                        msg.get('content', ''),
                        None  # 不更新系统提示
                    )
                elif msg.get('sender') == 'assistant':
                    # 添加助手消息
                    client.message_manager.add_assistant_message(
                        msg.get('content', '')
                    )
                elif msg.get('sender') == 'tool':
                    # 跳过工具消息，它们会在下一轮对话中重新生成
                    pass
        
        return {
            "status": "ok",
            "message": "历史对话已加载",
            "conversation_id": request.conversation_id,
            "title": conversation.get('title', ''),
            "turns": conversation.get('turns', 0)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"加载对话时出错: {str(e)}"
        }

@router.post("/{conversation_id}/delete")
async def delete_conversation(conversation_id: str, client: MCPClient = Depends(get_client)):
    """
    删除特定对话记录
    
    Args:
        conversation_id: 要删除的对话ID
    """
    try:
        db = get_db_manager()
        result = db.delete_conversation(conversation_id)
        
        # 如果删除的是当前对话，清空当前会话状态
        if client.current_conversation_id == conversation_id:
            client.message_manager.clear_message_history()
            client.current_conversation_id = None
        
        return {
            "status": "ok" if result else "error",
            "message": "对话已删除" if result else "对话不存在或无法删除"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"删除对话时出错: {str(e)}"
        }

@router.get("/detail/{conversation_id}")
async def get_conversation_detail(conversation_id: str):
    """
    获取特定对话的完整记录
    
    返回对话的所有轮次内容，包括用户输入、AI回复、工具调用等详细信息，
    以便前端还原完整对话过程
    
    Args:
        conversation_id: 对话ID
    """
    try:
        db = get_db_manager()
        conversation = db.get_conversation(conversation_id)
        
        if not conversation:
            return {
                "status": "error",
                "message": f"找不到ID为 {conversation_id} 的对话记录"
            }
        
        # 提取对话基本信息
        conversation_detail = {
            "id": conversation["id"],
            "title": conversation["title"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"],
            "summary": conversation.get("summary", ""),
            "turns": conversation["turns"],
            "system_prompt": conversation["content"].get("system_prompt", ""),
            "messages": []
        }
        
        # 整理消息记录，将其转换为前端友好的格式
        if "content" in conversation and "messages" in conversation["content"]:
            for msg in conversation["content"]["messages"]:
                message_data = {
                    "type": msg.get("sender", "unknown"),
                    "timestamp": msg.get("timestamp", "")
                }
                
                # 根据消息类型处理不同字段
                if msg.get("sender") == "user":
                    message_data["content"] = msg.get("content", "")
                elif msg.get("sender") == "assistant":
                    message_data["content"] = msg.get("content", "")
                elif msg.get("sender") == "tool":
                    message_data["tool_name"] = msg.get("tool_name", "")
                    message_data["tool_args"] = msg.get("tool_args", "")
                    message_data["tool_result"] = msg.get("tool_result", "")
                
                conversation_detail["messages"].append(message_data)
        
        return {
            "status": "ok",
            "conversation": conversation_detail
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取对话详情时出错: {str(e)}"
        }

@router.post("/clear")
async def clear_conversation(client: MCPClient = Depends(get_client)):
    """
    清除当前对话历史并创建新的对话
    
    返回新创建的对话ID
    """
    try:
        # 清空消息历史
        client.message_manager.clear_message_history()
        
        # 创建新的会话ID
        db = get_db_manager()
        new_conversation_id = db.create_conversation()
        
        # 更新客户端的当前会话ID
        client.current_conversation_id = new_conversation_id
        
        return {
            "status": "ok",
            "message": "对话历史已清除，新会话已创建",
            "conversation_id": new_conversation_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"清除对话历史时出错: {str(e)}"
        } 