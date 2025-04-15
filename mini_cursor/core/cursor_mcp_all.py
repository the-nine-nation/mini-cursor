import os
import sys
import re
import logging
import json
import asyncio
from typing import Dict, Any, List, Tuple, TypedDict, Optional, Union, Literal, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import traceback
import requests

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchResult(TypedDict):
    file_path: str
    line_number: int
    line_content: str
    match_score: float

class EditResult(TypedDict, total=False):
    success: bool
    message: str
    original_lines: int
    modified_lines: int

@dataclass
class FileCache:
    dir_listing_cache: Dict[str, Tuple[float, List[str]]] = field(default_factory=dict)
    file_content_cache: Dict[str, Tuple[float, List[str]]] = field(default_factory=dict)
    non_text_files: Set[str] = field(default_factory=set)
    cache_ttl: int = 300

@dataclass
class AppContext:
    file_cache: FileCache = field(default_factory=FileCache)

# --- Utility functions (unchanged) ---
def is_binary_file(file_path: str) -> bool:
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            if b'\x00' in chunk:
                return True
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
    except (IOError, PermissionError):
        return True

def get_comment_marker(file_ext: str) -> str:
    comment_markers = {
        '.js': '//', '.ts': '//', '.jsx': '//', '.tsx': '//', '.c': '//', '.cpp': '//', '.cs': '//', '.java': '//', '.swift': '//', '.kt': '//', '.go': '//', '.rs': '//', '.scala': '//',
        '.py': '#', '.rb': '#', '.pl': '#', '.sh': '#', '.bash': '#', '.r': '#', '.yaml': '#', '.yml': '#', '.toml': '#',
        '.html': '<!--', '.xml': '<!--', '.svg': '<!--',
        '.sql': '--', '.lisp': ';;', '.clj': ';;', '.lua': '--', '.hs': '--', '.vb': "'"
    }
    return comment_markers.get(file_ext, '//')

def apply_edits(original_content: str, segments: List[str], placeholder_pattern: str) -> str:
    if len(segments) == 1:
        return segments[0]
    result = []
    last_pos = 0
    original_lines = original_content.splitlines()
    first_segment = segments[0]
    first_segment_lines = first_segment.splitlines()
    if first_segment_lines:
        match_pos = original_content.find(first_segment)
        if match_pos >= 0:
            result.append(original_content[:match_pos])
            result.append(first_segment)
            last_pos = match_pos + len(first_segment)
        else:
            result.append(first_segment)
    for i in range(1, len(segments)):
        curr_segment = segments[i]
        curr_lines = curr_segment.splitlines() if curr_segment else []
        if not curr_lines:
            continue
        match_pos = original_content.find(curr_segment, last_pos)
        if match_pos >= 0:
            result.append(original_content[last_pos:match_pos])
            result.append(curr_segment)
            last_pos = match_pos + len(curr_segment)
        else:
            context_found = False
            if len(curr_lines) > 1:
                first_line = curr_lines[0].strip()
                if len(first_line) > 5:
                    for i, line in enumerate(original_lines):
                        if first_line in line and i * len(line) > last_pos:
                            approx_pos = original_content.find(line, last_pos)
                            if approx_pos >= 0:
                                result.append(original_content[last_pos:approx_pos])
                                result.append(curr_segment)
                                last_pos = approx_pos + len(line) + 1
                                context_found = True
                                break
            if not context_found:
                result.append(curr_segment)
    if last_pos < len(original_content):
        result.append(original_content[last_pos:])
    return "".join(result)

def get_file_paths(directory_path: str, file_cache: FileCache, max_files: int = 10000) -> List[str]:
    import time
    now = time.time()
    if directory_path in file_cache.dir_listing_cache:
        cache_time, file_paths = file_cache.dir_listing_cache[directory_path]
        if now - cache_time < file_cache.cache_ttl:
            return file_paths
    file_paths = []
    file_count = 0
    for root, _, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_paths.append(file_path)
            file_count += 1
            if file_count >= max_files:
                logger.warning(f"Reached maximum file count ({max_files}), stopping directory traversal")
                break
        if file_count >= max_files:
            break
    file_cache.dir_listing_cache[directory_path] = (now, file_paths)
    return file_paths

def get_file_content(file_path: str, file_cache: FileCache) -> Optional[List[str]]:
    import time
    now = time.time()
    if file_path in file_cache.non_text_files:
        return None
    if file_path in file_cache.file_content_cache:
        cache_time, lines = file_cache.file_content_cache[file_path]
        try:
            mtime = os.path.getmtime(file_path)
            if mtime <= cache_time:
                return lines
        except (OSError, IOError):
            return lines if now - cache_time < file_cache.cache_ttl else None
    if is_binary_file(file_path):
        file_cache.non_text_files.add(file_path)
        return None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            file_cache.file_content_cache[file_path] = (now, lines)
            return lines
    except (UnicodeDecodeError, PermissionError, IsADirectoryError, IOError):
        file_cache.non_text_files.add(file_path)
        return None

