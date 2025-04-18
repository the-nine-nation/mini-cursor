#!/usr/bin/env python
"""
开发调试脚本：直接运行chat功能进行测试
"""
import os
import asyncio
from mini_cursor.mcp_qa import main as qa_main

print("启动chat功能测试...")
workspace = os.getcwd()

# 直接运行chat功能，绕过cli入口
if __name__ == "__main__":
    asyncio.run(qa_main(workspace=workspace)) 