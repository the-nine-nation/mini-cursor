#!/usr/bin/env python3

import asyncio
import json
import os
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.api.dependencies import get_client, os_version, shell_path
from mini_cursor.api.models import ChatRequest
from mini_cursor.api.routers.prompt_manager import load_system_prompt

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)
user_info="""
<user_info>
The user's OS version is %s. The absolute path of the user's workspace is %s. The user's shell is %s. 
</user_info>
"""
@router.post("")
async def chat(request: ChatRequest, client: MCPClient = Depends(get_client)):
    """聊天端点，使用 SSE 流式返回响应"""
    workspace = request.workspace or os.getcwd()
    custom_system_prompt = request.system_prompt or load_system_prompt()
    
    # 获取对话历史记录（如果有）
    conversation_history = request.conversation_history if hasattr(request, 'conversation_history') else None
    
    # 准备 SSE 流
    async def generate_stream():
        # 初始化process_task为None，以便在发生异常时安全检查
        process_task = None
        try:
            # 设置事件监听器以捕获更新并发送 SSE 事件
            event_queue = asyncio.Queue()
            
            # 创建一个监听函数
            def event_listener(event_type, data):
                asyncio.create_task(event_queue.put({
                    "type": event_type,
                    "data": data
                }))
            
            # 保存原始监听器（如果有）
            original_listener = client.update_listener
            
            # 设置新的监听器
            client.set_update_listener(event_listener)
            
            try:
                # 启动异步处理查询的任务，传递对话历史记录
                process_task = asyncio.create_task(
                    client.process_query(
                        request.query, 
                        custom_system_prompt+user_info%(os_version, workspace, shell_path),
                        stream=True,
                        conversation_history=conversation_history
                    )
                )
                
                # 首先发送一个初始事件
                yield f"event: start\ndata: {json.dumps({'status': 'processing'})}\n\n"
                
                # 添加标志来跟踪是否为首个消息事件
                is_first_message = True
                
                # 处理事件队列
                while True:
                    # 检查处理查询的任务是否已完成
                    if process_task.done():
                        # 如果任务出错，发送错误信息
                        if process_task.exception():
                            error = str(process_task.exception())
                            yield f"event: error\ndata: {json.dumps({'error': error})}\n\n"
                        # 发送完成事件并退出循环
                        yield f"event: done\ndata: {json.dumps({'status': 'completed'})}\n\n"
                        break
                    
                    # 等待事件队列中的消息，但设置超时，以便定期检查process_task的状态
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=0.5)
                        event_type = event["type"]
                        event_data = event["data"]
                        
                        if event_type == "assistant_message":
                            # 检查是否是首条消息且内容仅为"\n\n"
                            if is_first_message and event_data == "\n\n" or event_data == "\n":
                                # 忽略此消息，不发送
                                is_first_message = False
                                continue
                            
                            # 不是首条消息或内容不仅为"\n\n"，正常发送
                            is_first_message = False
                            yield f"event: message\ndata: {json.dumps({'content': event_data}, ensure_ascii=False)}\n\n"
                        elif event_type == "thinking":
                            yield f"event: thinking\ndata: {json.dumps({'content': event_data}, ensure_ascii=False)}\n\n"
                        elif event_type == "tool_call":
                            yield f"event: tool_call\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                        elif event_type == "tool_result":
                            # 分离工具结果，不对output内容进行json序列化
                            result = event_data.get('result', event_data.get('output', ''))
                            # 移除result/output字段，这样就不会被双重序列化
                            event_data_copy = event_data.copy()
                            if 'result' in event_data_copy:
                                del event_data_copy['result']
                            if 'output' in event_data_copy:
                                del event_data_copy['output']
                            
                            # 确保事件数据中包含工具调用ID
                            if 'id' not in event_data_copy and 'id' in event_data:
                                event_data_copy['id'] = event_data['id']
                            
                            yield f"event: tool_result\ndata: {json.dumps(event_data_copy, ensure_ascii=False)}\noutput: {result}\n\n"
                        elif event_type == "tool_error":
                            # 分离错误信息，不对error内容进行json序列化
                            error = event_data.get('error', '')
                            # 移除error字段
                            event_data_copy = event_data.copy()
                            if 'error' in event_data_copy:
                                del event_data_copy['error']
                            
                            # 确保事件数据中包含工具调用ID
                            if 'id' not in event_data_copy and 'id' in event_data:
                                event_data_copy['id'] = event_data['id']
                            
                            yield f"event: tool_error\ndata: {json.dumps(event_data_copy, ensure_ascii=False)}\nerror: {error}\n\n"
                    except asyncio.TimeoutError:
                        # 超时只是用来定期检查process_task状态，不是真正的错误
                        continue
            finally:
                # 恢复原始监听器
                client.set_update_listener(original_listener)
                
                # 确保任务被取消（如果尚未完成）
                if process_task is not None and not process_task.done():
                    process_task.cancel()
                    try:
                        await process_task
                    except asyncio.CancelledError:
                        pass
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'message': 'An error occurred'}, ensure_ascii=False)}\nerror: {str(e)}\n\n"
    
    # 返回 SSE 流
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 防止Nginx等代理服务器缓冲响应
        }
    ) 