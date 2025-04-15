#!/usr/bin/env python3

import asyncio
import sys
import traceback

from mini_cursor.core.config import Colors, OPENAI_BASE_URL, OPENAI_MODEL, TOOL_CALL_TIMEOUT, VERBOSE_LOGGING, MCP_CONFIG_FILE
from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.core.cli import CLIHandler, setup_readline, config_main, mcp_config_generate_main
from mini_cursor.prompt import system_prompt

import os
import platform

# 获取操作系统版本
os_version = platform.platform()

# 获取shell路径
shell_path = os.environ.get('SHELL', '未知')


async def chat_loop(client, cli_handler, workspace):
    """运行交互式聊天循环"""
    cli_handler.print_welcome_message()

    while True:
        try:
            # 使用增强的输入方法
            query = cli_handler.get_input()
            
            if not query:
                print("Please enter a query. Empty input is not allowed.")
                continue
                
            if query.lower() == 'quit':
                break
            
            # 处理特殊命令
            if query.lower() == 'history':
                client._display_tool_history()
                continue
                
            if query.lower() == 'message history':
                client._display_message_history()
                continue
                
            if query.lower() == 'clear history':
                client.clear_message_history()
                continue
            
            if query.lower() == 'config':
                config_main()
                continue
            if query.lower() == 'mcp-config-generate':
                mcp_config_generate_main()
                continue
            if query.lower() == 'help':
                print("\n可用命令:")
                print("  quit                退出聊天")
                print("  history             查看工具调用历史")
                print("  message history     查看消息历史")
                print("  clear history       清空消息历史")
                print("  servers             查看可用MCP服务器")
                print("  config              修改API参数（写入.env）")
                print("  mcp-config-generate 生成/编辑mcp_config.json")
                print("  help                显示本帮助")
                continue
            
            # 重置Ctrl+C状态
            cli_handler.reset_ctrl_c_status()
                
            await client.process_query(query, system_prompt%(os_version, workspace, shell_path))
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Continuing...")


async def main(workspace=None):
    # 设置readline
    setup_readline()
    
    # 打印版本信息和调试信息
    print(f"{Colors.BOLD}{Colors.CYAN}MCP Terminal Client{Colors.ENDC}")
    print(f"{Colors.CYAN}Python version: {sys.version}{Colors.ENDC}")
    print(f"{Colors.CYAN}OpenAI API Base URL: {OPENAI_BASE_URL}{Colors.ENDC}")
    print(f"{Colors.CYAN}Using model: {OPENAI_MODEL}{Colors.ENDC}")
    print(f"{Colors.CYAN}Tool call timeout: {TOOL_CALL_TIMEOUT}s{Colors.ENDC}")
    print(f"{Colors.CYAN}Verbose logging: {'Enabled' if VERBOSE_LOGGING else 'Disabled'}{Colors.ENDC}")
    print(f"{Colors.CYAN}MCP config file: {MCP_CONFIG_FILE}{Colors.ENDC}")
    
    if workspace is None:
        workspace = os.getcwd()
    client = MCPClient()
    cli_handler = CLIHandler(client)
    
    try:
        await client.connect_to_servers()
        await chat_loop(client, cli_handler, workspace)
    except Exception as e:
        print(f"{Colors.RED}Fatal error: {e}{Colors.ENDC}")
        if VERBOSE_LOGGING:
            traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main()) 