def calculate_match_score(text: str, patterns: List[re.Pattern], boost_all_keywords: bool = True) -> float:
    match_counts = [len(pattern.findall(text)) for pattern in patterns]
    score = sum(match_counts)
    if boost_all_keywords and all(count > 0 for count in match_counts) and len(patterns) > 1:
        score *= 2
    return score

def search_file_content(directory_path: str, keywords: List[str], top_k: int, file_cache: FileCache) -> List[SearchResult]:
    results = []
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        return []
    patterns = [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]
    file_paths = get_file_paths(directory_path, file_cache)
    for file_path in file_paths:
        lines = get_file_content(file_path, file_cache)
        if lines is None:
            continue
        for line_number, line in enumerate(lines, 1):
            if any(pattern.search(line) for pattern in patterns):
                score = calculate_match_score(line, patterns)
                results.append({
                    "file_path": file_path,
                    "line_number": line_number,
                    "line_content": line.strip(),
                    "match_score": score
                })
    results = sorted(results, key=lambda x: x["match_score"], reverse=True)
    return results[:top_k]

# --- MCP Server Setup ---
app_context = AppContext()
server = Server("cursor-mcp-all")

# 用于缓存每个文件的上一次 edit 操作参数
last_edit_cache: dict[str, dict] = {}

# 从 JSON 文件加载 tool_specs
with open(os.path.join(os.path.dirname(__file__), 'tool_specs.json'), 'r', encoding='utf-8') as f:
    tool_specs = json.load(f)

