import os
import sys
import logging
import json
import asyncio
import traceback
from typing import Dict, Any, List, Optional, TypedDict, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from typing import AsyncIterator

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Import database drivers
try:
    from clickhouse_driver import Client as ClickHouseClient
    CLICKHOUSE_NATIVE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_NATIVE_AVAILABLE = False

try:
    import requests
    CLICKHOUSE_HTTP_AVAILABLE = True
except ImportError:
    CLICKHOUSE_HTTP_AVAILABLE = False

CLICKHOUSE_AVAILABLE = CLICKHOUSE_NATIVE_AVAILABLE or CLICKHOUSE_HTTP_AVAILABLE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 从环境变量读取数据库连接配置
DB_CONFIG = {
    "enabled": os.environ.get("CLICKHOUSE_ENABLED", "false").lower() == "true",
    "host": os.environ.get("CLICKHOUSE_HOST", "localhost"),
    "port": int(os.environ.get("CLICKHOUSE_PORT", "9000")),
    "http_port": int(os.environ.get("CLICKHOUSE_HTTP_PORT", "8123")),
    "database": os.environ.get("CLICKHOUSE_DATABASE", "default"),
    "username": os.environ.get("CLICKHOUSE_USERNAME", "default"),
    "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
    "use_http": os.environ.get("CLICKHOUSE_USE_HTTP", "auto").lower(),  # "true", "false", or "auto"
    "max_rows": int(os.environ.get("CLICKHOUSE_MAX_ROWS", "10")),  # 默认每次查询最多返回10行
    "resource_desc_file": os.environ.get("CLICKHOUSE_RESOURCE_DESC_FILE", ""),  # 资源描述文件路径（必需）
}


@dataclass
class DatabaseConnection:
    connection: Any  # The actual database connection object
    database: str
    connection_type: str  # "native" or "http"
    last_used: float = field(default_factory=lambda: 0)
    
@dataclass
class AppContext:
    connection: Optional[DatabaseConnection] = None
    connection_ttl: int = 3600  # 1 hour

# --- MCP Server Setup ---
app_context = AppContext()
server = Server("clickhouse-mcp")

# 从文件加载资源描述
def load_resource_description():
    """从文件加载资源描述，文件路径必须指定"""
    file_path = DB_CONFIG["resource_desc_file"]
    if not file_path:
        logger.error("Resource description file path (CLICKHOUSE_RESOURCE_DESC_FILE) is required but not specified")
        sys.exit(1)
        
    if not os.path.isfile(file_path):
        logger.error(f"Resource description file {file_path} does not exist")
        sys.exit(1)
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                logger.error(f"Resource description file {file_path} is empty")
                sys.exit(1)
            logger.info(f"Loaded resource description from {file_path}")
            return content
    except Exception as e:
        logger.error(f"Error reading resource description file {file_path}: {e}")
        sys.exit(1)

clickhouse_resource_description = load_resource_description()

# Define tool specifications
tool_specs = [
    {
        "name": "clickhouse_execute_read_query",
        "description": "Execute read-only ClickHouse SQL code. Only SELECT, SHOW, DESCRIBE, EXPLAIN allowed; queries are validated before execution."+clickhouse_resource_description,
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The SQL code to execute (only SELECT, SHOW, DESCRIBE, EXPLAIN allowed)"
                },
                "params": {
                    "type": "object",
                    "description": "Parameters for the SQL query (for parameterized queries)",
                    "additionalProperties": True
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum number of rows to return",
                    "default": DB_CONFIG["max_rows"]
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "clickhouse_get_table_schema",
        "description": "Get the schema for a specific ClickHouse table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The name of the table to get schema for"
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum number of rows to return",
                    "default": DB_CONFIG["max_rows"]
                }
            },
            "required": ["table_name"]
        }
    }
]

# --- ClickHouse HTTP Client ---
def execute_http_query(host, port, database, query, username, password, params=None, max_rows=None):
    """通过HTTP接口执行ClickHouse查询"""
    if max_rows is None:
        max_rows = DB_CONFIG["max_rows"]
        
    url = f"http://{host}:{port}/"
    
    # 添加只读标志和数据库名称
    params_dict = {
        "readonly": "1",
        "database": database,
        "default_format": "JSONCompact"  # 使用JSON格式响应
    }
    
    # 添加认证信息
    auth = None
    if username:
        if password:
            auth = (username, password)
        else:
            params_dict["user"] = username
    
    try:
        response = requests.post(url, params=params_dict, data=query, auth=auth)
        response.raise_for_status()
        
        # 解析JSON响应
        result = response.json()
        
        # 处理结果
        if "data" in result:
            rows = result.get("data", [])
            column_names = []
            
            # 从meta字段获取列名
            if "meta" in result:
                column_names = [col.get("name") for col in result.get("meta", [])]
            elif rows and len(rows) > 0:
                # 如果没有meta，从第一行获取列名
                column_names = list(rows[0].keys())
                
            return {
                "success": True,
                "data": rows[:max_rows],
                "error": None,
                "row_count": len(rows),
                "column_names": column_names
            }
        else:
            return {
                "success": True,
                "data": [],
                "error": None,
                "row_count": 0,
                "column_names": []
            }
    except Exception as e:
        logger.error(f"HTTP query error: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "row_count": 0,
            "column_names": []
        }

# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan() -> AsyncIterator[None]:
    """Manage application lifecycle with database connection."""
    conn = None
    if DB_CONFIG["enabled"]:
        config = DB_CONFIG
        use_http = config["use_http"]
        
        # 确定使用哪种连接方式
        if use_http == "auto":
            # 优先使用HTTP接口，如果不可用则尝试原生接口
            use_http = "true" if CLICKHOUSE_HTTP_AVAILABLE else "false"
            logger.info(f"Auto-selecting connection mode: {'HTTP' if use_http == 'true' else 'Native'}")

        try:
            if use_http == "true" and CLICKHOUSE_HTTP_AVAILABLE:
                # 测试HTTP连接
                logger.info(f"Connecting to ClickHouse via HTTP on {config['host']}:{config['http_port']}")
                test_result = execute_http_query(
                    config["host"], 
                    config["http_port"], 
                    config["database"], 
                    "SELECT 1", 
                    config["username"], 
                    config["password"]
                )
                
                if test_result["success"]:
                    logger.info(f"Connected to ClickHouse via HTTP at {config['host']}:{config['http_port']}")
                    conn = DatabaseConnection(
                        connection=None,  # HTTP模式不需要持久连接
                        database=config["database"],
                        connection_type="http"
                    )
                else:
                    logger.error(f"Failed to connect to ClickHouse via HTTP: {test_result.get('error')}")
            
            elif CLICKHOUSE_NATIVE_AVAILABLE:
                # 使用原生客户端
                logger.info(f"Connecting to ClickHouse via native protocol on {config['host']}:{config['port']}")
                client = ClickHouseClient(
                    host=config["host"],
                    port=config["port"],
                    database=config["database"],
                    user=config["username"],
                    password=config["password"],
                    settings={'readonly': 1}  # 强制只读模式
                )
                client.execute("SELECT 1")  # Test connection
                logger.info(f"Connected to ClickHouse via native protocol at {config['host']}:{config['port']}")
                conn = DatabaseConnection(
                    connection=client,
                    database=config["database"],
                    connection_type="native"
                )
            else:
                logger.error("Neither ClickHouse HTTP nor native connection is available. Install clickhouse-driver or requests package.")
            
            app_context.connection = conn
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse during startup: {e}")
            app_context.connection = None # Ensure connection is None if setup fails

    try:
        yield # Server runs here
    finally:
        # Cleanup on shutdown
        if app_context.connection:
            logger.info(f"Closing ClickHouse {app_context.connection.connection_type} connection")
            
            if app_context.connection.connection_type == "native" and app_context.connection.connection:
                try:
                    # ClickHouse native client's cleanup
                    # Close underlying socket if available
                    client = app_context.connection.connection
                    
                    # 尝试关闭底层网络连接
                    if hasattr(client, 'disconnect'):
                        client.disconnect()
                    elif hasattr(client, 'connection') and hasattr(client.connection, 'socket'):
                        client.connection.socket.close()
                    
                    logger.info("ClickHouse native connection closed")
                except Exception as e:
                    logger.error(f"Error closing ClickHouse native connection: {e}")
            
            # 确保连接对象被清除
            app_context.connection = None
            logger.info("ClickHouse connection cleanup completed")

# --- Connection Management Functions ---

def get_connection() -> Optional[DatabaseConnection]:
    """获取由生命周期管理的ClickHouse数据库连接"""
    if not app_context.connection:
        logger.error("ClickHouse connection not available or not enabled.")
        return None
    return app_context.connection

