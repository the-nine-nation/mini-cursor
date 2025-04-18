from mini_cursor.core.config import Colors

def display_tool_history(tool_history):
    """显示工具调用历史"""
    if not tool_history:
        print(f"{Colors.YELLOW}No tool call history available{Colors.ENDC}")
        return
        
    print(f"\n{Colors.BOLD}{Colors.CYAN}===== Tool Call History ====={Colors.ENDC}")
    for i, record in enumerate(tool_history, 1):
        status = f"{Colors.GREEN}✓{Colors.ENDC}" if record["success"] else f"{Colors.RED}✗{Colors.ENDC}"
        server = record.get("server", "unknown")
        print(f"{i}. [{status}] {record['timestamp']} - {server}/{record['tool']}")
        if 'duration' in record:
            print(f"   Duration: {record['duration']:.2f}s")
        if not record["success"] and record["error"]:
            print(f"   {Colors.RED}Error: {record['error']}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 30}{Colors.ENDC}")

def display_servers(server_tools):
    """显示连接的MCP服务器和它们的工具"""
    if not server_tools:
        print(f"{Colors.YELLOW}No MCP servers connected{Colors.ENDC}")
        return
        
    print(f"\n{Colors.BOLD}{Colors.CYAN}===== Connected MCP Servers ====={Colors.ENDC}")
    for server_name, tools in server_tools.items():
        print(f"{Colors.BOLD}{server_name}{Colors.ENDC} ({len(tools)} tools)")
        for tool_name in sorted(tools.keys()):
            tool = tools[tool_name]
            print(f"  • {Colors.YELLOW}{tool_name}{Colors.ENDC}: {tool.description[:60]}...")
    print(f"{Colors.CYAN}{'=' * 30}{Colors.ENDC}")

def display_message_history(message_history):
    """显示当前的消息历史"""
    if not message_history:
        print(f"{Colors.YELLOW}No message history available{Colors.ENDC}")
        return
        
    print(f"\n{Colors.BOLD}{Colors.CYAN}===== Message History ({len(message_history)} messages) ====={Colors.ENDC}")
    for i, msg in enumerate(message_history):
        role = msg["role"]
        # 根据角色使用不同颜色
        if role == "system":
            role_color = f"{Colors.MAGENTA}system{Colors.ENDC}"
        elif role == "user":
            role_color = f"{Colors.GREEN}user{Colors.ENDC}"
        elif role == "assistant":
            role_color = f"{Colors.BLUE}assistant{Colors.ENDC}"
        elif role == "tool":
            role_color = f"{Colors.YELLOW}tool{Colors.ENDC}"
        else:
            role_color = role
            
        # 消息内容截断显示
        content = msg.get("content", "")
        if content and len(content) > 60:
            content = content[:57] + "..."
            
        print(f"{i+1}. [{role_color}] {content}")
    print(f"{Colors.CYAN}{'=' * 30}{Colors.ENDC}")
    print(f"Use '{Colors.BOLD}clear history{Colors.ENDC}' to clear the conversation history.") 