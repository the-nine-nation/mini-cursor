import os
from pathlib import Path
from dotenv import load_dotenv

# 添加颜色输出支持
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

# OpenAI API配置
OPENAI_API_KEY = None 
OPENAI_BASE_URL = None
OPENAI_MODEL = None







# 设置超时时间（秒）
TOOL_CALL_TIMEOUT = 15
# 设置是否显示详细日志
VERBOSE_LOGGING = False
# MCP配置文件
MCP_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "mcp_config.json") 

# 初始化函数，用于首次加载或重新加载配置
def init_config():
    global OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    current_dir = Path(__file__).resolve()  # 当前文件的绝对路径
    # 向上查找包含mini_cursor目录的父目录
    project_root = current_dir.parent.parent.parent  # 这应该是mini-cursor目录
    env_file_path = project_root / "mini_cursor" / ".env"
    load_dotenv(dotenv_path=env_file_path, override=True)
    print(f"已加载环境变量从: {env_file_path}")
    
    
    # 从环境变量加载配置
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
    
    return {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "OPENAI_BASE_URL": OPENAI_BASE_URL,
        "OPENAI_MODEL": OPENAI_MODEL
    }

# 初始化配置
init_config() 