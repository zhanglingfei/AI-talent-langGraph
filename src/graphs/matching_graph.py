"""
匹配工作流图定义
"""

from langgraph.graph import StateGraph, END
from src.graphs.states import GraphState
from src.nodes.matching_nodes import MatchingEngine
from src.nodes.persistence_nodes import DataPersistence

def build_matching_graph() -> StateGraph:
    """构建匹配流程图 - 支持多阶段筛选和混合评分"""
    
    # 初始化处理器
    matching_engine = MatchingEngine()
    data_persistence = DataPersistence()
    
    # 创建图
    workflow = StateGraph(GraphState)
    
    # 添加多阶段筛选节点
    workflow.add_node("hard_filter", matching_engine.hard_filter_candidates)
    workflow.add_node("vector_prefilter", matching_engine.vector_prefilter_candidates)
    workflow.add_node("hybrid_matching", matching_engine.hybrid_matching)
    workflow.add_node("save_results", data_persistence.save_match_results)
    
    # 添加备用传统节点
    workflow.add_node("prefilter_candidates", matching_engine.prefilter_candidates)
    workflow.add_node("prefilter_projects", matching_engine.prefilter_projects)
    workflow.add_node("ai_matching", matching_engine.ai_matching)
    
    # 新的路由逻辑 - 支持多阶段筛选
    def route_matching_strategy(state: GraphState) -> str:
        """根据匹配类型和配置选择匹配策略"""
        use_advanced_matching = state.get("use_advanced_matching", True)
        match_type = state.get("match_type")
        
        if use_advanced_matching and match_type == "project_to_resume":
            return "hard_filter"  # 使用多阶段筛选
        elif match_type == "project_to_resume":
            return "prefilter_candidates"  # 传统候选人筛选
        else:
            return "prefilter_projects"   # 传统项目筛选
    
    def route_matching_method(state: GraphState) -> str:
        """选择匹配方法"""
        use_hybrid_matching = state.get("use_hybrid_matching", True)
        
        if use_hybrid_matching:
            return "hybrid_matching"
        else:
            return "ai_matching"
    
    # 设置条件入口点
    workflow.set_conditional_entry_point(
        route_matching_strategy,
        {
            "hard_filter": "hard_filter",
            "prefilter_candidates": "prefilter_candidates", 
            "prefilter_projects": "prefilter_projects"
        }
    )
    
    # 多阶段筛选流程：硬条件过滤 → 向量预筛选 → 混合匹配
    workflow.add_edge("hard_filter", "vector_prefilter")
    workflow.add_conditional_edges(
        "vector_prefilter",
        route_matching_method,
        {
            "hybrid_matching": "hybrid_matching",
            "ai_matching": "ai_matching"
        }
    )
    
    # 传统流程：预筛选 → AI匹配
    workflow.add_conditional_edges(
        "prefilter_candidates",
        route_matching_method,
        {
            "hybrid_matching": "hybrid_matching",
            "ai_matching": "ai_matching"
        }
    )
    workflow.add_conditional_edges(
        "prefilter_projects", 
        route_matching_method,
        {
            "hybrid_matching": "hybrid_matching",
            "ai_matching": "ai_matching"
        }
    )
    
    # 所有匹配方法最终保存结果
    workflow.add_edge("hybrid_matching", "save_results")
    workflow.add_edge("ai_matching", "save_results")
    workflow.add_edge("save_results", END)
    
    return workflow.compile()


def build_advanced_matching_graph() -> StateGraph:
    """构建高级匹配流程图 - 默认启用多阶段筛选和混合评分"""
    return build_matching_graph()


def build_simple_matching_graph() -> StateGraph:
    """构建简单匹配流程图 - 使用传统方法"""
    # 初始化处理器
    matching_engine = MatchingEngine(use_vector_search=False)
    data_persistence = DataPersistence(use_qdrant=False)
    
    # 创建简化图
    workflow = StateGraph(GraphState)
    
    # 添加传统节点
    workflow.add_node("prefilter_candidates", matching_engine.prefilter_candidates)
    workflow.add_node("prefilter_projects", matching_engine.prefilter_projects)
    workflow.add_node("ai_matching", matching_engine.ai_matching)
    workflow.add_node("save_results", data_persistence.save_match_results)
    
    # 简单路由
    def route_simple(state: GraphState) -> str:
        if state.get("match_type") == "project_to_resume":
            return "prefilter_candidates"
        else:
            return "prefilter_projects"
    
    workflow.set_conditional_entry_point(
        route_simple,
        {
            "prefilter_candidates": "prefilter_candidates",
            "prefilter_projects": "prefilter_projects"
        }
    )
    
    workflow.add_edge("prefilter_candidates", "ai_matching")
    workflow.add_edge("prefilter_projects", "ai_matching")
    workflow.add_edge("ai_matching", "save_results")
    workflow.add_edge("save_results", END)
    
    return workflow.compile()