def format_query_results(result: Dict) -> str:
    """格式化查询结果为字符串表格"""
    if not result.get("success"):
        return f"Error executing query: {result.get('error', 'Unknown error')}"
        
    if not result.get("data"):
        return f"Query executed. Rows returned: {result.get('row_count', 0)}"
        
    # 格式化为表格
    output = []
    column_names = result["column_names"]
    
    # 检查数据结构
    data = result["data"]
    is_list_of_lists = False
    
    # 如果是列表的列表结构，而不是字典列表
    if data and isinstance(data[0], list):
        is_list_of_lists = True
        # 如果没有列名，生成序号列名
        if not column_names:
            column_names = [f"Column_{i}" for i in range(len(data[0]))]
    
    # 计算列宽
    widths = [len(str(col)) for col in column_names]
    for row in data:
        for i, col in enumerate(column_names):
            if i < len(widths):  # 防止索引越界
                if is_list_of_lists:
                    # 列表格式
                    value = str(row[i]) if i < len(row) else ''
                else:
                    # 字典格式
                    value = str(row.get(col, '')) if hasattr(row, 'get') else str(row)
                widths[i] = max(widths[i], len(value))
    
    # 创建表头
    header = " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(column_names) if i < len(widths))
    separator = "-+-".join("-" * w for w in widths)
    
    output.append(header)
    output.append(separator)
    
    # 创建数据行
    for row in data:
        if is_list_of_lists:
            # 列表格式
            row_str = " | ".join(str(row[i] if i < len(row) else '').ljust(widths[i]) 
                               for i in range(len(column_names)) if i < len(widths))
        else:
            # 字典格式
            if hasattr(row, 'get'):
                row_str = " | ".join(str(row.get(col, '')).ljust(widths[i]) 
                                  for i, col in enumerate(column_names) if i < len(widths))
            else:
                # 如果是单个值，将其显示在第一列
                row_str = str(row).ljust(widths[0] if widths else 10)
                
        output.append(row_str)
    
    output.append("")
    output.append(f"Total rows: {result['row_count']} (showing first {len(data)})")
    
    return "\n".join(output)

# --- Tool Implementations ---

async def tool_clickhouse_execute_read_query(args: dict) -> str:
    try:
        query = args["query"]
        params = args.get("params", {})
        max_rows = args.get("max_rows", DB_CONFIG["max_rows"])
                    
        # 执行查询
        return await execute_db_query(query, params, max_rows)
        
    except KeyError as e:
        return f"Error: Missing required parameter: {e.args[0]}"
    except Exception as e:
        return f"Error: {str(e)}\n{traceback.format_exc()}"


async def tool_clickhouse_get_table_schema(args: dict) -> str:
    try:
        table_name = args["table_name"]
        max_rows = args.get("max_rows", DB_CONFIG["max_rows"])
        
        # 获取连接
        conn = get_connection()
        if not conn:
            return f"Error: Could not connect to ClickHouse database"
        
        # 使用DESCRIBE语句获取表结构
        query = f"DESCRIBE TABLE {table_name}"
        
        # 使用通用查询处理逻辑
        result = await execute_db_query(query, {}, max_rows)
        return result
        
    except KeyError as e:
        return f"Error: Missing required parameter: {e.args[0]}"
    except Exception as e:
        return f"Error getting schema: {str(e)}\n{traceback.format_exc()}"

