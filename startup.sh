#!/bin/bash

# 检查环境变量
if [ ! -f .env ]; then
    echo "错误: 请先配置 .env 文件"
    exit 1
fi

# 安装依赖
pip install -r requirements.txt

# 初始化数据库连接
python -c "from src.services.sheets_service import SheetsService; SheetsService()._initialize_service()"

# 启动应用
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload