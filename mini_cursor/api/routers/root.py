#!/usr/bin/env python3

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from mini_cursor.core.config import OPENAI_MODEL, OPENAI_BASE_URL, TOOL_CALL_TIMEOUT
from mini_cursor.api.dependencies import static_dir, get_configuration_errors

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def root():
    """根路径，提供API信息和演示页面链接"""
    return f"""
    <html>
        <head>
            <title>Mini Cursor API</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                }}
                a {{
                    color: #0066cc;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                .info {{
                    background-color: #f5f5f5;
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <h1>Mini Cursor API</h1>
            <div class="info">
                <p><strong>状态：</strong> 运行中</p>
                <p><strong>模型：</strong> {OPENAI_MODEL}</p>
                <p><strong>工具调用超时：</strong> {TOOL_CALL_TIMEOUT}秒</p>
            </div>
            <p>欢迎使用 Mini Cursor API！您可以通过以下方式使用此API：</p>
            <ul>
                <li><a href="/demo">打开演示页面</a> - 简单的Web界面测试</li>
                <li><a href="/docs">API文档</a> - FastAPI自动生成的Swagger文档</li>
                <li><a href="/redoc">ReDoc文档</a> - 另一种格式的API文档</li>
            </ul>
        </body>
    </html>
    """

@router.get("/demo", response_class=HTMLResponse)
async def demo():
    """返回演示页面"""
    try:
        with open(static_dir / "api_demo.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <body>
                <h1>Demo页面未找到</h1>
                <p>请确保static/api_demo.html文件存在</p>
                <p><a href="/">返回首页</a></p>
            </body>
        </html>
        """

@router.get("/api-info")
async def api_info():
    """API信息端点"""
    config_errors = get_configuration_errors()
    has_errors = bool(config_errors)
    
    response = {
        "status": "warning" if has_errors else "ok",
        "name": "Mini Cursor API",
        "model": OPENAI_MODEL,
        "base_url": OPENAI_BASE_URL,
        "tool_call_timeout": TOOL_CALL_TIMEOUT
    }
    
    if has_errors:
        response["configuration_errors"] = config_errors
        response["message"] = "检测到配置错误，请访问配置页面修复问题，或检查终端日志获取详情"
        
    return response 