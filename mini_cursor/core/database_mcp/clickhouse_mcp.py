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
    "http_port": int(os.environ.get("CLICKHOUSE_PORT", "8123")),  # 使用CLICKHOUSE_PORT作为HTTP端口
    "database": os.environ.get("CLICKHOUSE_DATABASE", "default"),
    "username": os.environ.get("CLICKHOUSE_USERNAME", "default"),
    "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
    "use_http": "true",  # 强制使用HTTP模式，因为配置的是HTTP端口
    "max_rows": int(os.environ.get("MAX_ROWS", "10")),  # 默认每次查询最多返回50行
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
    connection_mode: Optional[str] = None
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
        "description": "Execute read-only ClickHouse SQL code. Only SELECT, SHOW, DESCRIBE, EXPLAIN allowed; queries are validated before execution.\n\n"+clickhouse_resource_description,
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
        "description": "Get the schema for a ClickHouse table. If no table name is provided or '*' is used, it will return a list of all available tables in the database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "The name of the table to get schema for. Leave empty or use '*' to list all tables."
                },
                "max_rows": {
                    "type": "integer",
                    "description": "Maximum number of rows to return",
                    "default": DB_CONFIG["max_rows"]
                }
            }
        }
    }
]

# --- ClickHouse HTTP Client ---
def execute_http_query(host, port, database, query, username, password, params=None, max_rows=None):
    """通过HTTP接口执行ClickHouse查询"""
    if max_rows is None:
        max_rows = DB_CONFIG["max_rows"]
        
    url = f"http://{host}:{port}/"
    
    # 使用已验证工作的查询方式：URL参数认证 + GET请求
    params_dict = {
        "query": query,
        "user": username,
        "password": password,
        "database": database,
        "default_format": "JSONCompact"  # 使用JSON格式响应
    }
    
    try:
        logger.info(f"Executing ClickHouse HTTP query: {url}")
        response = requests.get(url, params=params_dict)
        response.raise_for_status()
        return process_clickhouse_response(response, max_rows)
    except Exception as e:
        logger.error(f"ClickHouse HTTP query error: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "row_count": 0,
            "column_names": []
        }

def process_clickhouse_response(response, max_rows):
    """处理ClickHouse HTTP响应"""
    try:
        content_type = response.headers.get('Content-Type', '')
        logger.info(f"Response content type: {content_type}")
        
        # 尝试解析JSON响应
        if 'json' in content_type.lower():
            try:
                result = response.json()
                return process_clickhouse_result(result, max_rows)
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse JSON response: {json_err}")
                # 即使是JSON内容类型，如果解析失败，也作为文本处理
        
        # 处理TSV格式（ClickHouse默认）
        if 'text/tab-separated-values' in content_type.lower() or 'tsv' in content_type.lower():
            text = response.text.strip()
            rows = []
            
            # 分割成行
            lines = text.split('\n')
            if not lines:
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "row_count": 0,
                    "column_names": []
                }
                
            # 确定列名
            # 如果是简单查询，如SELECT 1，ClickHouse不会返回列名
            # 根据查询结果推断列名
            if len(lines) == 1 and not '\t' in lines[0]:
                # 单值结果
                column_names = ["result"]
                rows = [[lines[0]]]
            else:
                # 有标题行的TSV
                column_names = ["value"] if len(lines) > 0 else []
                
                for line in lines:
                    if line.strip():
                        if '\t' in line:
                            # 这是一个有多列的行
                            row_values = line.split('\t')
                            rows.append(row_values)
                            # 生成足够的列名
                            if len(column_names) < len(row_values):
                                column_names = [f"column_{i+1}" for i in range(len(row_values))]
                        else:
                            # 单列行
                            rows.append([line])
            
            return {
                "success": True,
                "data": rows[:max_rows],
                "error": None,
                "row_count": len(rows),
                "column_names": column_names
            }
                
        # 其他文本响应
        text = response.text.strip()
        
        # 简单处理通用文本响应
        if not text:
            return {
                "success": True,
                "data": [],
                "error": None,
                "row_count": 0,
                "column_names": []
            }
            
        # 单行响应
        if '\n' not in text:
            return {
                "success": True,
                "data": [[text]],
                "error": None,
                "row_count": 1,
                "column_names": ["result"]
            }
            
        # 多行响应
        lines = text.split('\n')
        rows = [[line] for line in lines if line.strip()]
        
        return {
            "success": True,
            "data": rows[:max_rows],
            "error": None,
            "row_count": len(rows),
            "column_names": ["result"]
        }
            
    except Exception as e:
        logger.error(f"Error processing response: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "row_count": 0,
            "column_names": []
        }

