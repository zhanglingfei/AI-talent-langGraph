import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List

load_dotenv()

class ConfigError(Exception):
    """配置错误异常"""
    pass

class Config:
    """系统配置"""
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    
    # Google配置 (备用)
    SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
    ATTACHMENT_FOLDER_ID = os.getenv("GOOGLE_FOLDER_ID")
    CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "src/services/credentials.json")
    
    # Qdrant配置
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    QDRANT_GRPC_PORT = int(os.getenv("QDRANT_GRPC_PORT", 6334))
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # 处理配置
    EMAIL_BATCH_SIZE = int(os.getenv("EMAIL_BATCH_SIZE", 10))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    
    # LLM配置
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.05))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 2000))
    
    # 向量化配置
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", 1536))
    
    # Qdrant Collection名称
    COLLECTIONS = {
        "CANDIDATES": "talent_candidates",
        "PROJECTS": "talent_projects",
        "MATCHES": "talent_matches"
    }
    
    # Sheet名称 (备用)
    SHEET_NAMES = {
        "GMAIL_DATA": "GmailData",
        "PROJECTS": "Projects", 
        "RESUME_DATABASE": "resume_database",
        "MATCHES": "Matches"
    }
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """验证配置完整性，返回错误列表"""
        errors = []
        
        # 验证必需的API密钥
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY 环境变量未设置")
        
        # 验证Google配置（如果要使用Google Sheets）
        if not cls.SPREADSHEET_ID:
            logging.warning("GOOGLE_SPREADSHEET_ID 未设置，Google Sheets功能将不可用")
        
        # 验证凭据文件是否存在
        if cls.CREDENTIALS_PATH and not os.path.exists(cls.CREDENTIALS_PATH):
            logging.warning(f"Google凭据文件不存在: {cls.CREDENTIALS_PATH}")
        
        # 验证数值配置
        try:
            if cls.EMAIL_BATCH_SIZE <= 0:
                errors.append("EMAIL_BATCH_SIZE 必须大于0")
            if cls.MAX_RETRIES < 0:
                errors.append("MAX_RETRIES 不能小于0")
            if cls.LLM_TEMPERATURE < 0 or cls.LLM_TEMPERATURE > 2:
                errors.append("LLM_TEMPERATURE 必须在0-2之间")
        except ValueError as e:
            errors.append(f"配置值类型错误: {str(e)}")
        
        return errors
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """获取配置摘要（不包含敏感信息）"""
        return {
            "openai_configured": bool(cls.OPENAI_API_KEY),
            "google_sheets_configured": bool(cls.SPREADSHEET_ID),
            "credentials_file_exists": bool(cls.CREDENTIALS_PATH and os.path.exists(cls.CREDENTIALS_PATH)),
            "email_batch_size": cls.EMAIL_BATCH_SIZE,
            "max_retries": cls.MAX_RETRIES,
            "llm_temperature": cls.LLM_TEMPERATURE,
            "sheet_names": cls.SHEET_NAMES
        }
    
    @classmethod
    def ensure_valid_config(cls):
        """确保配置有效，如果有错误则抛出异常"""
        errors = cls.validate_config()
        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"- {error}" for error in errors)
            raise ConfigError(error_msg)
        
        logging.info("配置验证通过")
    
    @classmethod
    def log_config_status(cls):
        """记录配置状态"""
        summary = cls.get_config_summary()
        logging.info("=== 系统配置状态 ===")
        logging.info(f"OpenAI API: {'✓' if summary['openai_configured'] else '✗'}")
        logging.info(f"Google Sheets: {'✓' if summary['google_sheets_configured'] else '✗'}")
        logging.info(f"凭据文件: {'✓' if summary['credentials_file_exists'] else '✗'}")
        logging.info(f"邮件批处理大小: {summary['email_batch_size']}")
        logging.info(f"最大重试次数: {summary['max_retries']}")
        logging.info(f"LLM温度: {summary['llm_temperature']}")
        
        # 验证配置并记录警告
        errors = cls.validate_config()
        if errors:
            logging.warning("配置问题:")
            for error in errors:
                logging.warning(f"  - {error}")
        else:
            logging.info("配置验证通过 ✓")