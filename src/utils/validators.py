"""数据验证工具"""

import re
from typing import Dict, Any

def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_candidate_data(data: Dict[str, Any]) -> bool:
    """验证候选人数据完整性"""
    required_fields = ['name', 'experience_years', 'skills']
    return all(field in data and data[field] for field in required_fields)