#!/usr/bin/env python
"""
调试测试文件：演示如何在开发过程中调试mini-cursor包
"""

import mini_cursor
from mini_cursor import cli_main

def main():
    print("开始调试测试")
    
    # 使用Python内置的pdb进行调试
    import pdb; pdb.set_trace()  # 这里将会暂停执行，进入调试模式
    
    # 在调试器中，你可以：
    # - 打印变量: p mini_cursor.__version__
    # - 执行语句: !print(dir(cli_main))
    # - 继续执行: c
    # - 退出调试: q
    
    # 测试包功能
    print(f"包版本: {mini_cursor.__version__}")
    
    # 在这里可以测试其他功能
    
    print("调试测试完成")

if __name__ == "__main__":
    main() 