def process_clickhouse_result(result, max_rows):
    """处理ClickHouse HTTP响应结果"""
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

# --- Lifespan Management ---
@asynccontextmanager
async def app_lifespan() -> AsyncIterator[None]:
    """Manage application lifecycle with database connection."""
    conn = None
    connection_mode = None
    
    if DB_CONFIG["enabled"]:
        config = DB_CONFIG
        
        # 1. 首先尝试HTTP连接（通过配置确定的优先方式）
        if CLICKHOUSE_HTTP_AVAILABLE:
            try:
                logger.info(f"Testing ClickHouse HTTP connection to {config['host']}:{config['http_port']}")
                
                # 使用简单的HTTP请求测试连接
                url = f"http://{config['host']}:{config['http_port']}/"
                params = {
                    "query": "SELECT 1",
                    "user": config["username"],
                    "password": config["password"],
                    "database": config["database"]
                }
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                logger.info(f"ClickHouse HTTP connection successful: {response.text.strip()}")
                
                conn = DatabaseConnection(
                    connection=None,  # HTTP模式不需要持久连接
                    database=config["database"],
                    connection_type="http"
                )
                connection_mode = "http"
                logger.info("Successfully established ClickHouse HTTP connection")
                
            except Exception as http_err:
                logger.warning(f"ClickHouse HTTP connection failed: {http_err}")
                # 在HTTP失败后尝试原生连接，不退出
                connection_mode = None
        
        # 2. 如果HTTP连接失败或不可用，尝试原生驱动连接
        if connection_mode is None and CLICKHOUSE_NATIVE_AVAILABLE:
            try:
                logger.info(f"Testing ClickHouse native connection to {config['host']}:{config['port']}")
                
                client = ClickHouseClient(
                    host=config["host"],
                    port=config["port"],
                    database=config["database"],
                    user=config["username"],
                    password=config["password"],
                    settings={'readonly': 1}  # 强制只读模式
                )
                
                # 测试连接
                result = client.execute("SELECT 1")
                logger.info(f"ClickHouse native connection successful: {result}")
                
                conn = DatabaseConnection(
                    connection=client,
                    database=config["database"],
                    connection_type="native"
                )
                connection_mode = "native"
                logger.info("Successfully established ClickHouse native connection")
                
            except Exception as native_err:
                logger.error(f"ClickHouse native connection failed: {native_err}")
                # 两种方式都失败了，将保持 conn=None
        
        # 记录最终连接状态
        if conn is None:
            logger.error("Failed to establish any ClickHouse connection")
            if not CLICKHOUSE_HTTP_AVAILABLE and not CLICKHOUSE_NATIVE_AVAILABLE:
                logger.error("Neither ClickHouse HTTP nor native drivers are available")
            else:
                logger.error("All connection attempts failed")
        else:
            logger.info(f"ClickHouse connection established using {connection_mode} mode")
            
        app_context.connection = conn
        app_context.connection_mode = connection_mode

    try:
        yield # Server runs here
    finally:
        # Cleanup on shutdown
        if app_context.connection:
            logger.info(f"Closing ClickHouse {app_context.connection.connection_type} connection")
            
            if app_context.connection.connection_type == "native" and app_context.connection.connection:
                try:
                    # ClickHouse native client's cleanup
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
            app_context.connection_mode = None
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
        
    # 检查是否有错误信息，并作为纯文本显示
    if result.get("error"):
        # 对于错误消息，直接以纯文本返回，保留所有换行符
        return f"Error: {result.get('error')}"
        
    # 格式化为表格
    output = []
    column_names = result.get("column_names", [])
    
    # 检查数据结构
    data = result["data"]
    is_list_of_lists = False
    
    if not data:
        return "Query executed. No data returned."
    
    # 检测数据类型
    if isinstance(data[0], list):
        is_list_of_lists = True
        # 如果没有列名，生成序号列名
        if not column_names:
            column_names = [f"Column_{i}" for i in range(len(data[0]))]
    elif isinstance(data[0], dict):
        # 从字典中提取列名
        if not column_names:
            column_names = list(data[0].keys())
    else:
        # 处理不是列表或字典的情况
        column_names = ["Value"]
        data = [[item] for item in data]
        is_list_of_lists = True
    
    # 计算列宽
    widths = [len(str(col)) for col in column_names]
    
    for row in data:
        if is_list_of_lists:
            # 针对列表数据
            for i, value in enumerate(row):
                if i < len(widths):
                    # 确保我们正确处理值中的换行符
                    str_value = str(value)
                    # 计算列宽时要考虑字符串中可能的换行符
                    max_line_len = max([len(line) for line in str_value.split('\n')]) if '\n' in str_value else len(str_value)
                    widths[i] = max(widths[i], max_line_len)
        elif isinstance(row, dict):
            # 针对字典数据
            for i, col in enumerate(column_names):
                if i < len(widths):
                    value = str(row.get(col, ''))
                    # 计算列宽时要考虑字符串中可能的换行符
                    max_line_len = max([len(line) for line in value.split('\n')]) if '\n' in value else len(value)
                    widths[i] = max(widths[i], max_line_len)
        else:
            # 单值处理
            str_value = str(row)
            max_line_len = max([len(line) for line in str_value.split('\n')]) if '\n' in str_value else len(str_value)
            widths[0] = max(widths[0], max_line_len)
    
    # 创建表头
    if column_names:
        header = " | ".join(str(col).ljust(widths[i]) for i, col in enumerate(column_names) if i < len(widths))
        separator = "-+-".join("-" * w for w in widths)
        
        output.append(header)
        output.append(separator)
    
    # 创建数据行
    for row in data:
        if is_list_of_lists:
            # 列表格式
            row_values = []
            for i, value in enumerate(row):
                if i < len(widths):
                    # 如果值中有换行符，需要特殊处理
                    str_value = str(value)
                    if '\n' in str_value:
                        # 对于多行内容，我们保留原始换行符
                        # 缩进后续行以对齐
                        lines = str_value.split('\n')
                        first_line = lines[0].ljust(widths[i])
                        padding = ' ' * (len(" | ".join([""] * i)) + 3)
                        continuation = '\n'.join([f"{padding}{line}" for line in lines[1:]])
                        row_values.append(first_line)
                        if continuation:
                            row_values[-1] = f"{row_values[-1]}\n{continuation}"
                    else:
                        row_values.append(str_value.ljust(widths[i]))
            row_str = " | ".join(row_values)
        elif isinstance(row, dict):
            # 字典格式
            row_values = []
            for i, col in enumerate(column_names):
                if i < len(widths):
                    value = str(row.get(col, ''))
                    if '\n' in value:
                        # 对于多行内容，保留原始换行符
                        lines = value.split('\n')
                        first_line = lines[0].ljust(widths[i])
                        padding = ' ' * (len(" | ".join([""] * i)) + 3)
                        continuation = '\n'.join([f"{padding}{line}" for line in lines[1:]])
                        row_values.append(first_line)
                        if continuation:
                            row_values[-1] = f"{row_values[-1]}\n{continuation}"
                    else:
                        row_values.append(value.ljust(widths[i]))
            row_str = " | ".join(row_values)
        else:
            # 单值
            row_str = str(row).ljust(widths[0] if widths else 10)
                
        output.append(row_str)
    
    output.append("")
    output.append(f"Total rows: {result['row_count']} (showing first {len(data)})")
    
    # 包装在<pre>标签中以确保在Web界面保留换行符和格式
    return "<pre>" + "\n".join(output) + "</pre>"

