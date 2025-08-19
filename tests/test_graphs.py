"""
工作流图测试
"""

import pytest
from datetime import datetime
from src.graphs.email_graph import build_email_processing_graph
from src.graphs.matching_graph import build_matching_graph
from src.models import EmailInfo

def test_email_processing_graph():
    """测试邮件处理工作流"""
    graph = build_email_processing_graph()
    
    test_email = EmailInfo(
        id="test_001",
        subject="Python开发工程师简历",
        body="5年Python开发经验，熟悉Django、FastAPI",
        timestamp=datetime.now(),
        sender="test@example.com",
        has_attachment=True
    )
    
    initial_state = {
        "emails": [test_email],
        "current_email": test_email,
        "errors": [],
        "processing_log": [],
        "retry_count": 0,
        "batch_complete": False
    }
    
    # 运行图
    result = graph.invoke(initial_state)
    
    # 验证结果
    assert "processing_log" in result
    assert len(result["processing_log"]) > 0
    assert "errors" in result

def test_matching_graph():
    """测试匹配工作流"""
    graph = build_matching_graph()
    
    initial_state = {
        "match_type": "project_to_resume",
        "match_query_id": "PROJ_001",
        "prefiltered_items": [],
        "match_results": [],
        "errors": [],
        "processing_log": [],
        "retry_count": 0
    }
    
    # 运行图
    result = graph.invoke(initial_state)
    
    # 验证结果
    assert "match_results" in result
    assert "processing_log" in result
    assert len(result["processing_log"]) > 0

if __name__ == "__main__":
    test_email_processing_graph()
    test_matching_graph()
    print("所有测试通过!")