import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """系统配置"""
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    # Google配置
    SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
    ATTACHMENT_FOLDER_ID = os.getenv("GOOGLE_FOLDER_ID")
    CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # 处理配置
    EMAIL_BATCH_SIZE = 10
    MAX_RETRIES = 3
    
    # Sheet名称
    SHEET_NAMES = {
        "GMAIL_DATA": "GmailData",
        "PROJECTS": "Projects", 
        "RESUME_DATABASE": "resume_database",
        "MATCHES": "Matches"
    }