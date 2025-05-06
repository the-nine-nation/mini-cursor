#!/usr/bin/env python3

import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

from mini_cursor.core.config import Colors, OPENAI_BASE_URL, OPENAI_MODEL, TOOL_CALL_TIMEOUT, VERBOSE_LOGGING
from mini_cursor.api.dependencies import static_dir, client_cache, server_manager_cache, tool_manager_cache
from mini_cursor.api.routers import root, tools, chat, config, conversations
from mini_cursor.core.database import get_db_manager

# 定义生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 这里可以添加启动逻辑（如果有的话）
    # yield 之前的代码会在应用启动时执行
    
    # 初始化SQLite数据库（如果不存在）
    print("正在检查SQLite数据库...")
    db = get_db_manager()
    print("数据库检查完成")
    
    yield  # 应用在此处运行
    
    # yield 之后的代码会在应用关闭时执行
    # 清理资源
    for pid, client in client_cache.items():
        await client.close()
    
    for pid, server_manager in server_manager_cache.items():
        await server_manager.close()
    
    client_cache.clear()
    server_manager_cache.clear()
    tool_manager_cache.clear()

# 创建 FastAPI 应用
app = FastAPI(
    title="Mini Cursor API", 
    description="API for Mini Cursor with SSE streaming", 
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境下应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 添加favicon路由
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(os.path.join(static_dir, 'favicon.ico'))

# 包含所有路由器
app.include_router(root.router)
app.include_router(chat.router)
app.include_router(tools.router)
app.include_router(config.router)
app.include_router(conversations.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7727))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"{Colors.BOLD}{Colors.CYAN}Mini Cursor API Server{Colors.ENDC}")
    print(f"{Colors.CYAN}Python version: {sys.version}{Colors.ENDC}")
    print(f"{Colors.CYAN}OpenAI API Base URL: {OPENAI_BASE_URL}{Colors.ENDC}")
    print(f"{Colors.CYAN}Using model: {OPENAI_MODEL}{Colors.ENDC}")
    print(f"{Colors.CYAN}Tool call timeout: {TOOL_CALL_TIMEOUT}s{Colors.ENDC}")
    print(f"{Colors.CYAN}Listening on: http://{host}:{port}{Colors.ENDC}")
    
    uvicorn.run("mini_cursor.api.main:app", host=host, port=port, reload=False) 