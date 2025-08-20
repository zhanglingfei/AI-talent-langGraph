# Talent Matching System

An IT talent matching system based on LangGraph

## Quick Start

### 1. Environment Setup
```bash
cp .env.example .env
# Edit the .env file and fill in your API keys

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment variables
cp .env.example .env
# Edit .env and enter the actual API keys

# 3. Set up Google authentication
# Download credentials.json to the project root

# 4. Initialize services
python -c "from src.main import TalentMatchingSystem; system = TalentMatchingSystem()"

# 5. Start the API service
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

# 6. Or use Docker

docker-compose up -d
```

<img width="1756" height="1780" alt="image" src="https://github.com/user-attachments/assets/6b214f08-ac11-4005-86d8-78c66fa184cc" />
