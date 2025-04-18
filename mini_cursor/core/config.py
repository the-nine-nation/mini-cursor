import os
from pathlib import Path
from dotenv import load_dotenv

# 尝试加载多个位置的.env文件
# 1. 项目根目录
root_env_path = Path.cwd() / ".env"
# 2. 包内目录
package_env_path = Path(__file__).parent.parent / ".env"

# 优先加载当前工作目录中的.env文件，其次是包内的.env文件
if root_env_path.exists():
    load_dotenv(dotenv_path=root_env_path, override=True)
    print(f"已加载环境变量从: {root_env_path}")
elif package_env_path.exists():
    load_dotenv(dotenv_path=package_env_path, override=True)
    print(f"已加载环境变量从: {package_env_path}")
else:
    print("未找到.env文件，使用环境变量默认值")

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

# OpenAI API配置
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")

# 设置超时时间（秒）
TOOL_CALL_TIMEOUT = 30
# 设置是否显示详细日志
VERBOSE_LOGGING = True
# MCP配置文件
MCP_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "core", "mcp_config.json") 