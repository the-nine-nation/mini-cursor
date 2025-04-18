# mini-cursor 开发指南

## 开发环境设置

本项目已设置为可编辑模式开发，无需每次修改代码后重新安装。

### 安装步骤

1. 克隆仓库：
   ```bash
   git clone https://github.com/the-nine-nation/mini-cursor.git
   cd mini-cursor
   ```

2. 创建并激活conda环境（或使用其他虚拟环境）：
   ```bash
   conda create -n mini-cursor python=3.10
   conda activate mini-cursor
   ```

3. 以开发模式安装：
   ```bash
   pip install -e .
   ```

4. 验证安装：
   ```bash
   pip show mini-cursor
   # 应显示 "Editable project location: /your/path/to/mini-cursor"
   ```

## 开发工作流程

项目包含以下开发辅助脚本：

- `test_dev.py`: 基本测试脚本，显示包版本和可用命令
- `debug_test.py`: 带断点的调试脚本，用于交互式调试
- `dev_chat.py`: 直接运行chat功能的脚本，跳过CLI入口

### 常用开发命令

1. 运行基本测试：
   ```bash
   python test_dev.py
   ```

2. 运行调试模式：
   ```bash
   python debug_test.py
   ```
   在调试器中：
   - `p mini_cursor.__version__` - 打印变量
   - `!print(dir(cli_main))` - 执行命令
   - `c` - 继续执行
   - `q` - 退出调试

3. 测试chat功能：
   ```bash
   python dev_chat.py
   ```

4. 使用命令行工具（无需重新安装即可测试更改）：
   ```bash
   mini-cursor help
   ```

## 文件结构

- `mini_cursor/`: 主包目录
  - `__init__.py`: 包初始化和版本信息
  - `cli_main.py`: 命令行接口定义
  - `mcp_qa.py`: 聊天功能实现
  - `prompt.py`: 提示词模板
  - `core/`: 核心功能模块

## 调试技巧

1. 修改代码后无需重新安装，更改会立即生效
2. 使用Python内置的断点：`import pdb; pdb.set_trace()`
3. 或者使用现代Python断点：`breakpoint()`
4. 在VSCode中设置断点并使用调试器
5. 使用`print()`语句进行简单调试

## 发布流程

1. 更新版本号：`mini_cursor/__init__.py`中的`__version__`
2. 更新`setup.py`中的依赖（如果有更改）
3. 构建包：`python -m build`
4. 测试安装：`pip install dist/mini_cursor-X.Y.Z.tar.gz`
5. 发布：`twine upload dist/*` 