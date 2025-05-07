#!/usr/bin/env python3

import asyncio
import sys
import traceback
import signal
import os
import platform

from mini_cursor.core.config import Colors, OPENAI_BASE_URL, OPENAI_MODEL, TOOL_CALL_TIMEOUT, VERBOSE_LOGGING, MCP_CONFIG_FILE
from mini_cursor.core.mcp_client import MCPClient
from mini_cursor.core.cli import CLIHandler, setup_readline, config_main, mcp_config_generate_main

prompt_path=os.path.join(os.path.dirname(__file__), 'data', 'system_prompt.txt')
system_prompt=open(prompt_path, 'r', encoding='utf-8').read()
# 获取操作系统版本
os_version = platform.platform()

# 获取shell路径
shell_path = os.environ.get('SHELL', '未知')

# 全局变量，用于信号处理程序
shutdown_event = None
client = None

# 自定义信号处理程序
def setup_signal_handlers():
    def graceful_exit_handler(sig, frame):
        print("\n\n正在优雅退出，请稍候...(这可能需要几秒钟)")
        if shutdown_event:
            shutdown_event.set()
    
    # 设置SIGINT (Ctrl+C) 处理器
    signal.signal(signal.SIGINT, graceful_exit_handler)
    
    # 设置SIGTERM处理器
    signal.signal(signal.SIGTERM, graceful_exit_handler)


async def chat_loop(client, cli_handler, workspace):
    """运行交互式聊天循环"""
    global shutdown_event
    shutdown_event = asyncio.Event()
    
    cli_handler.print_welcome_message()

    while not shutdown_event.is_set():
        try:
            # 使用增强的输入方法, 带超时以便可以检查shutdown_event
            # 创建一个任务来获取用户输入
            input_task = asyncio.create_task(asyncio.to_thread(cli_handler.get_input))
            
            # 等待用户输入或者shutdown_event被设置
            done, pending = await asyncio.wait(
                [input_task, asyncio.create_task(shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 如果shutdown_event被设置，取消输入任务并退出
            if shutdown_event.is_set():
                for task in pending:
                    task.cancel()
                break
            
            # 获取用户输入
            query = input_task.result() if input_task in done else ""
            
            # 检查输入是否为空
            if not query or not query.strip():
                print(f"{Colors.YELLOW}请输入有效的查询。空输入不被允许。{Colors.ENDC}")
                continue
                
            if query.lower() == 'quit':
                print("\n退出中，正在清理资源...")
                shutdown_event.set()
                break
            
            # 处理特殊命令
            if query.lower() == 'history':
                client.display_tool_history()
                continue
                
            if query.lower() == 'message history':
                client.display_message_history()
                continue
                
            if query.lower() == 'clear history':
                client.clear_message_history()
                continue
                
            if query.lower() == 'servers':
                client.display_servers()
                continue
            
            if query.lower() == 'config':
                config_updated = config_main()
                if config_updated:
                    print(f"{Colors.CYAN}配置已更新，正在重新加载...{Colors.ENDC}")
                    client.update_config()
                    # 显示当前模型是否为支持思考的模型
                    current_model = os.environ.get("OPENAI_MODEL", "").lower()
                    if "deepseek-r1" in current_model:
                        print(f"{Colors.GREEN}当前使用的是支持思考过程显示的模型: {current_model}{Colors.ENDC}")
                continue
                
            if query.lower() == 'mcp-config':
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
                print("  mcp-config          生成/编辑mcp_config.json")
                print("  help                显示本帮助")
                print("\n工具管理命令:")
                print("  enable <tool>       启用特定工具")
                print("  disable <tool>      禁用特定工具")
                print("  enable-all          启用所有工具")
                print("  disable-all         禁用所有工具")
                print("  mode <all|selective> 设置工具启用模式")
                continue
            
            # 处理工具管理命令
            if query.lower().startswith('enable ') and len(query.split()) >= 2:
                tool_name = query.split(None, 1)[1].strip()
                client.enable_tool(tool_name)
                continue
                
            if query.lower().startswith('disable ') and len(query.split()) >= 2:
                tool_name = query.split(None, 1)[1].strip()
                client.disable_tool(tool_name)
                continue
                
            if query.lower() == 'enable-all':
                client.enable_all_tools()
                print(f"{Colors.GREEN}已启用所有工具{Colors.ENDC}")
                continue
                
            if query.lower() == 'disable-all':
                client.disable_all_tools()
                print(f"{Colors.GREEN}已禁用所有工具{Colors.ENDC}")
                continue
                
            if query.lower().startswith('mode ') and len(query.split()) >= 2:
                mode = query.split(None, 1)[1].strip().lower()
                if mode in ['all', 'selective']:
                    client.set_tool_enablement_mode(mode)
                else:
                    print(f"{Colors.RED}无效的模式: {mode}. 必须是 'all' 或 'selective'{Colors.ENDC}")
                continue
            
            # 重置Ctrl+C状态
            cli_handler.reset_ctrl_c_status()
            
            # 处理实际查询
            try:
                # 输入可能很长，先显示一下要处理的输入内容
                if len(query) > 500:
                    lines = query.count('\n') + 1
                    print(f"\n{Colors.CYAN}正在处理您的输入 ({len(query)} 字符, {lines} 行)...{Colors.ENDC}")
                
                await client.process_query(query, system_prompt)
            except Exception as e:
                print(f"\n{Colors.RED}处理查询时出错: {e}{Colors.ENDC}")
                if VERBOSE_LOGGING:
                    traceback.print_exc()
            
        except KeyboardInterrupt:
            print("\n退出中，正在清理资源...")
            shutdown_event.set()
            break
        except asyncio.CancelledError:
            # 任务被取消，优雅退出
            break
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")
            if VERBOSE_LOGGING:
                traceback.print_exc()
            print("Continuing...")


async def main(workspace=None):
    global client
    # 设置readline
    setup_readline()
    
    # 设置信号处理
    setup_signal_handlers()
    
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
        if client:
            print("\n正在关闭所有连接和资源...")
            await client.close()
            print(f"{Colors.GREEN}已安全退出，再见！{Colors.ENDC}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 如果在asyncio.run期间收到Ctrl+C，确保干净退出
        print("\n程序被中断，强制退出。")
    except Exception as e:
        print(f"{Colors.RED}未处理的异常: {e}{Colors.ENDC}")
        if VERBOSE_LOGGING:
            traceback.print_exc() 