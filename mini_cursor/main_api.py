#!/usr/bin/env python3

"""
这个文件保留用于向后兼容。
新代码已重构到 mini_cursor/api/ 目录中。
"""

import os
import sys
from mini_cursor.api.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7727))
    host = os.environ.get("HOST", "0.0.0.0")
    
    # 直接运行新的API模块
    uvicorn.run("mini_cursor.api.main:app", host=host, port=port, reload=False) 