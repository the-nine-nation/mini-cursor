from setuptools import setup, find_packages

setup(
    name="mini-cursor",
    version="0.1.0",
    description="None",
    author="Lucas Luo",
    author_email="None",
    url="https://github.com/the-nine-nation/mini-cursor",
    license="MIT",
    packages=find_packages(include=["mini_cursor", "mini_cursor.*"]),
    include_package_data=True,
    install_requires=[
        'python-dotenv',
        'openai',
        'requests',
        'mcp',
        'click',
        'rich',
        'aiomysql',
        'clickhouse-driver'
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