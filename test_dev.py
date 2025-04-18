#!/usr/bin/env python
"""
开发测试文件：用于在开发过程中测试mini-cursor包的功能，无需重新安装
"""

import sys
import os
from pathlib import Path

# 导入mini_cursor包
import mini_cursor

# 显示包信息
print(f"mini_cursor 版本: {mini_cursor.__version__ if hasattr(mini_cursor, '__version__') else '未定义'}")
print(f"包路径: {mini_cursor.__file__}")
print(f"父目录: {Path(mini_cursor.__file__).parent}")

# 导入cli模块
from mini_cursor import cli_main

# 列出可用的命令
print("\n可用命令:")
for command in dir(cli_main):
    if not command.startswith("_") and callable(getattr(cli_main, command)):
        print(f"- {command}")

# 这里你可以添加任何想要测试的功能
print("\n测试完成!") 