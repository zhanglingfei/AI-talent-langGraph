import logging
from datetime import datetime
from src.graphs.email_graph import build_email_processing_graph
from src.graphs.matching_graph import build_matching_graph
from src.models import EmailInfo
from langgraph.checkpoint import MemorySaver

class TalentMatchingSystem:
    """人才匹配系统主类"""
    
    def __init__(self):
        self.email_graph = build_email_processing_graph()
        self.matching_graph = build_matching_graph()
        self.checkpointer = MemorySaver()
        
    def process_emails(self, label: str = "all") -> dict:
        """处理邮件"""
        # 模拟邮件数据
        test_email = EmailInfo(
            id="test_001",
            subject="Java开发工程师简历",
            body="姓名：张三，5年Java开发经验...",
            timestamp=datetime.now(),
            sender="candidate@example.com",
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
        config = {"configurable": {"thread_id": "email_processing"}}
        result = self.email_graph.invoke(initial_state, config)
        
        return {
            "processed": 1,
            "errors": result.get("errors", []),
            "log": result.get("processing_log", [])
        }
    def match_project_with_candidates(self, project_id: str) -> dict:
        # 缺少实现，需要添加：
        initial_state = {
            "match_type": "project_to_resume",
            "match_query_id": project_id,
            "prefiltered_items": [],
            "match_results": [],
            "errors": [],
            "processing_log": [],
            "retry_count": 0
        }
        config = {"configurable": {"thread_id": f"match_{project_id}"}}
        result = self.matching_graph.invoke(initial_state, config)
        return {
            "matches": result.get("match_results", []),
            "errors": result.get("errors", []),
            "log": result.get("processing_log", [])
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 初始化系统
    system = TalentMatchingSystem()
    
    # 处理邮件
    print("处理邮件...")
    result = system.process_emails()
    print(f"处理完成: {result}")