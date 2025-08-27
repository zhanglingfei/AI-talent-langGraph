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
from src.services.qdrant_service import QdrantService
from src.services.business_rules_scorer import BusinessRulesScorer
from src.utils.logger import setup_logger
from typing import Tuple

logger = setup_logger(__name__)

class MatchingEngine:
    """匹配引擎节点集合"""
    
    def __init__(self, use_vector_search=True):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.05,
            api_key=Config.OPENAI_API_KEY
        )
        self.use_vector_search = use_vector_search
        if use_vector_search:
            self.qdrant_service = QdrantService()
        self.business_scorer = BusinessRulesScorer()
        
    def prefilter_candidates(self, state: GraphState) -> GraphState:
        """预筛选候选人节点"""
        state["processing_log"].append("执行候选人预筛选")
        
        try:
            if self.use_vector_search:
                # 使用向量搜索进行预筛选
                query = state.get("query", "")
                if query:
                    candidates = self.qdrant_service.search_candidates(
                        query=query, 
                        limit=10, 
                        score_threshold=0.6
                    )
                    state["prefiltered_items"] = candidates
                    state["processing_log"].append(f"向量搜索候选人完成: {len(candidates)} 个")
                else:
                    # 没有查询条件，返回空结果
                    state["prefiltered_items"] = []
                    state["processing_log"].append("无查询条件，跳过候选人预筛选")
            else:
                # 备用：使用传统方法
                from src.services.sheets_service import SheetsService
                sheets_service = SheetsService()
                candidates = sheets_service.get_candidates()
                
                if candidates:
                    filtered_candidates = candidates[:10]
                    state["prefiltered_items"] = filtered_candidates
                    state["processing_log"].append(f"预筛选候选人完成: {len(filtered_candidates)} 个")
                else:
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
            if self.use_vector_search:
                # 使用向量搜索进行预筛选
                query = state.get("query", "")
                if query:
                    projects = self.qdrant_service.search_projects(
                        query=query, 
                        limit=10, 
                        score_threshold=0.6
                    )
                    state["prefiltered_items"] = projects
                    state["processing_log"].append(f"向量搜索项目完成: {len(projects)} 个")
                else:
                    # 没有查询条件，返回空结果
                    state["prefiltered_items"] = []
                    state["processing_log"].append("无查询条件，跳过项目预筛选")
            else:
                # 备用：使用传统方法
                from src.services.sheets_service import SheetsService
                sheets_service = SheetsService()
                projects = sheets_service.get_projects()
                
                if projects:
                    filtered_projects = projects[:10]
                    state["prefiltered_items"] = filtered_projects
                    state["processing_log"].append(f"预筛选项目完成: {len(filtered_projects)} 个")
                else:
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
    
    def hard_filter_candidates(self, state: GraphState) -> GraphState:
        """硬条件过滤候选人"""
        state["processing_log"].append("执行硬条件过滤")
        
        try:
            if self.use_vector_search:
                # 从Qdrant获取所有候选人
                all_candidates = self.qdrant_service.search_candidates(
                    query="",  # 空查询获取所有
                    limit=100,
                    score_threshold=0.0  # 不过滤相似度
                )
            else:
                # 从Google Sheets获取候选人
                from src.services.sheets_service import SheetsService
                sheets_service = SheetsService()
                all_candidates = sheets_service.get_candidates()
            
            # 获取项目要求
            project_requirements = state.get("project_requirements", {})
            
            # 应用硬性过滤
            filtered_candidates = self.business_scorer.apply_hard_filters(
                all_candidates, 
                project_requirements
            )
            
            state["hard_filtered_items"] = filtered_candidates
            state["processing_log"].append(f"硬条件过滤完成: {len(filtered_candidates)} 个候选人")
            
        except Exception as e:
            state["errors"].append(f"硬条件过滤失败: {str(e)}")
            state["hard_filtered_items"] = []
        
        return state
    
    def vector_prefilter_candidates(self, state: GraphState) -> GraphState:
        """向量预筛选候选人"""
        state["processing_log"].append("执行向量预筛选")
        
        if not self.use_vector_search:
            # 如果不使用向量搜索，直接使用硬条件过滤的结果
            state["prefiltered_items"] = state.get("hard_filtered_items", [])
            state["processing_log"].append("向量搜索未启用，使用硬条件过滤结果")
            return state
        
        try:
            query = state.get("query", "")
            hard_filtered = state.get("hard_filtered_items", [])
            
            if not query:
                state["prefiltered_items"] = hard_filtered[:10]
                state["processing_log"].append("无查询条件，直接使用硬条件过滤结果")
                return state
            
            # 对硬条件过滤后的候选人进行向量搜索
            # 这里简化处理，在实际应用中可以实现更精确的向量筛选
            vector_results = self.qdrant_service.search_candidates(
                query=query,
                limit=20,
                score_threshold=0.6
            )
            
            # 取交集：既通过硬条件又通过向量搜索的候选人
            hard_filtered_ids = {item.get("id", item.get("point_id")) for item in hard_filtered}
            vector_filtered = []
            
            for result in vector_results:
                result_id = result.get("id", result.get("point_id"))
                if result_id in hard_filtered_ids:
                    vector_filtered.append(result)
            
            state["prefiltered_items"] = vector_filtered[:10]
            state["processing_log"].append(f"向量预筛选完成: {len(vector_filtered)} 个候选人")
            
        except Exception as e:
            state["errors"].append(f"向量预筛选失败: {str(e)}")
            # 降级到硬条件过滤结果
            state["prefiltered_items"] = state.get("hard_filtered_items", [])[:10]
        
        return state
    
    def vector_similarity_matching(self, state: GraphState) -> GraphState:
        """基于向量相似度的直接匹配"""
        if not self.use_vector_search:
            state["processing_log"].append("向量搜索未启用，跳过相似度匹配")
            return state
        
        prefiltered_items = state.get("prefiltered_items", [])
        if not prefiltered_items:
            state["match_results"] = []
            state["processing_log"].append("无预筛选项目，跳过相似度匹配")
            return state
        
        try:
            matches = []
            for item in prefiltered_items[:5]:  # 限制处理数量
                # 将相似度分数转换为匹配结果
                similarity_score = item.get("similarity_score", 0.7)
                match_score = int(similarity_score * 100)  # 转换为0-100分
                
                match_result = MatchResult(
                    id=item.get("point_id", item.get("id", "unknown")),
                    name=item.get("name", item.get("title", "未知")),
                    score=match_score,
                    reason=f"向量相似度匹配 (相似度: {similarity_score:.3f})"
                )
                matches.append(match_result)
            
            # 按分数排序
            matches.sort(key=lambda x: x.score, reverse=True)
            state["match_results"] = matches
            state["processing_log"].append(f"向量相似度匹配完成: {len(matches)} 个结果")
            
        except Exception as e:
            state["errors"].append(f"向量相似度匹配失败: {str(e)}")
            state["match_results"] = []
        
        return state
    
    def hybrid_matching(self, state: GraphState) -> GraphState:
        """混合评分匹配：向量相似度 + AI评分 + 业务规则"""
        state["processing_log"].append("执行混合评分匹配")
        
        prefiltered_items = state.get("prefiltered_items", [])
        if not prefiltered_items:
            state["match_results"] = []
            state["processing_log"].append("无预筛选项目，跳过混合匹配")
            return state
        
        try:
            hybrid_matches = []
            project_info = state.get("project_info") or self._get_project_info_from_state(state)
            
            for item in prefiltered_items[:5]:  # 限制处理数量
                # 获取权重配置 - 支持动态调整
                vector_weight = Config.MATCHING_WEIGHTS["HYBRID_VECTOR"] 
                ai_weight = Config.MATCHING_WEIGHTS["HYBRID_AI"]
                business_weight = Config.MATCHING_WEIGHTS["HYBRID_BUSINESS"]
                
                # 1. 向量相似度分数 
                vector_score = item.get("final_score", item.get("similarity_score", 0.7)) * 100
                
                # 2. AI评分
                ai_score, ai_reason = self._get_ai_score(item, project_info)
                
                # 3. 业务规则评分
                business_score, business_reason = self.business_scorer.calculate_business_score(
                    item, project_info.model_dump() if project_info else {}
                )
                
                # 计算综合分数
                final_score = (
                    vector_score * vector_weight +
                    ai_score * ai_weight +
                    business_score * business_weight
                )
                
                # 构建综合匹配原因
                hybrid_reason = f"混合评分 [向量:{vector_score:.1f}({vector_weight*100:.0f}%) | AI:{ai_score}({ai_weight*100:.0f}%) | 业务:{business_score}({business_weight*100:.0f}%)] = {final_score:.1f}"
                
                match_result = MatchResult(
                    id=item.get("point_id", item.get("id", "unknown")),
                    name=item.get("name", item.get("title", "未知")),
                    score=int(final_score),
                    reason=hybrid_reason
                )
                hybrid_matches.append(match_result)
            
            # 按综合分数排序
            hybrid_matches.sort(key=lambda x: x.score, reverse=True)
            state["match_results"] = hybrid_matches
            state["processing_log"].append(f"混合评分匹配完成: {len(hybrid_matches)} 个结果")
            
        except Exception as e:
            state["errors"].append(f"混合评分匹配失败: {str(e)}")
            # 降级到向量相似度匹配
            state = self.vector_similarity_matching(state)
        
        return state
    
    def _get_ai_score(self, candidate_item: Dict[str, Any], project_info) -> Tuple[int, str]:
        """获取AI评分"""
        if not project_info:
            return 60, "无项目信息，给予基础分"
        
        try:
            # 构造简化的匹配prompt
            matching_prompt = ChatPromptTemplate.from_template("""
            请为以下候选人和项目的匹配度打分（0-100分）：
            
            候选人信息：
            姓名: {candidate_name}
            职位: {candidate_title}
            技能: {candidate_skills}
            经验: {candidate_experience}
            
            项目需求：
            项目: {project_title}
            类型: {project_type}
            技术要求: {project_tech}
            描述: {project_desc}
            
            评分标准：
            - 技能匹配度 (40%)
            - 经验相关性 (30%) 
            - 其他因素 (30%)
            
            请返回JSON格式：
            {{"score": 85, "reason": "详细匹配原因"}}
            """)
            
            chain = matching_prompt | self.llm | JsonOutputParser()
            
            result = chain.invoke({
                "candidate_name": candidate_item.get("name", ""),
                "candidate_title": candidate_item.get("title", ""),
                "candidate_skills": candidate_item.get("skills", ""),
                "candidate_experience": candidate_item.get("experience_years", ""),
                "project_title": project_info.title,
                "project_type": project_info.type,
                "project_tech": project_info.tech_requirements,
                "project_desc": project_info.description[:200]  # 限制长度
            })
            
            return result.get("score", 60), result.get("reason", "AI评分")
            
        except Exception as e:
            logger.warning(f"AI评分失败: {str(e)}")
            return 60, "AI评分失败，给予基础分"
    
    def _get_project_info_from_state(self, state: GraphState):
        """从state中获取项目信息"""
        # 尝试从不同的state字段获取项目信息
        project_data = state.get("current_project") or state.get("query_project")
        if project_data:
            from src.models import ProjectInfo
            return ProjectInfo(**project_data)
        return None
    
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