#!/usr/bin/env python3

from fastapi import APIRouter, Depends

from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.api.dependencies import get_client, get_enabled_tool_names, get_configuration_errors
from mini_cursor.api.models import ToolEnablementRequest, ToolModeRequest

router = APIRouter(
    prefix="/tools",
    tags=["tools"],
)

@router.get("")
async def list_tools(client: MCPClient = Depends(get_client)):
    """返回所有可用的MCP服务及其工具信息"""
    result = {}
    
    # 获取配置错误信息
    config_errors = get_configuration_errors()
    has_errors = bool(config_errors)
    
    # 获取工具管理器
    tool_manager = client.tool_manager
    
    try:
        # 获取所有服务器及其工具
        # 注意：server_tools是嵌套字典结构，外层是服务器名称，内层是工具名称到工具对象的映射
        for server_name, tools_dict in tool_manager.server_tools.items():
            server_info = {
                "name": server_name,
                "tools": []
            }
            
            # 处理每个工具 - 这里tools_dict是一个字典，key是工具名称，value是工具对象
            for tool_name, tool in tools_dict.items():
                tool_info = {
                    "name": tool_name,
                    "description": tool.description if hasattr(tool, "description") else "No description"
                }
                
                # 添加参数信息（如果有）
                if hasattr(tool, "parameters") and tool.parameters:
                    # 提取参数的简化信息
                    parameters = {}
                    if hasattr(tool.parameters, "properties") and tool.parameters.properties:
                        for param_name, param in tool.parameters.properties.items():
                            param_info = {
                                "description": getattr(param, "description", ""),
                                "type": getattr(param, "type", "string"),
                                "required": param_name in (getattr(tool.parameters, "required", []) or [])
                            }
                            parameters[param_name] = param_info
                    
                    tool_info["parameters"] = parameters
                elif hasattr(tool, "inputSchema") and tool.inputSchema:
                    # 适配不同格式的工具参数结构
                    try:
                        if isinstance(tool.inputSchema, dict) and "properties" in tool.inputSchema:
                            parameters = {}
                            for param_name, param in tool.inputSchema.get("properties", {}).items():
                                param_info = {
                                    "description": param.get("description", ""),
                                    "type": param.get("type", "string"),
                                    "required": param_name in (tool.inputSchema.get("required", []) or [])
                                }
                                parameters[param_name] = param_info
                            tool_info["parameters"] = parameters
                    except Exception as e:
                        print(f"Error processing parameters for tool {tool_name}: {e}")
                
                server_info["tools"].append(tool_info)
            
            result[server_name] = server_info
    except Exception as e:
        # 捕获所有异常，返回一个空的结果集但仍然可以渲染页面
        print(f"Error listing tools: {e}")
        if not has_errors:
            config_errors['tools_list'] = {
                'error': f"获取工具列表失败: {str(e)}",
                'traceback': str(e)
            }
            has_errors = True
    
    try:
        enabled_tools = get_enabled_tool_names(tool_manager)
        tool_enablement_mode = tool_manager.tool_enablement_mode
    except Exception as e:
        print(f"Error getting tool enablement info: {e}")
        enabled_tools = []
        tool_enablement_mode = "all"  # 默认模式
    
    response = {
        "status": "warning" if has_errors else "ok",
        "servers": result,
        "enabled_tools": enabled_tools,
        "tool_enablement_mode": tool_enablement_mode
    }
    
    # 如果有配置错误，添加到响应中
    if has_errors:
        response["configuration_errors"] = config_errors
        response["message"] = "检测到配置错误，请访问配置页面修复问题，或检查终端日志获取详情"
    
    return response

@router.post("/enable")
async def enable_tool(request: ToolEnablementRequest, client: MCPClient = Depends(get_client)):
    """启用特定工具"""
    tool_manager = client.tool_manager
    result = tool_manager.enable_tool(request.tool_name)
    
    return {
        "status": "ok" if result else "error",
        "message": f"工具 {request.tool_name} 已启用" if result else f"工具 {request.tool_name} 不存在或无法启用",
        "enabled_tools": get_enabled_tool_names(tool_manager)
    }

@router.post("/disable")
async def disable_tool(request: ToolEnablementRequest, client: MCPClient = Depends(get_client)):
    """禁用特定工具"""
    tool_manager = client.tool_manager
    result = tool_manager.disable_tool(request.tool_name)
    
    return {
        "status": "ok" if result else "error",
        "message": f"工具 {request.tool_name} 已禁用" if result else f"工具 {request.tool_name} 不存在或无法禁用",
        "enabled_tools": get_enabled_tool_names(tool_manager)
    }

@router.post("/enable-all")
async def enable_all_tools(client: MCPClient = Depends(get_client)):
    """启用所有工具"""
    tool_manager = client.tool_manager
    tool_manager.enable_all_tools()
    
    return {
        "status": "ok",
        "message": "所有工具已启用",
        "enabled_tools": get_enabled_tool_names(tool_manager)
    }

@router.post("/disable-all")
async def disable_all_tools(client: MCPClient = Depends(get_client)):
    """禁用所有工具"""
    tool_manager = client.tool_manager
    tool_manager.disable_all_tools()
    
    return {
        "status": "ok",
        "message": "所有工具已禁用",
        "enabled_tools": get_enabled_tool_names(tool_manager)
    }

@router.post("/mode")
async def set_tool_mode(request: ToolModeRequest, client: MCPClient = Depends(get_client)):
    """设置工具启用模式"""
    tool_manager = client.tool_manager
    
    if request.mode not in ['all', 'selective']:
        return {
            "status": "error",
            "message": "无效的模式，必须是 'all' 或 'selective'"
        }
    
    tool_manager.set_tool_enablement_mode(request.mode)
    
    return {
        "status": "ok",
        "message": f"工具启用模式已设置为 {request.mode}",
        "tool_enablement_mode": tool_manager.tool_enablement_mode,
        "enabled_tools": get_enabled_tool_names(tool_manager)
    }

@router.get("/history")
async def get_tool_history(limit: int = 10, client: MCPClient = Depends(get_client)):
    """获取最近的工具调用历史
    
    Args:
        limit: 返回的历史记录数量，默认10条
    """
    return {
        "status": "ok",
        "history": client.tool_history_manager.get_recent_tool_calls(limit)
    }

@router.get("/history/{call_id}")
async def get_tool_call_detail(call_id: str, client: MCPClient = Depends(get_client)):
    """获取特定工具调用的详细信息
    
    Args:
        call_id: 工具调用ID
    """
    tool_call = client.tool_history_manager.get_tool_call(call_id)
    if not tool_call:
        return {
            "status": "error",
            "message": f"找不到ID为 {call_id} 的工具调用记录"
        }
    
    return {
        "status": "ok",
        "tool_call": tool_call
    } 