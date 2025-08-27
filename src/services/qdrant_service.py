"""
Qdrant向量数据库服务集成
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import uuid
from src.config import Config
from src.services.embedding_service import EmbeddingService
from src.utils.logger import setup_logger
from src.models import CandidateInfo, ProjectInfo

logger = setup_logger(__name__)

class QdrantService:
    """Qdrant向量数据库服务类"""
    
    def __init__(self):
        self.client = QdrantClient(
            host=Config.QDRANT_HOST,
            port=Config.QDRANT_PORT
        )
        self.embedding_service = EmbeddingService()
        self.collections = Config.COLLECTIONS
        self._initialize_collections()
    
    def _initialize_collections(self):
        """初始化Qdrant集合"""
        try:
            for collection_name in self.collections.values():
                if not self._collection_exists(collection_name):
                    self._create_collection(collection_name)
                    logger.info(f"创建集合: {collection_name}")
                else:
                    logger.debug(f"集合已存在: {collection_name}")
        except Exception as e:
            logger.error(f"初始化集合失败: {str(e)}")
    
    def _collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        try:
            collections = self.client.get_collections().collections
            return any(col.name == collection_name for col in collections)
        except Exception:
            return False
    
    def _create_collection(self, collection_name: str):
        """创建新集合"""
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=Config.EMBEDDING_DIMENSION,
                distance=Distance.COSINE
            )
        )
    
    def save_candidate(self, candidate_data: Dict[str, Any]) -> bool:
        """保存候选人信息到向量数据库"""
        try:
            # 创建CandidateInfo对象
            candidate = CandidateInfo(**candidate_data)
            
            # 生成向量
            embedding = self.embedding_service.create_candidate_embedding(candidate)
            
            # 准备metadata
            metadata = candidate.model_dump()
            metadata["created_at"] = datetime.now().isoformat()
            metadata["source"] = "email"
            metadata["type"] = "candidate"
            
            # 创建点
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=metadata
            )
            
            # 插入到Qdrant
            collection_name = self.collections["CANDIDATES"]
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"成功保存候选人: {candidate.name}")
            return True
            
        except Exception as e:
            logger.error(f"保存候选人失败: {str(e)}")
            return False
    
    def save_project(self, project_data: Dict[str, Any]) -> bool:
        """保存项目信息到向量数据库"""
        try:
            # 创建ProjectInfo对象
            project = ProjectInfo(**project_data)
            
            # 生成向量
            embedding = self.embedding_service.create_project_embedding(project)
            
            # 准备metadata
            metadata = project.model_dump()
            metadata["created_at"] = datetime.now().isoformat()
            metadata["source"] = "email"
            metadata["type"] = "project"
            
            # 创建点
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=metadata
            )
            
            # 插入到Qdrant
            collection_name = self.collections["PROJECTS"]
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"成功保存项目: {project.title}")
            return True
            
        except Exception as e:
            logger.error(f"保存项目失败: {str(e)}")
            return False
    
    def save_match_result(self, match_data: Dict[str, Any]) -> bool:
        """保存匹配结果"""
        try:
            # 准备metadata
            metadata = match_data.copy()
            metadata["created_at"] = datetime.now().isoformat()
            metadata["type"] = "match"
            
            # 使用匹配描述创建向量
            match_text = f"匹配: {match_data.get('candidate_id', '')} -> {match_data.get('project_id', '')} 分数: {match_data.get('score', 0)}"
            embedding = self.embedding_service.create_embedding(match_text)
            
            # 创建点
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=metadata
            )
            
            # 插入到Qdrant
            collection_name = self.collections["MATCHES"]
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"成功保存匹配结果: {match_data.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"保存匹配结果失败: {str(e)}")
            return False
    
    def search_candidates(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None, 
        limit: int = 10,
        score_threshold: float = 0.7,
        use_weighted_search: bool = True
    ) -> List[Dict[str, Any]]:
        """搜索候选人"""
        try:
            # 创建查询向量
            query_vector = self.embedding_service.create_embedding(query)
            
            # 构建过滤条件
            filter_conditions = self._build_filter(filters) if filters else None
            
            # 执行搜索
            collection_name = self.collections["CANDIDATES"]
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=filter_conditions,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # 格式化结果并应用权重
            results = []
            for point in search_result:
                result = point.payload.copy()
                raw_similarity = point.score
                
                if use_weighted_search:
                    # 应用index.html设计的权重：向量70% + 过滤30%
                    weighted_score = self._calculate_weighted_score(
                        raw_similarity, 
                        result,
                        filters or {}
                    )
                    result["similarity_score"] = raw_similarity
                    result["weighted_score"] = weighted_score
                    result["final_score"] = weighted_score
                else:
                    result["similarity_score"] = raw_similarity
                    result["final_score"] = raw_similarity
                
                result["point_id"] = point.id
                results.append(result)
            
            # 按最终分数重新排序
            if use_weighted_search:
                results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            
            logger.info(f"找到 {len(results)} 个候选人")
            return results
            
        except Exception as e:
            logger.error(f"搜索候选人失败: {str(e)}")
            return []
    
    def search_projects(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None, 
        limit: int = 10,
        score_threshold: float = 0.7,
        use_weighted_search: bool = True
    ) -> List[Dict[str, Any]]:
        """搜索项目"""
        try:
            # 创建查询向量
            query_vector = self.embedding_service.create_embedding(query)
            
            # 构建过滤条件
            filter_conditions = self._build_filter(filters) if filters else None
            
            # 执行搜索
            collection_name = self.collections["PROJECTS"]
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=filter_conditions,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # 格式化结果并应用权重
            results = []
            for point in search_result:
                result = point.payload.copy()
                raw_similarity = point.score
                
                if use_weighted_search:
                    # 应用权重：向量70% + 过滤30%
                    weighted_score = self._calculate_weighted_score(
                        raw_similarity, 
                        result,
                        filters or {}
                    )
                    result["similarity_score"] = raw_similarity
                    result["weighted_score"] = weighted_score
                    result["final_score"] = weighted_score
                else:
                    result["similarity_score"] = raw_similarity
                    result["final_score"] = raw_similarity
                
                result["point_id"] = point.id
                results.append(result)
            
            # 按最终分数重新排序
            if use_weighted_search:
                results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
            
            logger.info(f"找到 {len(results)} 个项目")
            return results
            
        except Exception as e:
            logger.error(f"搜索项目失败: {str(e)}")
            return []
    
    def find_similar_candidates(self, candidate_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """找到相似的候选人"""
        try:
            # 获取候选人的向量
            collection_name = self.collections["CANDIDATES"]
            point = self.client.retrieve(
                collection_name=collection_name,
                ids=[candidate_id],
                with_vectors=True
            )
            
            if not point or not point[0].vector:
                logger.warning(f"未找到候选人 {candidate_id} 的向量")
                return []
            
            # 使用该向量搜索相似候选人
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=point[0].vector,
                limit=limit + 1,  # +1 to exclude self
                score_threshold=0.7
            )
            
            # 排除自己
            results = []
            for p in search_result:
                if str(p.id) != candidate_id:
                    result = p.payload.copy()
                    result["similarity_score"] = p.score
                    result["point_id"] = p.id
                    results.append(result)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"查找相似候选人失败: {str(e)}")
            return []
    
    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """构建Qdrant过滤条件"""
        conditions = []
        
        for key, value in filters.items():
            if value is not None:
                condition = FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
                conditions.append(condition)
        
        return Filter(must=conditions) if conditions else None
    
    def _calculate_weighted_score(
        self, 
        vector_score: float, 
        candidate_data: Dict[str, Any], 
        filters: Dict[str, Any]
    ) -> float:
        """计算加权分数 - 符合index.html设计：向量70% + 过滤30%"""
        try:
            # 向量相似度分数 (70%)
            vector_weight = Config.MATCHING_WEIGHTS["VECTOR_SIMILARITY"]
            vector_component = vector_score * vector_weight
            
            # 过滤匹配分数 (30%)
            filter_weight = Config.MATCHING_WEIGHTS["METADATA_FILTERS"] 
            filter_component = self._calculate_filter_score(candidate_data, filters) * filter_weight
            
            # 综合分数
            final_score = vector_component + filter_component
            
            logger.debug(f"权重评分: 向量{vector_score:.3f}*{vector_weight} + 过滤{filter_component/filter_weight:.3f}*{filter_weight} = {final_score:.3f}")
            
            return min(1.0, final_score)  # 确保不超过1.0
            
        except Exception as e:
            logger.error(f"权重计算失败: {str(e)}")
            return vector_score
    
    def _calculate_filter_score(self, candidate_data: Dict[str, Any], filters: Dict[str, Any]) -> float:
        """计算过滤条件匹配分数"""
        if not filters:
            return 0.8  # 无过滤条件时给基础分
        
        total_filters = len(filters)
        matched_filters = 0
        
        for key, expected_value in filters.items():
            candidate_value = candidate_data.get(key, "")
            
            if self._filter_matches(candidate_value, expected_value):
                matched_filters += 1
        
        # 返回匹配百分比
        return matched_filters / total_filters if total_filters > 0 else 0.8
    
    def _filter_matches(self, candidate_value: str, expected_value: Any) -> bool:
        """检查过滤条件是否匹配"""
        if not candidate_value or not expected_value:
            return False
        
        candidate_str = str(candidate_value).lower()
        expected_str = str(expected_value).lower()
        
        # 简单的包含匹配
        return expected_str in candidate_str or candidate_str in expected_str
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "config": {
                    "distance": str(info.config.params.vectors.distance),
                    "size": info.config.params.vectors.size
                }
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            return {}
    
    def delete_point(self, collection_name: str, point_id: str) -> bool:
        """删除指定点"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=[point_id]
            )
            logger.info(f"删除点 {point_id} 成功")
            return True
        except Exception as e:
            logger.error(f"删除点失败: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            collections = self.client.get_collections()
            return len(collections.collections) >= 0
        except Exception as e:
            logger.error(f"Qdrant健康检查失败: {str(e)}")
            return False