async def execute_db_query(query: str, params: dict, max_rows: int) -> str:
    """执行数据库查询并返回结果"""
    try:
        # 安全检查：只允许SELECT、SHOW、DESCRIBE、EXPLAIN等只读操作
        query_lower = query.strip().lower()
        allowed_prefixes = ("select", "show", "describe", "desc", "explain")
        if not query_lower.startswith(allowed_prefixes):
            return f"Error: Only read operations (SELECT, SHOW, DESCRIBE, EXPLAIN) are allowed. Rejected query: {query}"
        
        # 防止多语句执行
        if ";" in query[:-1]:  # 允许查询末尾有分号
            return f"Error: Multiple statements are not allowed. Rejected query: {query}"
        
        # 获取连接
        conn = get_connection()
        if not conn:
            return f"Error: Could not connect to ClickHouse database"
        
        result = None
        
        if conn.connection_type == "http":
            # 使用HTTP接口
            result = execute_http_query(
                DB_CONFIG["host"], 
                DB_CONFIG["http_port"], 
                conn.database, 
                query, 
                DB_CONFIG["username"], 
                DB_CONFIG["password"], 
                params, 
                max_rows
            )
        else:
            # 在ClickHouse上使用原生客户端执行查询
            result_set = conn.connection.execute(query, params)
            
            # 判断查询类型
            is_show_query = query_lower.startswith(("show", "describe", "desc"))
            
            if isinstance(result_set, list):
                # 对于SELECT查询和SHOW查询
                column_names = []
                rows = []
                
                # 对于SHOW/DESCRIBE等简单查询，使用简单处理
                if is_show_query:
                    # 这些查询通常返回单列或简单结构
                    # 如SHOW TABLES返回表名列表
                    if result_set and len(result_set) > 0:
                        # 检查是否是元组/列表列表
                        is_list_of_tuples = isinstance(result_set[0], (list, tuple))
                        
                        if is_list_of_tuples:
                            # 对于SHOW TABLES, DESCRIBE TABLE等返回的是元组列表
                            # 确定列数
                            num_cols = len(result_set[0]) if result_set else 0
                            # 生成默认列名
                            if query_lower.startswith("show tables"):
                                column_names = ["table_name"]
                            elif query_lower.startswith(("describe", "desc")):
                                column_names = ["name", "type", "default_type", "default_expression"]
                            else:
                                column_names = [f"column_{i}" for i in range(num_cols)]
                            
                            # 保留原始数据结构
                            rows = result_set[:max_rows]
                        else:
                            # 对于返回标量列表的情况
                            column_names = ["value"]
                            rows = [[item] for item in result_set[:max_rows]]
                else:
                    # 对于复杂SELECT查询，尝试获取真实列名
                    try:
                        # 使用JSON格式获取列名
                        col_query = f"SELECT * FROM ({query}) FORMAT JSONCompactEachRow LIMIT 1"
                        col_result = conn.connection.execute(col_query, params)
                        if col_result and isinstance(col_result, list) and len(col_result) > 0:
                            field = col_result[0]
                            if field and hasattr(field, 'keys'):
                                column_names = list(field.keys())
                    except Exception as col_err:
                        logger.warning(f"Could not determine column names for query '{query}': {col_err}")
                    
                    # 如果无法获取列名，使用默认列名
                    if not column_names and result_set and len(result_set) > 0:
                        num_cols = len(result_set[0]) if isinstance(result_set[0], (list, tuple)) else 1
                        column_names = [f"column_{i}" for i in range(num_cols)]
                    
                    # 如果是字典列表，保留原样；如果是元组列表，转换为列表的列表
                    if result_set and len(result_set) > 0:
                        if hasattr(result_set[0], 'keys'):
                            rows = result_set[:max_rows]
                        else:
                            rows = result_set[:max_rows]
                
                # 格式化结果
                result = {
                    "success": True,
                    "data": rows,
                    "error": None,
                    "row_count": len(result_set),
                    "column_names": column_names
                }
            else:
                # 对于返回行数的DDL查询 (不应该在只读模式中出现)
                result = {
                    "success": True,
                    "data": None,
                    "error": None,
                    "row_count": result_set,
                    "column_names": []
                }
        
        # 格式化结果为字符串
        if result:
            return format_query_results(result)
        else:
            return "Query executed but no results were returned."
    
    except Exception as e:
        return f"Database error: {str(e)}\n{traceback.format_exc()}"

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
        arguments = arguments or {}
        
        if name == "clickhouse_execute_read_query":
            result = await tool_clickhouse_execute_read_query(arguments)
        elif name == "clickhouse_get_table_schema":
            result = await tool_clickhouse_get_table_schema(arguments)
        else:
            result = f"Unknown tool: {name}"
            
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# --- Main entry ---
async def main():
    from mcp.server.stdio import stdio_server
    
    # 打印数据库配置信息
    logger.info("ClickHouse configuration:")
    enabled = "ENABLED" if DB_CONFIG["enabled"] else "DISABLED"
    logger.info(f"- ClickHouse ({enabled}): {DB_CONFIG['host']}:{DB_CONFIG['port']} (native), {DB_CONFIG['host']}:{DB_CONFIG['http_port']} (HTTP), database: {DB_CONFIG['database']}")
    logger.info(f"- Connection mode: {DB_CONFIG['use_http']}")
    logger.info(f"- Max rows per query: {DB_CONFIG['max_rows']}")
    
    # 打印资源描述文件信息
    logger.info(f"- Resource description file: {DB_CONFIG['resource_desc_file']}")
    
    # 检查必要包是否安装
    if not CLICKHOUSE_NATIVE_AVAILABLE:
        logger.warning("clickhouse-driver not installed, native protocol unavailable")
    if not CLICKHOUSE_HTTP_AVAILABLE:
        logger.warning("requests not installed, HTTP protocol unavailable")
    if not CLICKHOUSE_AVAILABLE:
        logger.error("No ClickHouse connection methods available. Install clickhouse-driver or requests.")

    async with app_lifespan(): # Manage connection lifecycle
        async with stdio_server() as (read_stream, write_stream):
            logger.info("ClickHouse MCP server running with stdio transport")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="clickhouse-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

if __name__ == "__main__":
    asyncio.run(main()) 