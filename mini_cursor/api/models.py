#!/usr/bin/env python3

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query: str
    system_prompt: Optional[str] = None
    workspace: Optional[str] = None

class OpenAIConfigRequest(BaseModel):
    """OpenAI配置请求模型"""
    base_url: str
    model: str
    api_key: Optional[str] = None

class MCPConfigRequest(BaseModel):
    """MCP配置请求模型"""
    config: Dict[str, Any]

class ToolEnablementRequest(BaseModel):
    """工具启用/禁用请求模型"""
    tool_name: str

class ToolModeRequest(BaseModel):
    """工具模式请求模型"""
    mode: str

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    summary: Optional[str] = None
    turns: int

class LoadConversationRequest(BaseModel):
    conversation_id: str

class SystemPromptRequest(BaseModel):
    """系统提示请求模型"""
    content: str 