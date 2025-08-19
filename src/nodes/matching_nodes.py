"""
匹配引擎节点实现
"""

import json
from typing import List, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from src.config import Config
from src.graphs.states import GraphState
from src.models import MatchResult

class MatchingEngine:
    """匹配引擎节点集合"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.05,
            api_key=Config.OPENAI_API_KEY
        )
        
    def prefilter_candidates(self, state: GraphState) -> GraphState:
        """预筛选候选人节点"""
        state["processing_log"].append("执行候选人预筛选")
        
        # TODO: 从数据库读取候选人并进行初步筛选
        # 这里返回模拟数据
        state["prefiltered_items"] = [
            {"id": "C001", "name": "张三", "skills": "Java, Spring"},
            {"id": "C002", "name": "李四", "skills": "Python, Django"}
        ]
        
        return state
    
    def prefilter_projects(self, state: GraphState) -> GraphState:
        """预筛选项目节点"""
        state["processing_log"].append("执行项目预筛选")
        
        # TODO: 从数据库读取项目并进行初步筛选
        state["prefiltered_items"] = [
            {"id": "P001", "title": "电商平台开发", "tech": "Java"},
            {"id": "P002", "title": "数据分析平台", "tech": "Python"}
        ]
        
        return state
    
    def ai_matching(self, state: GraphState) -> GraphState:
        """AI智能匹配节点"""
        
        if not state["prefiltered_items"]:
            state["match_results"] = []
            return state
            
        matching_prompt = ChatPromptTemplate.from_template("""
        基于以下信息进行智能匹配：
        
        匹配类型: {match_type}
        查询ID: {query_id}
        
        待匹配项目列表:
        {items}
        
        请返回最匹配的前3个结果，格式如下：
        {{
            "matches": [
                {{
                    "id": "ID",
                    "name": "名称",
                    "score": 85,
                    "reason": "匹配原因"
                }}
            ]
        }}
        """)
        
        chain = matching_prompt | self.llm | JsonOutputParser()
        
        try:
            result = chain.invoke({
                "match_type": state["match_type"],
                "query_id": state["match_query_id"],
                "items": json.dumps(state["prefiltered_items"], ensure_ascii=False)
            })
            
            matches = [MatchResult(**match) for match in result.get("matches", [])]
            state["match_results"] = matches
            state["processing_log"].append(f"AI匹配完成，找到 {len(matches)} 个匹配结果")
            
        except Exception as e:
            state["errors"].append(f"AI匹配失败: {str(e)}")
            state["match_results"] = []
            
        return state