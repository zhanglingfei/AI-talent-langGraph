from langgraph.graph import StateGraph, END
from src.graphs.states import GraphState
from src.nodes.email_nodes import EmailProcessor
from src.nodes.persistence_nodes import DataPersistence
from src.models import EmailType

def route_after_classification(state: GraphState) -> str:
    """分类后的路由决策"""
    email_type = state.get("email_type")
    confidence = state.get("classification_confidence", 0)
    
    if confidence < 0.6:
        return "end"
    
    if email_type == EmailType.CANDIDATE:
        return "extract_candidate"
    elif email_type == EmailType.PROJECT:
        return "extract_project"
    else:
        return "end"

def build_email_processing_graph() -> StateGraph:
    """构建邮件处理图"""
    
    # 初始化处理器
    email_processor = EmailProcessor()
    data_persistence = DataPersistence()
    
    # 创建图
    workflow = StateGraph(GraphState)
    
    # 添加节点
    workflow.add_node("classify", email_processor.classify_email)
    workflow.add_node("extract_candidate", email_processor.extract_candidate_info)
    workflow.add_node("extract_project", email_processor.extract_project_info)
    workflow.add_node("save_candidate", data_persistence.save_candidate)
    workflow.add_node("save_project", data_persistence.save_project)
    
    # 设置入口
    workflow.set_entry_point("classify")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "classify",
        route_after_classification,
        {
            "extract_candidate": "extract_candidate",
            "extract_project": "extract_project",
            "end": END
        }
    )
    
    # 保存后结束
    workflow.add_edge("extract_candidate", "save_candidate")
    workflow.add_edge("extract_project", "save_project")
    workflow.add_edge("save_candidate", END)
    workflow.add_edge("save_project", END)
    
    return workflow.compile()