from setuptools import setup, find_packages

setup(
    name="mini-cursor",
    version="0.2.0",
    description="None",
    author="Lucas Luo",
    author_email="None",
    url="https://github.com/the-nine-nation/mini-cursor",
    license="MIT",
    packages=find_packages(include=["mini_cursor", "mini_cursor.*"]),
    include_package_data=True,
    package_data={
        "mini_cursor": ["static/**/*", "static/**/.*"],
    },
    install_requires=[
        'python-dotenv>=1.0.0',
        'openai>=1.3.0',
        'requests',
        'mcp',
        'click',
        'rich',
        'aiomysql',
        'clickhouse-driver',
        'fastapi>=0.104.1',
        'uvicorn>=0.23.2',
        'jinja2>=3.0.0',
        'sse-starlette>=1.6.1',
        'aiofiles>=0.8.0',
        'Markdown>=3.4.0',
        'pygments>=2.13.0',
    ],
    entry_points={
        'console_scripts': [
            'mini-cursor = mini_cursor.cli_main:cli',
        ],
    },
    python_requires='>=3.10',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
) 