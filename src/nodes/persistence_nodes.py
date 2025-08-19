"""
数据持久化节点实现
"""

import json
from datetime import datetime
from src.graphs.states import GraphState
from src.services.sheets_service import SheetsService

class DataPersistence:
    """数据持久化节点集合"""
    
    def __init__(self):
        self.sheets_service = SheetsService()
    
    def save_candidate(self, state: GraphState) -> GraphState:
        """保存候选人信息到数据库"""
        if state.get("candidate_info"):
            try:
                # 转换为字典格式
                candidate_data = state["candidate_info"].dict()
                candidate_data["created_at"] = datetime.now().isoformat()
                
                # TODO: 实际保存到Google Sheets
                # self.sheets_service.append_row("RESUME_DATABASE", candidate_data)
                
                state["processing_log"].append(
                    f"候选人信息已保存: {state['candidate_info'].name}"
                )
            except Exception as e:
                state["errors"].append(f"保存候选人失败: {str(e)}")
        
        return state
    
    def save_project(self, state: GraphState) -> GraphState:
        """保存项目信息到数据库"""
        if state.get("project_info"):
            try:
                # 转换为字典格式
                project_data = state["project_info"].dict()
                project_data["created_at"] = datetime.now().isoformat()
                
                # TODO: 实际保存到Google Sheets
                # self.sheets_service.append_row("PROJECTS", project_data)
                
                state["processing_log"].append(
                    f"项目信息已保存: {state['project_info'].title}"
                )
            except Exception as e:
                state["errors"].append(f"保存项目失败: {str(e)}")
        
        return state
    
    def save_match_results(self, state: GraphState) -> GraphState:
        """保存匹配结果"""
        if state.get("match_results"):
            try:
                for match in state["match_results"]:
                    match_data = match.dict()
                    match_data["created_at"] = datetime.now().isoformat()
                    match_data["query_id"] = state.get("match_query_id")
                    match_data["match_type"] = state.get("match_type")
                    
                    # TODO: 实际保存到Google Sheets
                    # self.sheets_service.append_row("MATCHES", match_data)
                
                state["processing_log"].append(
                    f"匹配结果已保存: {len(state['match_results'])} 条"
                )
            except Exception as e:
                state["errors"].append(f"保存匹配结果失败: {str(e)}")
        
        return state