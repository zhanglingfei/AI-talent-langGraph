"""
匹配工作流图定义
"""

from langgraph.graph import StateGraph, END
from src.graphs.states import GraphState
from src.nodes.matching_nodes import MatchingEngine
from src.nodes.persistence_nodes import DataPersistence

def build_matching_graph() -> StateGraph:
    """构建匹配流程图"""
    
    # 初始化处理器
    matching_engine = MatchingEngine()
    data_persistence = DataPersistence()
    
    # 创建图
    workflow = StateGraph(GraphState)
    
    # 添加节点
    workflow.add_node("prefilter_candidates", matching_engine.prefilter_candidates)
    workflow.add_node("prefilter_projects", matching_engine.prefilter_projects)
    workflow.add_node("ai_matching", matching_engine.ai_matching)
    workflow.add_node("save_results", data_persistence.save_match_results)
    
    # 路由逻辑
    def route_prefilter(state: GraphState) -> str:
        if state.get("match_type") == "project_to_resume":
            return "prefilter_candidates"
        else:
            return "prefilter_projects"
    
    # 设置条件入口点
    workflow.set_conditional_entry_point(
        route_prefilter,
        {
            "prefilter_candidates": "prefilter_candidates",
            "prefilter_projects": "prefilter_projects"
        }
    )
    
    # 预筛选后进入AI匹配
    workflow.add_edge("prefilter_candidates", "ai_matching")
    workflow.add_edge("prefilter_projects", "ai_matching")
    
    # AI匹配后保存结果
    workflow.add_edge("ai_matching", "save_results")
    workflow.add_edge("save_results", END)
    
    return workflow.compile()