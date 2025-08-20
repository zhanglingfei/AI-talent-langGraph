import logging
from datetime import datetime
from src.graphs.email_graph import build_email_processing_graph
from src.graphs.matching_graph import build_matching_graph
from src.models import EmailInfo
from src.config import Config
from langgraph.checkpoint import MemorySaver

class TalentMatchingSystem:
    """人才匹配系统主类"""
    
    def __init__(self):
        # 验证配置
        Config.log_config_status()
        
        # 检查关键配置
        if not Config.OPENAI_API_KEY:
            logging.warning("OpenAI API Key未配置，某些功能可能无法正常工作")
        
        self.email_graph = build_email_processing_graph()
        self.matching_graph = build_matching_graph()
        self.checkpointer = MemorySaver()
        
        logging.info("TalentMatchingSystem 初始化完成")
        
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
        """项目匹配候选人"""
        initial_state = {
            "match_type": "project_to_resume",
            "match_query_id": project_id,
            "prefiltered_items": [],
            "match_results": [],
            "errors": [],
            "processing_log": [],
            "retry_count": 0,
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "project_info": None,
            "next_step": None,
            "batch_complete": False
        }
        config = {"configurable": {"thread_id": f"match_project_{project_id}"}}
        result = self.matching_graph.invoke(initial_state, config)
        return {
            "matches": result.get("match_results", []),
            "errors": result.get("errors", []),
            "log": result.get("processing_log", [])
        }
    
    def match_candidate_with_projects(self, candidate_id: str) -> dict:
        """候选人匹配项目"""
        initial_state = {
            "match_type": "resume_to_project",
            "match_query_id": candidate_id,
            "prefiltered_items": [],
            "match_results": [],
            "errors": [],
            "processing_log": [],
            "retry_count": 0,
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "project_info": None,
            "next_step": None,
            "batch_complete": False
        }
        config = {"configurable": {"thread_id": f"match_candidate_{candidate_id}"}}
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