# --- Tool Implementations ---

async def tool_clickhouse_execute_read_query(args: dict) -> str:
    try:
        query = args["query"]
        params = args.get("params", {})
        # Cap max_rows at 50
        max_rows = min(args.get("max_rows", DB_CONFIG["max_rows"]), 50)
                    
        # 执行查询
        return await execute_db_query(query, params, max_rows)
        
    except KeyError as e:
        return f"Error: Missing required parameter: {e.args[0]}"
    except Exception as e:
        return f"Error: {str(e)}\n{traceback.format_exc()}"


async def tool_clickhouse_get_table_schema(args: dict) -> str:
    try:
        table_name = args.get("table_name", "")
        # Cap max_rows at 50
        max_rows = min(args.get("max_rows", DB_CONFIG["max_rows"]), 50)
        
        # 检查表名是否有效
        if not table_name or table_name.strip() == "*":
            # 如果没有提供表名或者使用了通配符，返回所有表
            query = f"SHOW TABLES FROM {DB_CONFIG['database']}"
            logger.info(f"No specific table name provided, listing all tables with query: {query}")
            result = await execute_db_query(query, {}, max_rows)
            return f"Available tables in database {DB_CONFIG['database']}:\n{result}"
        
        # 获取连接
        conn = get_connection()
        if not conn:
            return f"Error: Could not connect to ClickHouse database"
        
        # 使用DESCRIBE语句获取表结构，确保表名已被正确引用
        table_name = table_name.strip()
        query = f"DESCRIBE TABLE {table_name}"
        logger.info(f"Getting schema for table {table_name} with query: {query}")
        
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
        connection_error = None
        
        # 1. 首先使用启动时确定的连接方式
        try:
            # 使用已确定的连接方式执行查询
            if app_context.connection_mode == "http":
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
                if not result.get("success", False):
                    raise Exception(result.get("error", "Unknown HTTP query error"))
            else:
                # 使用原生客户端
                result_set = conn.connection.execute(query, params)
                result = process_native_result(result_set, query_lower, max_rows)
        except Exception as e:
            # 记录错误，准备尝试另一种方式
            connection_error = str(e)
            logger.warning(f"Query using {app_context.connection_mode} mode failed: {e}")
            result = None
        
        # 2. 如果主要连接方式失败，尝试另一种方式
        if result is None:
            try:
                alternate_mode = "http" if app_context.connection_mode == "native" else "native"
                logger.info(f"Trying alternate connection mode: {alternate_mode}")
                
                if alternate_mode == "http" and CLICKHOUSE_HTTP_AVAILABLE:
                    # 尝试HTTP连接
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
                    if not result.get("success", False):
                        raise Exception(result.get("error", "Unknown HTTP query error"))
                    
                elif alternate_mode == "native" and CLICKHOUSE_NATIVE_AVAILABLE:
                    # 临时创建原生客户端
                    try:
                        client = ClickHouseClient(
                            host=DB_CONFIG["host"],
                            port=DB_CONFIG["port"],
                            database=DB_CONFIG["database"],
                            user=DB_CONFIG["username"],
                            password=DB_CONFIG["password"],
                            settings={'readonly': 1}
                        )
                        result_set = client.execute(query, params)
                        result = process_native_result(result_set, query_lower, max_rows)
                        
                        # 关闭临时连接
                        if hasattr(client, 'disconnect'):
                            client.disconnect()
                    except Exception as native_error:
                        raise Exception(f"Native connection failed: {native_error}")
                else:
                    raise Exception(f"Alternate connection mode {alternate_mode} not available")
                
                # 如果替代方式成功，考虑切换连接模式
                logger.info(f"Query succeeded using alternate mode {alternate_mode}")
                
            except Exception as alt_error:
                # 两种方式都失败了，返回综合错误信息
                error_msg = f"Primary connection ({app_context.connection_mode}) error: {connection_error}\n"
                error_msg += f"Alternate connection error: {alt_error}"
                return f"Database error: {error_msg}"
        
        # 格式化结果为字符串
        if result:
            return format_query_results(result)
        else:
            return "Query executed but no results were returned."
    
    except Exception as e:
        return f"Database error: {str(e)}\n{traceback.format_exc()}"

