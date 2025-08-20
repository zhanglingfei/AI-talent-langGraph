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
        
        try:
            from src.services.sheets_service import SheetsService
            sheets_service = SheetsService()
            
            # 从数据库读取候选人数据
            candidates = sheets_service.get_candidates()
            
            if candidates:
                # 简单预筛选逻辑（可以根据需要扩展）
                filtered_candidates = candidates[:10]  # 限制数量
                state["prefiltered_items"] = filtered_candidates
                state["processing_log"].append(f"预筛选候选人完成: {len(filtered_candidates)} 个")
            else:
                # 如果没有数据，使用模拟数据
                state["prefiltered_items"] = [
                    {"id": "C001", "name": "张三", "skills": "Java, Spring", "title": "Java开发工程师"},
                    {"id": "C002", "name": "李四", "skills": "Python, Django", "title": "Python开发工程师"}
                ]
                state["processing_log"].append("使用模拟候选人数据")
                
        except Exception as e:
            state["errors"].append(f"候选人预筛选失败: {str(e)}")
            # 使用备用模拟数据
            state["prefiltered_items"] = [
                {"id": "C001", "name": "张三", "skills": "Java, Spring", "title": "Java开发工程师"},
                {"id": "C002", "name": "李四", "skills": "Python, Django", "title": "Python开发工程师"}
            ]
        
        return state
    
    def prefilter_projects(self, state: GraphState) -> GraphState:
        """预筛选项目节点"""
        state["processing_log"].append("执行项目预筛选")
        
        try:
            from src.services.sheets_service import SheetsService
            sheets_service = SheetsService()
            
            # 从数据库读取项目数据
            projects = sheets_service.get_projects()
            
            if projects:
                # 简单预筛选逻辑（可以根据需要扩展）
                filtered_projects = projects[:10]  # 限制数量
                state["prefiltered_items"] = filtered_projects
                state["processing_log"].append(f"预筛选项目完成: {len(filtered_projects)} 个")
            else:
                # 如果没有数据，使用模拟数据
                state["prefiltered_items"] = [
                    {"id": "P001", "title": "电商平台开发", "tech_requirements": "Java, Spring Boot, MySQL"},
                    {"id": "P002", "title": "数据分析平台", "tech_requirements": "Python, Django, PostgreSQL"}
                ]
                state["processing_log"].append("使用模拟项目数据")
                
        except Exception as e:
            state["errors"].append(f"项目预筛选失败: {str(e)}")
            # 使用备用模拟数据
            state["prefiltered_items"] = [
                {"id": "P001", "title": "电商平台开发", "tech_requirements": "Java, Spring Boot, MySQL"},
                {"id": "P002", "title": "数据分析平台", "tech_requirements": "Python, Django, PostgreSQL"}
            ]
        
        return state
    
    def ai_matching(self, state: GraphState) -> GraphState:
        """AI智能匹配节点"""
        
        if not state["prefiltered_items"]:
            state["match_results"] = []
            state["processing_log"].append("无预筛选项目，跳过AI匹配")
            return state
            
        matching_prompt = ChatPromptTemplate.from_template("""
        基于以下信息进行智能匹配：
        
        匹配类型: {match_type}
        查询ID: {query_id}
        
        待匹配项目列表:
        {items}
        
        请返回最匹配的前3个结果，严格按照以下JSON格式返回：
        {{
            "matches": [
                {{
                    "id": "项目或候选人的ID",
                    "name": "项目标题或候选人姓名",
                    "score": 85,
                    "reason": "详细的匹配原因说明"
                }}
            ]
        }}
        
        评分标准：
        - 技能匹配度 (40%)
        - 经验相关性 (30%) 
        - 其他因素 (30%)
        
        评分范围：0-100分
        """)
        
        chain = matching_prompt | self.llm | JsonOutputParser()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 限制输入内容长度，避免token过多
                items_json = json.dumps(state["prefiltered_items"][:5], ensure_ascii=False)
                
                result = chain.invoke({
                    "match_type": state["match_type"],
                    "query_id": state["match_query_id"],
                    "items": items_json
                })
                
                # 验证返回结果格式
                if not isinstance(result, dict) or "matches" not in result:
                    raise ValueError("AI返回结果格式不正确")
                
                matches = []
                for match_data in result.get("matches", []):
                    try:
                        match = MatchResult(**match_data)
                        matches.append(match)
                    except Exception as match_error:
                        state["errors"].append(f"匹配结果格式错误: {str(match_error)}")
                        continue
                
                state["match_results"] = matches
                state["processing_log"].append(f"AI匹配完成，找到 {len(matches)} 个匹配结果")
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    state["processing_log"].append(f"AI匹配第{attempt+1}次尝试失败，重试中...")
                    continue
                else:
                    state["errors"].append(f"AI匹配失败 (已重试{max_retries}次): {str(e)}")
                    state["match_results"] = []
                    
                    # 创建备用匹配结果
                    if state["prefiltered_items"]:
                        fallback_matches = []
                        for i, item in enumerate(state["prefiltered_items"][:3]):
                            fallback_match = MatchResult(
                                id=item.get("id", f"fallback_{i}"),
                                name=item.get("name", item.get("title", "未知")),
                                score=60 - i*5,  # 递减分数
                                reason="系统备用匹配结果"
                            )
                            fallback_matches.append(fallback_match)
                        state["match_results"] = fallback_matches
                        state["processing_log"].append(f"使用备用匹配结果: {len(fallback_matches)} 个")
            
        return state