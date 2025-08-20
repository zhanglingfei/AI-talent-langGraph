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
                candidate_data = state["candidate_info"].model_dump()
                candidate_data["created_at"] = datetime.now().isoformat()
                
                # 保存到Google Sheets
                try:
                    self.sheets_service.append_candidate_data(candidate_data)
                    state["processing_log"].append(
                        f"候选人信息已保存到Google Sheets: {state['candidate_info'].name}"
                    )
                except Exception as sheets_error:
                    # 如果Google Sheets保存失败，记录错误但不中断流程
                    state["processing_log"].append(
                        f"Google Sheets保存失败，但候选人信息已处理: {state['candidate_info'].name}"
                    )
                    state["errors"].append(f"Google Sheets保存失败: {str(sheets_error)}")
                    
            except Exception as e:
                state["errors"].append(f"保存候选人失败: {str(e)}")
        else:
            state["processing_log"].append("无候选人信息需要保存")
        
        return state
    
    def save_project(self, state: GraphState) -> GraphState:
        """保存项目信息到数据库"""
        if state.get("project_info"):
            try:
                # 转换为字典格式
                project_data = state["project_info"].model_dump()
                project_data["created_at"] = datetime.now().isoformat()
                
                # 保存到Google Sheets
                try:
                    self.sheets_service.append_project_data(project_data)
                    state["processing_log"].append(
                        f"项目信息已保存到Google Sheets: {state['project_info'].title}"
                    )
                except Exception as sheets_error:
                    # 如果Google Sheets保存失败，记录错误但不中断流程
                    state["processing_log"].append(
                        f"Google Sheets保存失败，但项目信息已处理: {state['project_info'].title}"
                    )
                    state["errors"].append(f"Google Sheets保存失败: {str(sheets_error)}")
                    
            except Exception as e:
                state["errors"].append(f"保存项目失败: {str(e)}")
        else:
            state["processing_log"].append("无项目信息需要保存")
        
        return state
    
    def save_match_results(self, state: GraphState) -> GraphState:
        """保存匹配结果"""
        if state.get("match_results") and len(state["match_results"]) > 0:
            try:
                match_count = 0
                for match in state["match_results"]:
                    match_data = match.model_dump()
                    match_data["created_at"] = datetime.now().isoformat()
                    match_data["query_id"] = state.get("match_query_id", "unknown")
                    match_data["match_type"] = state.get("match_type", "unknown")
                    
                    # 保存到Google Sheets
                    try:
                        self.sheets_service.append_match_data(match_data)
                        match_count += 1
                    except Exception as sheets_error:
                        state["errors"].append(f"保存匹配结果失败 {match.id}: {str(sheets_error)}")
                
                if match_count > 0:
                    state["processing_log"].append(
                        f"匹配结果已保存到Google Sheets: {match_count}/{len(state['match_results'])} 条"
                    )
                else:
                    state["processing_log"].append("匹配结果保存失败，但处理完成")
                    
            except Exception as e:
                state["errors"].append(f"保存匹配结果失败: {str(e)}")
        else:
            state["processing_log"].append("无匹配结果需要保存")
        
        return state