# --- Tool Implementations ---
async def tool_read_file(args: dict) -> str:
    target_file = args["target_file"]
    should_read_entire_file = args.get("should_read_entire_file", False)
    start_line = args.get("start_line_one_indexed", 1)
    end_line = args.get("end_line_one_indexed_inclusive", 1)
    try:
        if not os.path.exists(target_file):
            return f"Error: File '{target_file}' does not exist."
        with open(target_file, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
        total_lines = len(all_lines)
        if should_read_entire_file:
            start = 0
            end = total_lines
        else:
            # 转换为Python下标
            start = max(0, start_line - 1)
            end = min(end_line, total_lines)
        lines_to_read = all_lines[start:end]
        response_parts = [
            f"File: {target_file}",
            f"Total lines: {total_lines}",
        ]
        if should_read_entire_file:
            response_parts.append(f"Reading entire file\n")
        else:
            response_parts.append(f"Reading lines {start+1} to {end} (inclusive)\n")
        if start > 0 and not should_read_entire_file:
            response_parts.append(f"[... {start} lines before this ...]")
        content = "".join(lines_to_read)
        response_parts.append(content)
        if end < total_lines and not should_read_entire_file:
            remaining_lines = total_lines - end
            response_parts.append(f"[... {remaining_lines} more lines ...]")
        return "\n".join(response_parts)
    except Exception as e:
        return f"Error reading file: {str(e)}\n{traceback.format_exc()}"

async def tool_edit_file(args: dict) -> str:
    try:
        target_file = args["target_file"]
        instructions = args["instructions"]
        code_edit = args["code_edit"]
    except KeyError as e:
        return f"Error: Missing required parameter: {e.args[0]}"
    try:
        if not os.path.exists(target_file):
            return f"Error: File '{target_file}' does not exist."
        with open(target_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        file_ext = os.path.splitext(target_file)[1].lower()
        comment_marker = get_comment_marker(file_ext)
        placeholder_pattern = f"{comment_marker} \.\.\. existing code \.\.\."
        segments = re.split(placeholder_pattern, code_edit)
        segments = [s.strip() for s in segments]
        new_content = apply_edits(original_content, segments, placeholder_pattern)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        # 缓存本次 edit 操作参数
        last_edit_cache[target_file] = {
            "target_file": target_file,
            "instructions": instructions,
            "code_edit": code_edit
        }
        return f"Successfully edited '{target_file}'.\nInstructions: {instructions}"
    except Exception as e:
        return f"Error editing file: {str(e)}\n{traceback.format_exc()}"

async def tool_search_files(args: dict) -> str:
    query = args["query"]
    explanation = args["explanation"]
    try:
        # 在当前工作区递归查找所有文件
        matches = []
        root_dir = os.getcwd()
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(dirpath, filename), root_dir)
                if query.lower() in rel_path.lower():
                    matches.append(rel_path)
                    if len(matches) >= 10:
                        break
            if len(matches) >= 10:
                break
        if not matches:
            return f"No files found matching query '{query}'.\nExplanation: {explanation}"
        result = [f"Fuzzy file search results for '{query}': (showing up to 10 results)", f"Explanation: {explanation}"]
        for i, path in enumerate(matches, 1):
            result.append(f"{i}. {path}")
        return "\n".join(result)
    except Exception as e:
        return f"Error searching files: {str(e)}\n{traceback.format_exc()}"

async def tool_terminal_command(args: dict) -> str:
    command = args["command"]
    is_background = args["is_background"]
    explanation = args.get("explanation", "")
    try:
        logger.info(f"Running command: {command}")
        if explanation:
            logger.info(f"Explanation: {explanation}")
        dangerous_patterns = [
            r"^\s*rm\s+(-rf?|--recursive|--force)\s+(/|~|/home)",
            r"^\s*:\(\){ :\|:& };:",
            r"^\s*dd\s+.*\s+of=/dev/"
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return f"Error: The command '{command}' looks potentially harmful and has been blocked."
        if is_background:
            modified_cmd = f"nohup {command} > /tmp/mcp_cmd_output.log 2>&1 &"
            proc = await asyncio.create_subprocess_shell(
                modified_cmd, 
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return f"Command started in background: {command}"
        else:
            proc = await asyncio.create_subprocess_shell(
                command, 
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace')
            if proc.returncode != 0:
                return f"Command failed with exit code {proc.returncode}:\n\nSTDOUT:\n{output}\n\nSTDERR:\n{error}"
            else:
                return f"Command succeeded:\n\n{output}"
    except Exception as e:
        return f"Error executing command: {str(e)}\n{traceback.format_exc()}"

async def tool_reapply(args: dict) -> str:
    target_file = args.get("target_file")
    if not target_file:
        return "Error: Missing required parameter: target_file"
    if not os.path.exists(target_file):
        return f"Error: File '{target_file}' does not exist."
    # 查找上一次 edit 操作参数
    last_args = last_edit_cache.get(target_file)
    if not last_args:
        return f"No previous edit found for '{target_file}'."
    # 重新应用 edit 操作
    result = await tool_edit_file(last_args)
    return f"Reapplied last edit for '{target_file}':\n{result}"

async def tool_list_dir(args: dict) -> str:
    relative_path = args.get("relative_workspace_path")
    explanation = args.get("explanation", "")
    if not relative_path:
        return "Error: Missing required parameter: relative_workspace_path"
    abs_path = os.path.abspath(relative_path)
    if not os.path.exists(abs_path):
        return f"Error: Path '{relative_path}' does not exist."
    if not os.path.isdir(abs_path):
        return f"Error: Path '{relative_path}' is not a directory."
    try:
        entries = os.listdir(abs_path)
        entries.sort()
        result = [f"Directory listing for '{relative_path}':", f"Explanation: {explanation}"]
        if not entries:
            result.append("(Empty directory)")
        else:
            for entry in entries:
                entry_path = os.path.join(abs_path, entry)
                if os.path.isdir(entry_path):
                    result.append(f"[DIR]  {entry}")
                else:
                    result.append(f"      {entry}")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {str(e)}\n{traceback.format_exc()}"

async def tool_web_search(args: dict) -> str:
    query = args.get("query")
    summary = args.get("summary", True)
    count = args.get("count", 10)
    page = args.get("page", 1)
    if not query:
        return "Error: Missing required parameter: query"
    try:
        url = "https://api.bochaai.com/v1/web-search"
        payload = json.dumps({
            "query": query,
            "summary": summary,
            "count": count,
            "page": page
        })
        api_key = os.environ.get("BOCHAAI_API_KEY")
        if not api_key:
            return "Error: BOCHAAI_API_KEY environment variable not set."
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        result = response.json()
        return json.dumps(result, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Search API error: {str(e)}"}, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False, indent=2)

# --- MCP Handlers ---
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=spec["name"],
            description=spec["description"],
            inputSchema=spec["inputSchema"],
        ) for spec in tool_specs
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    try:
        if name == "read_file":
            result = await tool_read_file(arguments or {})
        elif name == "edit_file":
            result = await tool_edit_file(arguments or {})
        elif name == "search_files":
            result = await tool_search_files(arguments or {})
        elif name == "terminal_command":
            result = await tool_terminal_command(arguments or {})
        elif name == "reapply":
            result = await tool_reapply(arguments or {})
        elif name == "list_dir":
            result = await tool_list_dir(arguments or {})
        elif name == "web_search":
            result = await tool_web_search(arguments or {})
        else:
            result = f"Unknown tool: {name}"
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# --- Main entry ---
async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Cursor MCP server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="cursor-mcp-all",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
