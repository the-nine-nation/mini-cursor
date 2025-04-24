import click
import asyncio
import os
import webbrowser
import subprocess
import time
import signal
import sys
from mini_cursor.core.cli import config_main, mcp_config_generate_main, init_main
from mini_cursor.mcp_qa import main as qa_main
from rich.console import Console
from rich.table import Table
import shutil
from pathlib import Path

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
    # 提示用户可以开启详细调试
    print("提示: 设置环境变量 DEBUG_CHUNKS=1 可以显示详细的响应结构（用于调试）")
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
def web():
    """启动Web界面并在浏览器中打开"""
    console = Console()
    init_main()
    # 检查static目录是否存在
    package_dir = Path(__file__).parent
    static_dir = package_dir / 'static'
    
    if not static_dir.exists() or not (static_dir / 'js').exists() or not (static_dir / 'css').exists():
        console.print("[bold red]错误: 找不到静态资源目录![/bold red]")
        console.print("[yellow]这可能是由于pip安装时未正确包含静态文件导致的。[/yellow]")
        
        # 查找可能的替代位置
        alt_locations = [
            Path(package_dir).parent / 'mini_cursor' / 'static',  # 开发环境
            Path(sys.prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'mini_cursor' / 'static',  # 系统安装
        ]
        
        found = False
        for loc in alt_locations:
            if loc.exists():
                console.print(f"[green]找到替代静态资源目录: {loc}[/green]")
                # 复制文件到正确位置
                shutil.copytree(loc, static_dir, dirs_exist_ok=True)
                console.print("[green]已复制静态资源文件[/green]")
                found = True
                break
        
        if not found:
            console.print("[bold red]无法找到静态资源文件，Web界面可能无法正常运行。[/bold red]")
            console.print("[yellow]请考虑重新安装mini-cursor或从源代码运行。[/yellow]")
            # 继续尝试启动服务器，可能只是部分功能受限
    
    # 设置Web服务器端口
    port = int(os.environ.get("PORT", 7727))
    host = os.environ.get("HOST", "0.0.0.0")
    url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}/demo"
    
    console.print(f"[bold green]正在启动Web服务器...[/bold green]")
    
    # 启动Web服务器进程
    server_process = subprocess.Popen(
        [sys.executable, "-m", "mini_cursor.api.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务器启动
    console.print("[yellow]等待服务器启动中...[/yellow]")
    time.sleep(2)  # 给服务器一些启动时间
    
    # 检查服务器是否正常启动
    if server_process.poll() is not None:
        console.print("[bold red]服务器启动失败！[/bold red]")
        stdout, stderr = server_process.communicate()
        console.print(f"[red]错误信息: {stderr}[/red]")
        return
    
    # 在浏览器中打开Web界面
    console.print(f"[bold green]正在浏览器中打开Web界面: {url}[/bold green]")
    webbrowser.open(url)
    
    console.print("[yellow]Web服务器正在运行。按Ctrl+C停止服务器...[/yellow]")
    
    # 等待用户中断
    try:
        # 将服务器输出重定向到控制台
        while True:
            output = server_process.stdout.readline()
            if output:
                print(output.strip())
            if server_process.poll() is not None:
                break
    except KeyboardInterrupt:
        console.print("[bold yellow]正在停止Web服务器...[/bold yellow]")
        # 发送SIGTERM信号给进程（优雅关闭）
        server_process.send_signal(signal.SIGTERM)
        server_process.wait(timeout=5)  # 给服务器一些关闭时间
        console.print("[bold green]Web服务器已停止[/bold green]")

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
        ("web", "启动Web界面并在浏览器中打开"),
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