#!/usr/bin/env python3

import os
import json
import sys
from fastapi import APIRouter, Depends
from pathlib import Path
from dotenv import dotenv_values,set_key

from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.core.config import MCP_CONFIG_FILE
from mini_cursor.api.dependencies import get_client, current_dir
from mini_cursor.api.models import OpenAIConfigRequest, MCPConfigRequest, SystemPromptRequest

router = APIRouter(
    tags=["config"],
)

@router.post("/update-openai-config")
async def update_openai_config(request: OpenAIConfigRequest, client: MCPClient = Depends(get_client)):
    """更新OpenAI配置
    
    更新OpenAI API的基础URL、模型和API Key（如果提供）
    配置更新后会重新初始化 OpenAI 客户端
    """
    try:
        
        # 将配置写入.env文件以持久化
        # 尝试定位项目根目录的.env文件
        # 通常mini_cursor是包名，所以要查找包所在目录的.env文件
        current_dir = Path(__file__).resolve()  # 当前文件的绝对路径
        # 向上查找包含mini_cursor目录的父目录
        project_root = current_dir.parent.parent.parent  # 这应该是mini-cursor目录
        env_file_path = project_root / ".env"
        if not env_file_path.exists():
            # 如果.env文件不存在，创建一个空的.env文件
            env_file_path.touch()
            env_content={}
        else:
            # 读取现有的.env文件内容（如果存在）
            env_content = dotenv_values(env_file_path)
        
        # 更新配置
        env_content["OPENAI_BASE_URL"] = request.base_url
        env_content["OPENAI_MODEL"] = request.model
        if request.api_key and request.api_key.strip():
            env_content["OPENAI_API_KEY"] = request.api_key
    

        for key, value in env_content.items():
            set_key(env_file_path, key, value)
    
        return {
            "status": "ok",
            "message": "OpenAI配置已更新并持久化",
            "config": {
                "base_url": request.base_url,
                "model": request.model,
                "api_key_updated": bool(request.api_key and request.api_key.strip())
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"更新OpenAI配置时出错: {str(e)}"
        }

@router.get("/mcp-config")
async def get_mcp_config():
    """获取MCP配置"""
    try:
        # 检查配置文件是否存在
        config_path = Path(MCP_CONFIG_FILE)
        
        # 读取配置
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        return {"status": "success", "data": config_data}
    except Exception as e:
        return {"status": "error", "message": f"读取配置失败: {str(e)}"}


@router.post("/update-mcp-config")
async def update_mcp_config(request: MCPConfigRequest, client: MCPClient = Depends(get_client)):
    """更新MCP配置文件
    
    更新MCP配置文件内容并重新连接服务器
    """
    try:
        config_path = Path(MCP_CONFIG_FILE)
        
        # 保存新配置到文件
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(request.config, f, indent=4, ensure_ascii=False)
        
        # 重新连接MCP服务器
        await client.server_manager.close()
        await client.server_manager.connect_to_servers(client.tool_manager)
        
        return {
            "status": "ok",
            "message": "MCP配置已更新并已重新连接服务器"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"更新MCP配置失败: {str(e)}"
        }

@router.get("/system-prompt")
async def get_system_prompt():
    """获取当前系统提示"""
    try:
        # 获取系统提示文件路径
        prompt_path = Path(current_dir) / "data" / "system_prompt.txt"
        
        # 读取系统提示内容
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()
        
        return {"status": "success", "content": prompt_content}
    except Exception as e:
        return {"status": "error", "message": f"读取系统提示失败: {str(e)}"}

@router.post("/update-system-prompt")
async def update_system_prompt(request: SystemPromptRequest):
    """更新系统提示"""
    try:
        # 获取系统提示文件路径
        prompt_path = Path(current_dir) / "data" / "system_prompt.txt"
        
        # 写入新的系统提示内容
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        
        return {"status": "success", "message": "系统提示已更新"}
    except Exception as e:
        return {"status": "error", "message": f"更新系统提示失败: {str(e)}"}

@router.post("/reset-system-prompt")
async def reset_system_prompt():
    """重置系统提示为默认值"""
    try:
        # 获取默认系统提示文件路径
        default_prompt_path = Path(current_dir) / "data" / "system_prompt_default.txt"
        prompt_path = Path(current_dir) / "data" / "system_prompt.txt"
        
        # 读取默认系统提示内容
        with open(default_prompt_path, "r", encoding="utf-8") as f:
            default_prompt_content = f.read()
        
        # 将默认系统提示写入当前系统提示文件
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(default_prompt_content)
        
        return {"status": "success", "content": default_prompt_content, "message": "系统提示已重置为默认值"}
    except Exception as e:
        return {"status": "error", "message": f"重置系统提示失败: {str(e)}"} 