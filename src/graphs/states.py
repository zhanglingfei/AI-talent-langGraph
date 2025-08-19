from typing import TypedDict, List, Optional
from src.models import EmailInfo, EmailType, CandidateInfo, ProjectInfo, MatchResult

class GraphState(TypedDict):
    """Graph状态定义"""
    # 输入
    emails: List[EmailInfo]
    current_email: Optional[EmailInfo]
    
    # 处理状态
    email_type: Optional[EmailType]
    classification_confidence: float
    
    # 提取的信息
    candidate_info: Optional[CandidateInfo]
    project_info: Optional[ProjectInfo]
    
    # 匹配相关
    match_type: Optional[str]
    match_query_id: Optional[str]
    prefiltered_items: List[dict]
    match_results: List[MatchResult]
    
    # 错误和日志
    errors: List[str]
    processing_log: List[str]
    
    # 控制流
    next_step: Optional[str]
    retry_count: int
    batch_complete: bool