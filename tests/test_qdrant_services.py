"""
Qdrant和向量服务的单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.qdrant_service import QdrantService
from src.services.embedding_service import EmbeddingService
from src.models import CandidateInfo, ProjectInfo


class TestEmbeddingService:
    """测试向量化服务"""
    
    def setup_method(self):
        """测试设置"""
        with patch('src.services.embedding_service.openai.OpenAI') as mock_openai:
            self.embedding_service = EmbeddingService()
            self.mock_client = mock_openai.return_value
    
    def test_create_embedding_success(self):
        """测试创建向量 - 成功情况"""
        # 模拟OpenAI响应
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        self.mock_client.embeddings.create.return_value = mock_response
        
        result = self.embedding_service.create_embedding("测试文本")
        
        # 验证结果
        assert result == [0.1, 0.2, 0.3]
        self.mock_client.embeddings.create.assert_called_once()
    
    def test_create_embedding_empty_text(self):
        """测试创建向量 - 空文本情况"""
        result = self.embedding_service.create_embedding("")
        
        # 应该返回零向量
        assert len(result) == 1536  # Config.EMBEDDING_DIMENSION
        assert all(x == 0.0 for x in result)
    
    def test_create_candidate_embedding(self):
        """测试候选人向量化"""
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
        
        # 模拟OpenAI响应
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        self.mock_client.embeddings.create.return_value = mock_response
        
        result = self.embedding_service.create_candidate_embedding(candidate)
        
        # 验证结果
        assert result == [0.1, 0.2, 0.3]
        # 验证调用参数包含候选人信息
        call_args = self.mock_client.embeddings.create.call_args
        assert "张三" in call_args[1]['input']
        assert "Java开发工程师" in call_args[1]['input']
    
    def test_create_project_embedding(self):
        """测试项目向量化"""
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
        
        # 模拟OpenAI响应
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.4, 0.5, 0.6])]
        self.mock_client.embeddings.create.return_value = mock_response
        
        result = self.embedding_service.create_project_embedding(project)
        
        # 验证结果
        assert result == [0.4, 0.5, 0.6]
        # 验证调用参数包含项目信息
        call_args = self.mock_client.embeddings.create.call_args
        assert "电商平台开发" in call_args[1]['input']
        assert "Java, Spring Boot, MySQL" in call_args[1]['input']
    
    def test_calculate_similarity(self):
        """测试相似度计算"""
        embedding1 = [1.0, 0.0, 0.0]
        embedding2 = [0.0, 1.0, 0.0]
        embedding3 = [1.0, 0.0, 0.0]
        
        # 垂直向量应该相似度为0
        similarity1 = self.embedding_service.calculate_similarity(embedding1, embedding2)
        assert abs(similarity1 - 0.0) < 0.001
        
        # 相同向量应该相似度为1
        similarity2 = self.embedding_service.calculate_similarity(embedding1, embedding3)
        assert abs(similarity2 - 1.0) < 0.001


class TestQdrantService:
    """测试Qdrant服务"""
    
    def setup_method(self):
        """测试设置"""
        with patch('src.services.qdrant_service.QdrantClient') as mock_qdrant:
            with patch('src.services.qdrant_service.EmbeddingService') as mock_embedding:
                self.qdrant_service = QdrantService()
                self.mock_client = mock_qdrant.return_value
                self.mock_embedding_service = mock_embedding.return_value
    
    def test_save_candidate_success(self):
        """测试保存候选人 - 成功情况"""
        candidate_data = {
            "id": "CAND_001",
            "name": "张三",
            "title": "Java开发工程师",
            "experience_years": "5年",
            "skills": "Java, Spring Boot",
            "certificates": "",
            "education": "本科",
            "location_preference": "北京",
            "expected_salary": "15k-20k",
            "contact": "zhangsan@example.com"
        }
        
        # 模拟向量化服务
        self.mock_embedding_service.create_candidate_embedding.return_value = [0.1, 0.2, 0.3]
        
        # 模拟Qdrant操作
        self.mock_client.upsert.return_value = Mock()
        
        result = self.qdrant_service.save_candidate(candidate_data)
        
        # 验证结果
        assert result is True
        self.mock_client.upsert.assert_called_once()
        self.mock_embedding_service.create_candidate_embedding.assert_called_once()
    
    def test_save_project_success(self):
        """测试保存项目 - 成功情况"""
        project_data = {
            "id": "PROJ_001",
            "title": "电商平台开发",
            "type": "Web开发",
            "tech_requirements": "Java, Spring Boot, MySQL",
            "description": "开发一个电商平台",
            "budget": "50万",
            "duration": "6个月",
            "start_time": "2024年1月",
            "work_style": "远程"
        }
        
        # 模拟向量化服务
        self.mock_embedding_service.create_project_embedding.return_value = [0.4, 0.5, 0.6]
        
        # 模拟Qdrant操作
        self.mock_client.upsert.return_value = Mock()
        
        result = self.qdrant_service.save_project(project_data)
        
        # 验证结果
        assert result is True
        self.mock_client.upsert.assert_called_once()
        self.mock_embedding_service.create_project_embedding.assert_called_once()
    
    def test_search_candidates_success(self):
        """测试搜索候选人 - 成功情况"""
        query = "Python开发工程师"
        
        # 模拟向量化服务
        self.mock_embedding_service.create_embedding.return_value = [0.7, 0.8, 0.9]
        
        # 模拟Qdrant搜索结果
        mock_point = Mock()
        mock_point.id = "uuid-001"
        mock_point.score = 0.85
        mock_point.payload = {
            "id": "CAND_001",
            "name": "张三",
            "title": "Python开发工程师"
        }
        self.mock_client.search.return_value = [mock_point]
        
        results = self.qdrant_service.search_candidates(query, limit=5)
        
        # 验证结果
        assert len(results) == 1
        assert results[0]["name"] == "张三"
        assert results[0]["similarity_score"] == 0.85
        assert results[0]["point_id"] == "uuid-001"
        
        # 验证调用
        self.mock_client.search.assert_called_once()
        self.mock_embedding_service.create_embedding.assert_called_once_with(query)
    
    def test_search_projects_success(self):
        """测试搜索项目 - 成功情况"""
        query = "Web开发项目"
        
        # 模拟向量化服务
        self.mock_embedding_service.create_embedding.return_value = [0.3, 0.4, 0.5]
        
        # 模拟Qdrant搜索结果
        mock_point = Mock()
        mock_point.id = "uuid-002"
        mock_point.score = 0.75
        mock_point.payload = {
            "id": "PROJ_001",
            "title": "电商平台开发",
            "type": "Web开发"
        }
        self.mock_client.search.return_value = [mock_point]
        
        results = self.qdrant_service.search_projects(query, limit=5)
        
        # 验证结果
        assert len(results) == 1
        assert results[0]["title"] == "电商平台开发"
        assert results[0]["similarity_score"] == 0.75
        assert results[0]["point_id"] == "uuid-002"
        
        # 验证调用
        self.mock_client.search.assert_called_once()
        self.mock_embedding_service.create_embedding.assert_called_once_with(query)
    
    def test_health_check_success(self):
        """测试健康检查 - 成功情况"""
        # 模拟Qdrant健康响应
        mock_collections = Mock()
        mock_collections.collections = []
        self.mock_client.get_collections.return_value = mock_collections
        
        result = self.qdrant_service.health_check()
        
        # 验证结果
        assert result is True
        self.mock_client.get_collections.assert_called_once()
    
    def test_health_check_failure(self):
        """测试健康检查 - 失败情况"""
        # 模拟Qdrant连接失败
        self.mock_client.get_collections.side_effect = Exception("连接失败")
        
        result = self.qdrant_service.health_check()
        
        # 验证结果
        assert result is False
    
    def test_get_collection_info(self):
        """测试获取集合信息"""
        collection_name = "test_collection"
        
        # 模拟Qdrant集合信息
        mock_info = Mock()
        mock_info.vectors_count = 100
        mock_info.indexed_vectors_count = 100
        mock_info.points_count = 100
        mock_info.config.params.vectors.distance = Mock()
        mock_info.config.params.vectors.size = 1536
        
        self.mock_client.get_collection.return_value = mock_info
        
        result = self.qdrant_service.get_collection_info(collection_name)
        
        # 验证结果
        assert result["name"] == collection_name
        assert result["vectors_count"] == 100
        assert result["points_count"] == 100
        assert result["config"]["size"] == 1536


if __name__ == "__main__":
    pytest.main([__file__, "-v"])