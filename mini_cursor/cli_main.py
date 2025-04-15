import sys
import asyncio
from mini_cursor.core import cli
from mini_cursor.mcp_qa import main as qa_main
import os

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"cli"}:
        print("用法: mini-cursor cli [config|mcp-config|chat|init]")
        sys.exit(1)
    if len(sys.argv) < 3:
        print("用法: mini-cursor cli [config|mcp-config|chat|init]")
        sys.exit(1)
    subcmd = sys.argv[2]
    if subcmd == "config":
        # 进入参数修改界面
        # 假设cli.py有config_main函数
        from mini_cursor.core.cli import config_main
        config_main()
    elif subcmd == "mcp-config":
        # 生成mcpconfig
        from mini_cursor.core.cli import mcp_config_generate_main
        mcp_config_generate_main()
    elif subcmd == "chat":
        # 进入聊天模式
        workspace = os.getcwd()
        asyncio.run(qa_main(workspace=workspace))
    elif subcmd == "init":
        from mini_cursor.core.cli import init_main
        init_main()
    else:
        print(f"未知子命令: {subcmd}")
        sys.exit(1) 