def process_native_result(result_set, query_lower, max_rows):
    """处理原生客户端查询结果"""
    # 判断查询类型
    is_show_query = query_lower.startswith(("show", "describe", "desc"))
    
    if isinstance(result_set, list):
        # 对于SELECT查询和SHOW查询
        column_names = []
        rows = []
        
        # 对于SHOW/DESCRIBE等简单查询，使用简单处理
        if is_show_query:
            # 这些查询通常返回单列或简单结构
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
            # 对于复杂SELECT查询，尝试获取列名
            if result_set and len(result_set) > 0:
                # 检查结果类型
                if hasattr(result_set[0], 'keys'):
                    # 结果是字典列表
                    column_names = list(result_set[0].keys())
                    rows = result_set[:max_rows]
                else:
                    # 结果是元组/列表列表
                    num_cols = len(result_set[0]) if isinstance(result_set[0], (list, tuple)) else 1
                    column_names = [f"column_{i}" for i in range(num_cols)]
                    rows = result_set[:max_rows]
        
        # 格式化结果
        return {
            "success": True,
            "data": rows,
            "error": None,
            "row_count": len(result_set),
            "column_names": column_names
        }
    else:
        # 对于返回行数的DDL查询 (不应该在只读模式中出现)
        return {
            "success": True,
            "data": [[str(result_set)]],
            "error": None,
            "row_count": 1,
            "column_names": ["result"]
        }

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
        
        # 检查结果是否包含HTML标签，特别是<pre>标签
        if result.startswith("<pre>") and result.endswith("</pre>"):
            # 这是已经格式化为HTML的内容
            html_content = result
            # 从HTML中提取纯文本用于可能的其他处理
            text_content = result[5:-6]  # 去掉<pre>和</pre>标签
            
            return [types.TextContent(
                type="text", 
                text=text_content,
                annotations=None
            )]
        else:
            # 普通文本内容，不需要特殊处理
            return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# --- Main entry ---
