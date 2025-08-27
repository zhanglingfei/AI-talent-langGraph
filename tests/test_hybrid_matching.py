"""
混合评分和多阶段筛选的测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.nodes.matching_nodes import MatchingEngine
from src.services.business_rules_scorer import BusinessRulesScorer
from src.models import CandidateInfo, ProjectInfo, MatchResult
from src.graphs.matching_graph import build_matching_graph, build_advanced_matching_graph, build_simple_matching_graph


class TestBusinessRulesScorer:
    """测试业务规则评分器"""
    
    def setup_method(self):
        """测试设置"""
        self.scorer = BusinessRulesScorer()
    
    def test_extract_experience_years(self):
        """测试经验年限提取"""
        test_cases = [
            ("5年", 5),
            ("3-5年", 5),  # 取上限
            ("2年以上", 2),
            ("senior", 5),
            ("初级", 1),
            ("中级", 3),
            ("", 0)
        ]
        
        for input_text, expected in test_cases:
            result = self.scorer._extract_experience_years(input_text)
            assert result == expected, f"输入 '{input_text}' 期望 {expected}，实际 {result}"
    
    def test_calculate_skill_score(self):
        """测试技能匹配分数计算"""
        candidate_skills = "Java, Spring Boot, MySQL, Python"
        project_requirements = "需要Java开发工程师，熟悉Spring框架"
        
        score = self.scorer._calculate_skill_score(candidate_skills, project_requirements)
        
        # Java技能匹配，应该有较高分数
        assert score >= 20
        assert score <= 40
    
    def test_calculate_business_score(self):
        """测试完整业务规则评分"""
        candidate = {
            "name": "张三",
            "title": "Java开发工程师", 
            "skills": "Java, Spring Boot, MySQL",
            "experience_years": "5年",
            "education": "本科",
            "certificates": "AWS认证",
            "location_preference": "北京"
        }
        
        project = {
            "title": "电商平台开发",
            "type": "Web开发",
            "tech_requirements": "Java, Spring Boot, 需要5年以上经验",
            "work_style": "远程工作"
        }
        
        score, reason = self.scorer.calculate_business_score(candidate, project)
        
        assert 0 <= score <= 100
        assert "业务规则评分" in reason
        assert "技能匹配" in reason
    
    def test_hard_filter_location(self):
        """测试地点硬过滤"""
        candidates = [
            {"id": "C001", "name": "张三", "location_preference": "北京"},
            {"id": "C002", "name": "李四", "location_preference": "上海"},
            {"id": "C003", "name": "王五", "location_preference": "深圳"}
        ]
        
        requirements = {"location": "北京"}
        
        filtered = self.scorer.apply_hard_filters(candidates, requirements)
        
        # 只有北京的候选人应该通过
        assert len(filtered) == 1
        assert filtered[0]["name"] == "张三"
    
    def test_hard_filter_experience(self):
        """测试经验硬过滤"""
        candidates = [
            {"id": "C001", "name": "张三", "experience_years": "5年"},
            {"id": "C002", "name": "李四", "experience_years": "2年"},
            {"id": "C003", "name": "王五", "experience_years": "8年"}
        ]
        
        requirements = {"min_experience_years": 3}
        
        filtered = self.scorer.apply_hard_filters(candidates, requirements)
        
        # 只有3年以上经验的候选人应该通过
        assert len(filtered) == 2
        names = {c["name"] for c in filtered}
        assert "张三" in names
        assert "王五" in names


class TestHybridMatching:
    """测试混合评分匹配"""
    
    def setup_method(self):
        """测试设置"""
        self.engine = MatchingEngine(use_vector_search=True)
    
    def test_hybrid_matching_success(self):
        """测试混合评分匹配 - 成功情况"""
        # 模拟预筛选结果
        state = {
            "prefiltered_items": [
                {
                    "id": "C001",
                    "name": "张三",
                    "title": "Java工程师",
                    "skills": "Java, Spring",
                    "experience_years": "5年",
                    "similarity_score": 0.85,
                    "point_id": "uuid-001"
                }
            ],
            "project_info": ProjectInfo(
                id="PROJ_001",
                title="电商平台开发",
                type="Web开发",
                tech_requirements="Java, Spring Boot",
                description="开发一个电商平台",
                budget="50万",
                duration="6个月",
                start_time="2024年1月",
                work_style="远程"
            ),
            "processing_log": [],
            "errors": [],
            "match_results": []
        }
        
        # 模拟AI评分
        with patch.object(self.engine, '_get_ai_score') as mock_ai:
            mock_ai.return_value = (80, "技能匹配度高")
            
            # 模拟业务规则评分
            with patch.object(self.engine.business_scorer, 'calculate_business_score') as mock_business:
                mock_business.return_value = (75, "业务规则匹配良好")
                
                result = self.engine.hybrid_matching(state)
                
                # 验证混合评分结果
                assert len(result["match_results"]) == 1
                match = result["match_results"][0]
                
                # 验证综合分数计算
                # 向量: 85 * 0.3 = 25.5
                # AI: 80 * 0.4 = 32.0  
                # 业务: 75 * 0.3 = 22.5
                # 总分: 25.5 + 32.0 + 22.5 = 80.0
                assert match.score == 80
                assert "混合评分" in match.reason
                assert "向量" in match.reason
                assert "AI" in match.reason
                assert "业务" in match.reason
    
    def test_hybrid_matching_fallback(self):
        """测试混合评分匹配 - 降级情况"""
        state = {
            "prefiltered_items": [
                {
                    "id": "C001",
                    "name": "张三",
                    "similarity_score": 0.75,
                    "point_id": "uuid-001"
                }
            ],
            "project_info": None,  # 无项目信息
            "processing_log": [],
            "errors": [],
            "match_results": []
        }
        
        # 模拟混合评分失败
        with patch.object(self.engine.business_scorer, 'calculate_business_score') as mock_business:
            mock_business.side_effect = Exception("业务评分失败")
            
            # 应该降级到向量相似度匹配
            with patch.object(self.engine, 'vector_similarity_matching') as mock_vector:
                mock_vector.return_value = state
                
                result = self.engine.hybrid_matching(state)
                
                # 验证降级处理
                assert len(result["errors"]) > 0
                assert any("混合评分匹配失败" in error for error in result["errors"])
                mock_vector.assert_called_once()


class TestMultiStageFiltering:
    """测试多阶段筛选"""
    
    def setup_method(self):
        """测试设置"""
        self.engine = MatchingEngine(use_vector_search=True)
    
    def test_hard_filter_candidates(self):
        """测试硬条件过滤候选人"""
        state = {
            "project_requirements": {
                "location": "北京",
                "min_experience_years": 3,
                "required_skills": ["Java"]
            },
            "processing_log": [],
            "errors": [],
            "hard_filtered_items": []
        }
        
        # 模拟Qdrant搜索结果
        mock_candidates = [
            {"id": "C001", "name": "张三", "location_preference": "北京", "experience_years": "5年", "skills": "Java, Spring"},
            {"id": "C002", "name": "李四", "location_preference": "上海", "experience_years": "3年", "skills": "Python"},
            {"id": "C003", "name": "王五", "location_preference": "北京", "experience_years": "2年", "skills": "Java"}
        ]
        
        with patch.object(self.engine.qdrant_service, 'search_candidates') as mock_search:
            mock_search.return_value = mock_candidates
            
            result = self.engine.hard_filter_candidates(state)
            
            # 验证硬条件过滤结果
            filtered = result["hard_filtered_items"]
            assert len(filtered) == 1  # 只有张三满足所有条件
            assert filtered[0]["name"] == "张三"
            assert any("硬条件过滤完成" in log for log in result["processing_log"])
    
    def test_vector_prefilter_candidates(self):
        """测试向量预筛选候选人"""
        state = {
            "query": "Python开发工程师",
            "hard_filtered_items": [
                {"id": "C001", "name": "张三", "point_id": "uuid-001"},
                {"id": "C002", "name": "李四", "point_id": "uuid-002"}
            ],
            "processing_log": [],
            "errors": [],
            "prefiltered_items": []
        }
        
        # 模拟向量搜索结果
        mock_vector_results = [
            {"id": "C001", "name": "张三", "point_id": "uuid-001", "similarity_score": 0.9},
            {"id": "C003", "name": "王五", "point_id": "uuid-003", "similarity_score": 0.8}  # 不在硬条件过滤结果中
        ]
        
        with patch.object(self.engine.qdrant_service, 'search_candidates') as mock_search:
            mock_search.return_value = mock_vector_results
            
            result = self.engine.vector_prefilter_candidates(state)
            
            # 验证向量预筛选结果 - 应该只包含通过硬条件的候选人
            filtered = result["prefiltered_items"]
            assert len(filtered) == 1
            assert filtered[0]["name"] == "张三"
            assert any("向量预筛选完成" in log for log in result["processing_log"])


class TestMatchingGraphs:
    """测试匹配流程图"""
    
    def test_build_advanced_matching_graph(self):
        """测试构建高级匹配流程图"""
        graph = build_advanced_matching_graph()
        assert graph is not None
        
        # 验证图包含预期的节点
        # 注意：langgraph的内部结构可能不同，这里只做基本验证
        assert callable(graph.invoke)
    
    def test_build_simple_matching_graph(self):
        """测试构建简单匹配流程图"""
        graph = build_simple_matching_graph()
        assert graph is not None
        assert callable(graph.invoke)
    
    def test_matching_graph_execution(self):
        """测试匹配流程图执行"""
        # 这个测试需要完整的集成环境，这里只做基本结构测试
        graph = build_matching_graph()
        
        # 构造最小化的测试状态
        test_state = {
            "match_type": "project_to_resume",
            "use_advanced_matching": True,
            "use_hybrid_matching": True,
            "query": "Python开发工程师",
            "project_requirements": {"location": "北京"},
            "processing_log": [],
            "errors": [],
            "match_results": []
        }
        
        # 由于需要外部依赖（Qdrant、OpenAI），这里只验证图结构
        assert graph is not None
        # 在实际环境中可以执行：
        # result = graph.invoke(test_state)
        # assert "match_results" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])