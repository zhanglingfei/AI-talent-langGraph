"""
集成测试 - 测试完整的工作流程
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from src.main import TalentMatchingSystem
from src.models import EmailInfo, EmailType


class TestTalentMatchingIntegration:
    """测试人才匹配系统集成功能"""
    
    def setup_method(self):
        """测试设置"""
        self.system = TalentMatchingSystem()
    
    def test_process_emails_integration(self):
        """测试邮件处理完整流程"""
        # 模拟测试用例不需要实际的API调用
        with patch('src.nodes.email_nodes.ChatOpenAI') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            # 模拟邮件分类结果
            mock_llm.invoke.side_effect = [
                {"type": "CANDIDATE", "confidence": 0.9, "reason": "包含简历信息"},
                # 这里可能需要更多的mock返回值，取决于具体的流程
            ]
            
            result = self.system.process_emails("all")
            
            # 验证结果结构
            assert "processed" in result
            assert "errors" in result
            assert "log" in result
            assert result["processed"] == 1
    
    def test_match_project_with_candidates_integration(self):
        """测试项目匹配候选人完整流程"""
        project_id = "PROJ_001"
        
        with patch('src.nodes.matching_nodes.ChatOpenAI') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            # 模拟AI匹配结果
            mock_llm.invoke.return_value = {
                "matches": [
                    {
                        "id": "C001",
                        "name": "张三",
                        "score": 85,
                        "reason": "Java技能匹配度高，有5年相关经验"
                    },
                    {
                        "id": "C002", 
                        "name": "李四",
                        "score": 75,
                        "reason": "Python技能匹配，有相关项目经验"
                    }
                ]
            }
            
            result = self.system.match_project_with_candidates(project_id)
            
            # 验证结果结构
            assert "matches" in result
            assert "errors" in result
            assert "log" in result
            assert len(result["log"]) > 0
    
    def test_match_candidate_with_projects_integration(self):
        """测试候选人匹配项目完整流程"""
        candidate_id = "CAND_001"
        
        with patch('src.nodes.matching_nodes.ChatOpenAI') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            # 模拟AI匹配结果
            mock_llm.invoke.return_value = {
                "matches": [
                    {
                        "id": "P001",
                        "name": "电商平台开发",
                        "score": 90,
                        "reason": "技术栈完全匹配，项目规模适中"
                    }
                ]
            }
            
            result = self.system.match_candidate_with_projects(candidate_id)
            
            # 验证结果结构
            assert "matches" in result
            assert "errors" in result
            assert "log" in result
            assert len(result["log"]) > 0
    
    def test_error_handling_integration(self):
        """测试错误处理集成"""
        project_id = "INVALID_PROJECT"
        
        with patch('src.nodes.matching_nodes.ChatOpenAI') as mock_llm_class:
            mock_llm = Mock()
            mock_llm_class.return_value = mock_llm
            
            # 模拟API调用失败
            mock_llm.invoke.side_effect = Exception("API调用失败")
            
            result = self.system.match_project_with_candidates(project_id)
            
            # 验证错误处理
            assert "matches" in result
            assert "errors" in result
            assert len(result["errors"]) > 0 or len(result["matches"]) > 0  # 应该有错误或备用结果
    
    def test_configuration_validation(self):
        """测试配置验证"""
        from src.config import Config
        
        # 测试必要的配置项是否存在
        # 注意：在测试环境中，API Key可能为None，这是正常的
        assert hasattr(Config, 'OPENAI_API_KEY')
        assert hasattr(Config, 'SPREADSHEET_ID')
        assert hasattr(Config, 'SHEET_NAMES')
        assert isinstance(Config.SHEET_NAMES, dict)
        
        # 验证工作表名称配置
        expected_sheets = ["GMAIL_DATA", "PROJECTS", "RESUME_DATABASE", "MATCHES"]
        for sheet in expected_sheets:
            assert sheet in Config.SHEET_NAMES
    
    def test_data_models_validation(self):
        """测试数据模型验证"""
        from src.models import CandidateInfo, ProjectInfo, MatchResult, EmailInfo
        
        # 测试候选人模型
        candidate = CandidateInfo(
            id="C001",
            name="张三",
            title="Java开发工程师", 
            experience_years="5年",
            skills="Java, Spring Boot"
        )
        assert candidate.id == "C001"
        assert candidate.name == "张三"
        
        # 测试项目模型
        project = ProjectInfo(
            id="P001",
            title="电商平台开发",
            tech_requirements="Java, MySQL",
            description="开发电商平台"
        )
        assert project.id == "P001"
        assert project.title == "电商平台开发"
        
        # 测试匹配结果模型
        match = MatchResult(
            id="C001",
            name="张三", 
            score=85,
            reason="技能匹配"
        )
        assert match.score >= 0 and match.score <= 100
        
        # 测试邮件模型
        email = EmailInfo(
            id="E001",
            subject="测试邮件",
            body="测试内容",
            timestamp=datetime.now(),
            sender="test@example.com"
        )
        assert email.id == "E001"
        assert email.sender == "test@example.com"


class TestAPIIntegration:
    """测试API集成功能"""
    
    def test_api_endpoints_exist(self):
        """测试API端点是否存在"""
        from api.app import app
        
        # 获取所有路由
        routes = [route.path for route in app.routes]
        
        # 验证必要的端点存在
        assert "/health" in routes
        assert "/process-emails" in routes  
        assert "/match" in routes
    
    def test_api_models_validation(self):
        """测试API模型验证"""
        from api.app import ProcessEmailRequest, MatchRequest
        
        # 测试邮件处理请求模型
        email_req = ProcessEmailRequest(label="all")
        assert email_req.label == "all"
        
        # 测试匹配请求模型
        match_req = MatchRequest(
            match_type="project_to_resume",
            query_id="PROJ_001"
        )
        assert match_req.match_type == "project_to_resume"
        assert match_req.query_id == "PROJ_001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])