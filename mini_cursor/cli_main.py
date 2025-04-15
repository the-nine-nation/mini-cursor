import click
import asyncio
import os
from mini_cursor.core.cli import config_main, mcp_config_generate_main, init_main
from mini_cursor.mcp_qa import main as qa_main
from rich.console import Console
from rich.table import Table

@click.group()
def cli():
    """mini-cursor 命令行工具"""
    pass

@cli.command()
def config():
    """参数修改界面 (写入 .env 文件)"""
    config_main()

@cli.command('mcp-config')
def mcp_config():
    """生成/编辑 mcp_config.json"""
    mcp_config_generate_main()

@cli.command()
def chat():
    """进入聊天模式"""
    workspace = os.getcwd()
    asyncio.run(qa_main(workspace=workspace))

@cli.command()
def init():
    """初始化生成 mcp_config.json"""
    init_main()

@cli.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell):
    """生成自动补全脚本（bash/zsh/fish）"""
    import sys
    from click.shell_completion import get_completion_script
    prog_name = "mini-cursor"
    script = get_completion_script(cli, prog_name, shell)
    sys.stdout.write(script)

@cli.command()
def help():
    """显示所有可用命令及简要说明"""
    console = Console()
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("命令", style="cyan", no_wrap=True)
    table.add_column("说明", style="white")
    commands = [
        ("config", "参数修改界面 (写入 .env 文件)"),
        ("mcp-config", "生成/编辑 mcp_config.json"),
        ("chat", "进入聊天模式"),
        ("init", "初始化生成 mcp_config.json"),
        ("completion", "生成自动补全脚本 (bash/zsh/fish)"),
        ("help", "显示所有可用命令及简要说明")
    ]
    console.print("[bold green]mini-cursor 命令一览[/bold green]")
    console.print("[dim]------------------------------[/dim]")
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    console.print(table)
    console.print("[dim]------------------------------[/dim]")
    console.print("[yellow]提示：可用 Tab 补全命令，或用 mini-cursor completion 生成补全脚本！[/yellow]")

if __name__ == '__main__':
    cli() 