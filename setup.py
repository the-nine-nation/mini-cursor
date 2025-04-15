from setuptools import setup, find_packages

setup(
    name="mini_cursor",
    version="0.1.0",
    description="None",
    author="lzy",
    author_email="None",
    url="https://github.com/the-nine-nation/mini-cursor",
    license="MIT",
    packages=find_packages(
        ),
    include_package_data=True,
    install_requires=[
        'python-dotenv',
        'openai',
        'requests',
        'mcp[cli]',
    ],
    entry_points={
        'console_scripts': [
            'mini-cursor = mini_cursor.cli_main:main',
            'mini-cursor-server = mini_cursor.core.cursor_mcp_all:main',
        ],
    },
    python_requires='>=3.9',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
) 