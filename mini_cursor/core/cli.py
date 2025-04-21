import os
import readline
import signal
import sys
from typing import Optional
from dotenv import load_dotenv, set_key

from .config import Colors


def setup_readline():
    """设置readline以改善命令行输入体验"""
    # 历史记录文件
    histfile = os.path.join(os.path.expanduser("~"), ".mcp_history")
    try:
        readline.read_history_file(histfile)
        # 设置历史记录文件大小
        readline.set_history_length(1000)
    except FileNotFoundError:
        pass
    
    # 当程序退出时保存历史记录
    import atexit
    atexit.register(readline.write_history_file, histfile)


class CLIHandler:
    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.ctrl_c_pressed = False
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """设置信号处理程序，用于处理Ctrl+C等中断信号"""
        if os.isatty(sys.stdin.fileno()):
            # 创建命名空间以在回调中修改变量
            self.nonlocal_ns = type('NonLocalNamespace', (), {'ctrl_c_pressed': False})
            signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """处理中断信号（Ctrl+C）"""
        if self.nonlocal_ns.ctrl_c_pressed:
            print("\n[强制退出]")
            os._exit(0)
        else:
            self.nonlocal_ns.ctrl_c_pressed = True
            print("\n[按Ctrl+C再次确认强制退出，或继续等待...]")
            # 5秒后重置状态
            import asyncio
            asyncio.get_event_loop().call_later(5, lambda: setattr(self.nonlocal_ns, 'ctrl_c_pressed', False))
    
    def get_input(self, prompt="\nQuery: ") -> str:
        """获取用户输入的增强方法，支持多行输入"""
        try:
            print(f"{Colors.BOLD}{prompt}{Colors.ENDC}")
            print(f"{Colors.CYAN}(多行输入模式：两次回车结束输入,若要输入大量内容,请将\\n\\n删减){Colors.ENDC}")
            
            lines = []
            while True:
                try:
                    # 使用input()逐行读取，这样不会有大小限制
                    line = input()
                    if not line.strip():  # 空行表示结束输入
                        break
                    lines.append(line)
                except EOFError:  # 处理EOF (Ctrl+D)
                    print("\n检测到EOF，结束输入")
                    break
            
            user_input = "\n".join(lines).strip()
            
            # 如果输入为空，给出提示
            if not user_input:
                print(f"{Colors.YELLOW}输入为空，请重新输入{Colors.ENDC}")
                return self.get_input(prompt)
            
            # 处理特殊命令
            if user_input.lower() == 'history':
                self.mcp_client._display_tool_history()
                return self.get_input(prompt)  # 递归调用以获取实际查询
                
            # 显示可用的MCP服务器
            if user_input.lower() == 'servers':
                self.mcp_client._display_servers()
                return self.get_input(prompt)  # 递归调用以获取实际查询
                
            return user_input
        except KeyboardInterrupt:
            # 处理Ctrl+C
            print("\n输入已取消")
            return self.get_input(prompt)  # 允许用户重新输入，而不是直接退出
    
    def print_welcome_message(self) -> None:
        """打印欢迎信息和基本指令"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        print("Type 'servers' to see available MCP servers and tools.")
        print("Type 'history' to view tool call history.")
        print("Type 'message history' to view conversation history.")
        print("Type 'clear history' to clear conversation history.")
        print("Type 'enable <tool>' or 'disable <tool>' to manage available tools.")
        print("Press Ctrl+C twice to force exit if a command hangs.")
    
    def reset_ctrl_c_status(self) -> None:
        """重置Ctrl+C状态"""
        if hasattr(self, 'nonlocal_ns'):
            self.nonlocal_ns.ctrl_c_pressed = False

CONFIG_VARS = [
    ("OPENAI_BASE_URL", "OpenAI Base URL"),
    ("OPENAI_API_KEY", "OpenAI API Key"),
    ("OPENAI_MODEL", "OpenAI Model"),
]


def config_main():
    """
    交互式参数修改界面，支持将参数写入 .env 文件。
    返回: (bool) 是否更新了配置
    """
    print(f"{Colors.HEADER}参数修改界面 (写入 .env 文件){Colors.ENDC}")
    # 加载现有 .env
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    # 读取 config.py 默认值
    import mini_cursor.core.config as config
    updated = False
    for var, desc in CONFIG_VARS:
        current = os.environ.get(var, getattr(config, var, ""))
        print(f"当前 {desc} ({var}): {Colors.YELLOW}{current}{Colors.ENDC}")
        new_val = input(f"输入新的 {desc}，直接回车跳过: ").strip()
        if new_val:
            set_key(str(env_path), var, new_val)
            print(f"{Colors.GREEN}已更新 {var}{Colors.ENDC}")
            updated = True
    if updated:
        print(f"{Colors.GREEN}.env 文件已更新。{Colors.ENDC}")
    else:
        print(f"{Colors.YELLOW}未做任何更改。{Colors.ENDC}")
    
    return updated

def mcp_config_generate_main():
    """
    交互式生成/编辑 mcp_config.json，自动检测 cursor_mcp_all.py 路径。
    """
    import json
    from pathlib import Path
    import importlib.util
    config_path = Path(__file__).parent / "mcp_config.json"
    # 自动检测 cursor_mcp_all.py 的绝对路径
    def get_cursor_mcp_path():
        spec = importlib.util.find_spec("mini_cursor.core.cursor_mcp_all")
        if spec and spec.origin:
            return spec.origin
        # fallback: 相对路径
        fallback = Path(__file__).parent / "cursor_mcp_all.py"
        return str(fallback.resolve())
    cursor_mcp_py = get_cursor_mcp_path()
    # 读取现有配置
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            try:
                config = json.load(f)
            except Exception:
                config = {"mcpServers": {}}
    else:
        config = {"mcpServers": {}}
    servers = config.get("mcpServers", {})
    print(f"{Colors.HEADER}MCP配置生成/编辑界面{Colors.ENDC}")
    if servers:
        print(f"当前已配置服务器:")
        for name, s in servers.items():
            print(f"- {Colors.CYAN}{name}{Colors.ENDC}: command={s.get('command')}, args={s.get('args')}, env={s.get('env')}")
    else:
        print("暂无服务器配置。")
    while True:
        print(f"\n操作选项: [E]编辑 [A]添加 [D]删除 [S]保存并退出 [Q]退出不保存")
        op = input("选择操作: ").strip().upper()
        if op == "E":
            name = input("输入要编辑的服务器名: ").strip()
            if name not in servers:
                print(f"{Colors.RED}未找到服务器: {name}{Colors.ENDC}"); continue
            s = servers[name]
            for key in ["command", "args", "env"]:
                old = s.get(key, "")
                print(f"当前 {key}: {old}")
                new = input(f"输入新的 {key} (回车跳过，args 输入 'auto' 自动填充): ").strip()
                if new:
                    if key == "args":
                        if new == 'auto':
                            s[key] = [cursor_mcp_py]
                            print(f"已自动填充 args: {s[key]}")
                        else:
                            try:
                                s[key] = json.loads(new)
                            except Exception:
                                print("格式错误，args 应为 JSON 数组，如 [\"xxx.py\"]"); continue
                    elif key == "env":
                        try:
                            s[key] = json.loads(new)
                        except Exception:
                            print("格式错误，env 应为 JSON 对象，如 {\"KEY\":\"VAL\"}"); continue
                    else:
                        s[key] = new
            servers[name] = s
        elif op == "A":
            name = input("新服务器名: ").strip()
            if not name or name in servers:
                print("名称无效或已存在"); continue
            command = input("command: ").strip()
            args = input("args (JSON数组，如 [\"xxx.py\"]，或输入 'auto' 自动填充): ").strip()
            env = input("env (JSON对象，如 {\"KEY\":\"VAL\"}): ").strip()
            try:
                if args == 'auto' or not args:
                    args_val = [cursor_mcp_py]
                    print(f"已自动填充 args: {args_val}")
                else:
                    args_val = json.loads(args)
                env_val = json.loads(env) if env else {}
            except Exception:
                print("args/env 格式错误"); continue
            servers[name] = {"command": command, "args": args_val, "env": env_val}
        elif op == "D":
            name = input("要删除的服务器名: ").strip()
            if name in servers:
                del servers[name]
                print(f"{Colors.GREEN}已删除{name}{Colors.ENDC}")
            else:
                print("未找到")
        elif op == "S":
            config["mcpServers"] = servers
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"{Colors.GREEN}已保存到 {config_path}{Colors.ENDC}")
            break
        elif op == "Q":
            print("退出未保存。"); break
        else:
            print("无效操作。")

def init_main():
    """
    初始化生成 mcp_config.json，command 和 args 自动计算绝对路径，env 中 BOCHAAI_API_KEY 留空。
    """
    import json
    from pathlib import Path
    import importlib.util
    config_path = Path(__file__).parent / "mcp_config.json"
    # 自动检测 cursor_mcp_all.py 的绝对路径
    def get_cursor_mcp_path():
        spec = importlib.util.find_spec("mini_cursor.core.cursor_mcp_all")
        if spec and spec.origin:
            return spec.origin
        fallback = Path(__file__).parent / "cursor_mcp_all.py"
        return str(fallback.resolve())
    def get_mysql_mcp_path():
        spec = importlib.util.find_spec("mini_cursor.core.database_mcp.mysql_mcp")
        if spec and spec.origin:
            return spec.origin
        fallback = Path(__file__).parent / "database_mcp/mysql_mcp.py"
        return str(fallback.resolve())
    def get_clickhouse_mcp_path():
        spec = importlib.util.find_spec("mini_cursor.core.database_mcp.clickhouse_mcp")
        if spec and spec.origin:
            return spec.origin
        fallback = Path(__file__).parent / "database_mcp/clickhouse_mcp.py"
        return str(fallback.resolve())
    cursor_mcp_py = get_cursor_mcp_path()
    mysql_mcp_py = get_mysql_mcp_path()
    clickhouse_mcp_py = get_clickhouse_mcp_path()
    # 生成配置内容
    config = {
        "mcpServers": {
            "cursor_mcp": {
                "command": sys.executable,
                "args": [cursor_mcp_py],
                "env": {
                    "BOCHAAI_API_KEY": "bochaai的api,请进入https://open.bochaai.com/获取api,使模型能够进行web搜索"
                }
            },
            "mysql": {
                "command": sys.executable,
                "args": [mysql_mcp_py],
                "env": {
                    "MYSQL_ENABLED": "true",
                    "MYSQL_HOST": "mysql数据库的ip",
                    "MYSQL_PORT": "mysql数据库的端口",
                    "MYSQL_DATABASE": "mysql数据库的名称",
                    "MYSQL_USERNAME": "mysql数据库的用户名",
                    "MYSQL_PASSWORD": "mysql数据库的密码",
                    "MYSQL_POOL_MINSIZE": "1",
                    "MYSQL_POOL_MAXSIZE": "10",
                    "MYSQL_RESOURCE_DESC_FILE": "mysql数据库的资源描述文件路径"
                }
            },
            "clickhouse": {
                "command": sys.executable,
                "args": [clickhouse_mcp_py],
                "env": {
                    "CLICKHOUSE_ENABLED": "true",
                    "CLICKHOUSE_HOST": "clickhouse数据库的ip",
                    "CLICKHOUSE_PORT": "clickhouse数据库的端口",
                    "CLICKHOUSE_DATABASE": "clickhouse数据库的名称",
                    "CLICKHOUSE_USERNAME": "clickhouse数据库的用户名",
                    "CLICKHOUSE_PASSWORD": "clickhouse数据库的密码",
                    "CLICKHOUSE_RESOURCE_DESC_FILE": "clickhouse数据库的资源描述文件路径"
                    }
            }
        }
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    print(f"{Colors.GREEN}已生成初始化 mcp_config.json 于 {config_path}{Colors.ENDC}") 