async def main():
    from mcp.server.stdio import stdio_server
    
    # 打印基本配置信息
    logger.info("ClickHouse MCP Configuration:")
    logger.info(f"- Host: {DB_CONFIG['host']}")
    logger.info(f"- HTTP Port: {DB_CONFIG['http_port']}")
    logger.info(f"- Native Port: {DB_CONFIG['port']}")
    logger.info(f"- Database: {DB_CONFIG['database']}")
    logger.info(f"- Username: {DB_CONFIG['username']}")
    logger.info(f"- Resource File: {DB_CONFIG['resource_desc_file']}")
    
    # 检查必要条件
    if not DB_CONFIG["enabled"]:
        logger.warning("ClickHouse is disabled in configuration. Set CLICKHOUSE_ENABLED=true to enable.")
    
    if not CLICKHOUSE_HTTP_AVAILABLE and not CLICKHOUSE_NATIVE_AVAILABLE:
        logger.error("No ClickHouse clients available. Install clickhouse-driver or requests package.")
        sys.exit(1)
    
    # 启动服务
    try:
        async with app_lifespan():  # 这将设置连接
            # 检查连接是否建立成功
            if not app_context.connection:
                logger.warning("No ClickHouse connection established. MCP will still start but queries will fail.")
            else:
                logger.info(f"ClickHouse connection established using {app_context.connection_mode} mode.")
            
            # 启动MCP服务器
            async with stdio_server() as (read_stream, write_stream):
                logger.info("ClickHouse MCP server starting with stdio transport")
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
    except Exception as e:
        logger.error(f"ClickHouse MCP server failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 