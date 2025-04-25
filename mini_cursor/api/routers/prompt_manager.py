import os

# 获取文件的父目录
parent_dir = os.path.dirname(os.path.dirname(__file__))

# 获取父目录的父目录
grandparent_dir = os.path.dirname(parent_dir)

#获取默认系统提示文件路径
system_prompt_default_path = os.path.join(grandparent_dir, "data", "system_prompt_default.txt")

system_prompt_path = os.path.join(grandparent_dir, "data", "system_prompt.txt")
def load_system_prompt():
    # 读取系统提示文件内容
    try:
        if os.path.exists(system_prompt_path):
            with open(system_prompt_path, 'r', encoding='utf-8') as file:
                system_prompt= file.read()
        else:
            with open(system_prompt_default_path, 'r', encoding='utf-8') as file:
                system_prompt= file.read()
        return system_prompt
    except Exception as e:
        print(f"读取系统提示文件时出错: {str(e)}")