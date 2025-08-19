"""
LangGraph工作流定义模块
包含邮件处理和人才匹配的工作流图
"""

from src.graphs.email_graph import build_email_processing_graph
from src.graphs.matching_graph import build_matching_graph
from src.graphs.states import GraphState

__all__ = [
    "build_email_processing_graph",
    "build_matching_graph", 
    "GraphState"
]