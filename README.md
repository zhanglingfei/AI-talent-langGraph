# Talent Matching System

基于 LangGraph 的 IT 人才匹配系统

## 快速开始

### 1. 环境准备
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Keys

# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际的 API keys

# 3. 设置 Google 认证
# 下载 credentials.json 到项目根目录

# 4. 初始化服务
python -c "from src.main import TalentMatchingSystem; system = TalentMatchingSystem()"

# 5. 启动 API 服务
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

# 6. 或使用 Docker
docker-compose up -d