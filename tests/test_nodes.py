"""
节点功能单元测试
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from src.models import EmailInfo, EmailType, CandidateInfo, ProjectInfo, MatchResult
from src.nodes.email_nodes import EmailProcessor
from src.nodes.matching_nodes import MatchingEngine
from src.nodes.persistence_nodes import DataPersistence
from src.graphs.states import GraphState


class TestEmailProcessor:
    """测试邮件处理节点"""
    
    def setup_method(self):
        """测试设置"""
        self.processor = EmailProcessor()
        self.test_email = EmailInfo(
            id="test_001",
            subject="Java开发工程师简历",
            body="姓名：张三，5年Java开发经验，熟悉Spring Boot、MySQL",
            timestamp=datetime.now(),
            sender="zhangsan@example.com",
            has_attachment=False
        )
    
    def test_classify_email_candidate(self):
        """测试邮件分类 - 候选人类型"""
        state = {
            "current_email": self.test_email,
            "emails": [self.test_email],
            "errors": [],
            "processing_log": [],
            "retry_count": 0,
            "batch_complete": False,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "project_info": None,
            "match_type": None,
            "match_query_id": None,
            "prefiltered_items": [],
            "match_results": [],
            "next_step": None
        }
        
        with patch.object(self.processor.llm, 'invoke') as mock_llm:
            mock_llm.return_value.content = '{"type": "CANDIDATE", "confidence": 0.9, "reason": "包含简历信息"}'
            
            result = self.processor.classify_email(state)
            
            # 验证分类结果
            assert "processing_log" in result
            assert len(result["errors"]) == 0
    
    def test_extract_candidate_info_success(self):
        """测试候选人信息提取 - 成功情况"""
        state = {
            "current_email": self.test_email,
            "emails": [self.test_email],
            "errors": [],
            "processing_log": [],
            "retry_count": 0,
            "batch_complete": False,
            "email_type": EmailType.CANDIDATE,
            "classification_confidence": 0.9,
            "candidate_info": None,
            "project_info": None,
            "match_type": None,
            "match_query_id": None,
            "prefiltered_items": [],
            "match_results": [],
            "next_step": None
        }
        
        with patch.object(self.processor.llm, 'invoke') as mock_llm:
            # 模拟LLM返回候选人信息
            mock_candidate = CandidateInfo(
                id="CAND_test_001",
                name="张三",
                title="Java开发工程师",
                experience_years="5年",
                skills="Java, Spring Boot, MySQL",
                certificates="",
                education="本科",
                location_preference="北京",
                expected_salary="15k-20k",
                contact="zhangsan@example.com"
            )
            mock_llm.return_value = mock_candidate
            
            result = self.processor.extract_candidate_info(state)
            
            # 验证提取结果
            assert result["candidate_info"] is not None
            assert len(result["errors"]) == 0
    
    def test_extract_candidate_info_fallback(self):
        """测试候选人信息提取 - 失败降级情况"""
        state = {
            "current_email": self.test_email,
            "emails": [self.test_email],
            "errors": [],
            "processing_log": [],
            "retry_count": 0,
            "batch_complete": False,
            "email_type": EmailType.CANDIDATE,
            "classification_confidence": 0.9,
            "candidate_info": None,
            "project_info": None,
            "match_type": None,
            "match_query_id": None,
            "prefiltered_items": [],
            "match_results": [],
            "next_step": None
        }
        
        with patch.object(self.processor.llm, 'invoke') as mock_llm:
            # 模拟LLM调用失败
            mock_llm.side_effect = Exception("API调用失败")
            
            result = self.processor.extract_candidate_info(state)
            
            # 验证降级处理
            assert result["candidate_info"] is not None
            assert result["candidate_info"].name == "未知候选人"
            assert len(result["errors"]) > 0


class TestMatchingEngine:
    """测试匹配引擎节点"""
    
    def setup_method(self):
        """测试设置"""
        self.engine = MatchingEngine(use_vector_search=False)  # 测试时使用传统方法
        self.vector_engine = MatchingEngine(use_vector_search=True)  # 向量搜索引擎
    
    def test_prefilter_candidates_with_mock_data(self):
        """测试候选人预筛选 - 使用模拟数据"""
        state = {
            "processing_log": [],
            "errors": [],
            "prefiltered_items": [],
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "project_info": None,
            "match_type": "project_to_resume",
            "match_query_id": "PROJ_001",
            "match_results": [],
            "next_step": None,
            "retry_count": 0,
            "batch_complete": False
        }
        
        with patch('src.nodes.matching_nodes.SheetsService') as mock_service:
            # 模拟Sheets服务返回空数据
            mock_service.return_value.get_candidates.return_value = []
            
            result = self.engine.prefilter_candidates(state)
            
            # 验证预筛选结果
            assert len(result["prefiltered_items"]) > 0
            assert any("模拟候选人数据" in log for log in result["processing_log"])
    
    def test_ai_matching_success(self):
        """测试AI匹配 - 成功情况"""
        state = {
            "match_type": "project_to_resume",
            "match_query_id": "PROJ_001",
            "prefiltered_items": [
                {"id": "C001", "name": "张三", "skills": "Java, Spring"},
                {"id": "C002", "name": "李四", "skills": "Python, Django"}
            ],
            "match_results": [],
            "processing_log": [],
            "errors": [],
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "project_info": None,
            "next_step": None,
            "retry_count": 0,
            "batch_complete": False
        }
        
        with patch.object(self.engine.llm, 'invoke') as mock_llm:
            # 模拟LLM返回匹配结果
            mock_response = {
                "matches": [
                    {
                        "id": "C001",
                        "name": "张三",
                        "score": 85,
                        "reason": "Java技能匹配度高"
                    }
                ]
            }
            mock_llm.return_value = mock_response
            
            result = self.engine.ai_matching(state)
            
            # 验证匹配结果
            assert len(result["match_results"]) > 0
            assert result["match_results"][0].score == 85
            assert len(result["errors"]) == 0
    
    def test_ai_matching_with_fallback(self):
        """测试AI匹配 - 失败降级情况"""
        state = {
            "match_type": "project_to_resume",
            "match_query_id": "PROJ_001",
            "prefiltered_items": [
                {"id": "C001", "name": "张三", "skills": "Java, Spring"}
            ],
            "match_results": [],
            "processing_log": [],
            "errors": [],
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "project_info": None,
            "next_step": None,
            "retry_count": 0,
            "batch_complete": False
        }
        
        with patch.object(self.engine.llm, 'invoke') as mock_llm:
            # 模拟LLM调用失败
            mock_llm.side_effect = Exception("API调用失败")
            
            result = self.engine.ai_matching(state)
            
            # 验证降级处理
            assert len(result["match_results"]) > 0  # 应该有备用匹配结果
            assert any("备用匹配结果" in log for log in result["processing_log"])
            assert len(result["errors"]) > 0
    
    def test_vector_similarity_matching_success(self):
        """测试向量相似度匹配 - 成功情况"""
        state = {
            "prefiltered_items": [
                {
                    "id": "C001", 
                    "name": "张三",
                    "point_id": "uuid-001",
                    "similarity_score": 0.85
                },
                {
                    "id": "C002", 
                    "name": "李四",
                    "point_id": "uuid-002", 
                    "similarity_score": 0.75
                }
            ],
            "match_results": [],
            "processing_log": [],
            "errors": []
        }
        
        result = self.vector_engine.vector_similarity_matching(state)
        
        # 验证向量匹配结果
        assert len(result["match_results"]) == 2
        assert result["match_results"][0].score == 85  # 第一个应该是最高分
        assert "向量相似度匹配" in result["match_results"][0].reason
        assert any("向量相似度匹配完成" in log for log in result["processing_log"])
    
    def test_vector_prefilter_candidates_with_query(self):
        """测试向量搜索预筛选候选人"""
        state = {
            "query": "Python开发工程师",
            "prefiltered_items": [],
            "processing_log": [],
            "errors": []
        }
        
        with patch.object(self.vector_engine.qdrant_service, 'search_candidates') as mock_search:
            mock_search.return_value = [
                {"id": "C001", "name": "张三", "similarity_score": 0.9}
            ]
            
            result = self.vector_engine.prefilter_candidates(state)
            
            # 验证向量搜索结果
            assert len(result["prefiltered_items"]) == 1
            assert any("向量搜索候选人完成" in log for log in result["processing_log"])


class TestDataPersistence:
    """测试数据持久化节点"""
    
    def setup_method(self):
        """测试设置"""
        self.persistence = DataPersistence(use_qdrant=False)  # 测试时使用Google Sheets
        self.qdrant_persistence = DataPersistence(use_qdrant=True)  # Qdrant持久化
    
    def test_save_candidate_success(self):
        """测试保存候选人 - 成功情况"""
        candidate = CandidateInfo(
            id="CAND_001",
            name="张三",
            title="Java开发工程师",
            experience_years="5年",
            skills="Java, Spring Boot",
            certificates="",
            education="本科",
            location_preference="北京",
            expected_salary="15k-20k",
            contact="zhangsan@example.com"
        )
        
        state = {
            "candidate_info": candidate,
            "processing_log": [],
            "errors": [],
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "project_info": None,
            "match_type": None,
            "match_query_id": None,
            "prefiltered_items": [],
            "match_results": [],
            "next_step": None,
            "retry_count": 0,
            "batch_complete": False
        }
        
        with patch.object(self.persistence.sheets_service, 'append_candidate_data') as mock_save:
            mock_save.return_value = True
            
            result = self.persistence.save_candidate(state)
            
            # 验证保存结果
            assert any("已保存到Google Sheets" in log for log in result["processing_log"])
            assert len(result["errors"]) == 0
    
    def test_save_match_results_success(self):
        """测试保存匹配结果 - 成功情况"""
        matches = [
            MatchResult(id="C001", name="张三", score=85, reason="技能匹配"),
            MatchResult(id="C002", name="李四", score=75, reason="经验相关")
        ]
        
        state = {
            "match_results": matches,
            "match_query_id": "PROJ_001",
            "match_type": "project_to_resume",
            "processing_log": [],
            "errors": [],
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "project_info": None,
            "prefiltered_items": [],
            "next_step": None,
            "retry_count": 0,
            "batch_complete": False
        }
        
        with patch.object(self.persistence.sheets_service, 'append_match_data') as mock_save:
            mock_save.return_value = True
            
            result = self.persistence.save_match_results(state)
            
            # 验证保存结果
            assert any("匹配结果已保存到Google Sheets: 2/2 条" in log for log in result["processing_log"])
            assert len(result["errors"]) == 0
    
    def test_save_candidate_qdrant_success(self):
        """测试保存候选人到Qdrant - 成功情况"""
        candidate = CandidateInfo(
            id="CAND_001",
            name="张三",
            title="Java开发工程师",
            experience_years="5年",
            skills="Java, Spring Boot",
            certificates="",
            education="本科",
            location_preference="北京",
            expected_salary="15k-20k",
            contact="zhangsan@example.com"
        )
        
        state = {
            "candidate_info": candidate,
            "processing_log": [],
            "errors": [],
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "project_info": None,
            "match_type": None,
            "match_query_id": None,
            "prefiltered_items": [],
            "match_results": [],
            "next_step": None,
            "retry_count": 0,
            "batch_complete": False
        }
        
        with patch.object(self.qdrant_persistence.qdrant_service, 'save_candidate') as mock_save:
            mock_save.return_value = True
            
            result = self.qdrant_persistence.save_candidate(state)
            
            # 验证Qdrant保存结果
            assert any("已保存到Qdrant" in log for log in result["processing_log"])
            assert len(result["errors"]) == 0
    
    def test_save_project_qdrant_success(self):
        """测试保存项目到Qdrant - 成功情况"""
        from src.models import ProjectInfo
        project = ProjectInfo(
            id="PROJ_001",
            title="电商平台开发",
            type="Web开发",
            tech_requirements="Java, Spring Boot, MySQL",
            description="开发一个电商平台",
            budget="50万",
            duration="6个月",
            start_time="2024年1月",
            work_style="远程"
        )
        
        state = {
            "project_info": project,
            "processing_log": [],
            "errors": [],
            "emails": [],
            "current_email": None,
            "email_type": None,
            "classification_confidence": 0.0,
            "candidate_info": None,
            "match_type": None,
            "match_query_id": None,
            "prefiltered_items": [],
            "match_results": [],
            "next_step": None,
            "retry_count": 0,
            "batch_complete": False
        }
        
        with patch.object(self.qdrant_persistence.qdrant_service, 'save_project') as mock_save:
            mock_save.return_value = True
            
            result = self.qdrant_persistence.save_project(state)
            
            # 验证Qdrant保存结果
            assert any("已保存到Qdrant" in log for log in result["processing_log"])
            assert len(result["errors"]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])