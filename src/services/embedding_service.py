"""
向量化服务实现
"""

from typing import List, Union
import openai
from src.config import Config
from src.utils.logger import setup_logger
from src.models import CandidateInfo, ProjectInfo

logger = setup_logger(__name__)

class EmbeddingService:
    """向量化服务类"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.EMBEDDING_MODEL
        self.dimension = Config.EMBEDDING_DIMENSION
    
    def create_embedding(self, text: str) -> List[float]:
        """创建文本的向量表示"""
        try:
            if not text or not text.strip():
                logger.warning("空文本无法向量化")
                return [0.0] * self.dimension
            
            # 清理和截断文本
            cleaned_text = self._clean_text(text)
            
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned_text
            )
            
            embedding = response.data[0].embedding
            logger.debug(f"成功创建向量，维度: {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"向量化失败: {str(e)}")
            # 返回零向量作为后备
            return [0.0] * self.dimension
    
    def create_candidate_embedding(self, candidate: CandidateInfo) -> List[float]:
        """为候选人信息创建向量"""
        # 构建候选人的文本表示
        text_parts = [
            f"姓名: {candidate.name}",
            f"职位: {candidate.title}",
            f"工作经验: {candidate.experience_years}",
            f"技能: {candidate.skills}",
            f"教育背景: {candidate.education}",
            f"证书: {candidate.certificates}",
            f"地点偏好: {candidate.location_preference}"
        ]
        
        # 过滤空值
        meaningful_parts = [part for part in text_parts if not part.endswith(": ")]
        candidate_text = " | ".join(meaningful_parts)
        
        logger.debug(f"候选人向量化文本: {candidate_text[:200]}...")
        return self.create_embedding(candidate_text)
    
    def create_project_embedding(self, project: ProjectInfo) -> List[float]:
        """为项目信息创建向量"""
        # 构建项目的文本表示
        text_parts = [
            f"项目名称: {project.title}",
            f"项目类型: {project.type}",
            f"技术要求: {project.tech_requirements}",
            f"项目描述: {project.description}",
            f"工作方式: {project.work_style}",
            f"项目时长: {project.duration}"
        ]
        
        # 过滤空值
        meaningful_parts = [part for part in text_parts if not part.endswith(": ")]
        project_text = " | ".join(meaningful_parts)
        
        logger.debug(f"项目向量化文本: {project_text[:200]}...")
        return self.create_embedding(project_text)
    
    def create_batch_embeddings(self, texts: List[str], batch_size: int = 2048) -> List[List[float]]:
        """批量创建向量 - 支持大规模处理，符合OpenAI API限制"""
        try:
            # 清理文本
            cleaned_texts = [self._clean_text(text) for text in texts if text and text.strip()]
            
            if not cleaned_texts:
                logger.warning("没有有效文本进行批量向量化")
                return []
            
            all_embeddings = []
            total_texts = len(cleaned_texts)
            
            # 分批处理以符合API限制
            for i in range(0, total_texts, batch_size):
                batch_texts = cleaned_texts[i:i + batch_size]
                
                logger.info(f"处理向量化批次 {i//batch_size + 1}/{(total_texts-1)//batch_size + 1}")
                
                try:
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=batch_texts
                    )
                    
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    
                    logger.debug(f"批次完成，获得 {len(batch_embeddings)} 个向量")
                    
                except Exception as batch_error:
                    logger.error(f"批次 {i//batch_size + 1} 处理失败: {str(batch_error)}")
                    # 降级到单个处理
                    logger.info("降级到单个向量化处理")
                    for text in batch_texts:
                        try:
                            single_embedding = self.create_embedding(text)
                            all_embeddings.append(single_embedding)
                        except Exception as single_error:
                            logger.error(f"单个文本向量化失败: {str(single_error)}")
                            all_embeddings.append([0.0] * self.dimension)
            
            logger.info(f"成功批量创建 {len(all_embeddings)} 个向量")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"批量向量化失败: {str(e)}")
            # 返回零向量列表作为后备
            return [[0.0] * self.dimension] * len(texts)
    
    def _clean_text(self, text: str) -> str:
        """清理和预处理文本"""
        if not text:
            return ""
        
        # 移除多余空格和换行
        cleaned = " ".join(text.split())
        
        # 截断过长的文本 (OpenAI限制约8192 tokens)
        max_chars = 6000  # 保守估计
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "..."
            logger.warning(f"文本过长已截断至 {max_chars} 字符")
        
        return cleaned
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        try:
            import numpy as np
            
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)
            
            if norms == 0:
                return 0.0
            
            similarity = dot_product / norms
            return float(similarity)
            
        except Exception as e:
            logger.error(f"相似度计算失败: {str(e)}")
            return 0.0
    
    def create_candidate_embeddings_batch(self, candidates: List[CandidateInfo]) -> List[List[float]]:
        """批量为候选人创建向量"""
        candidate_texts = []
        for candidate in candidates:
            text_parts = [
                f"姓名: {candidate.name}",
                f"职位: {candidate.title}",
                f"工作经验: {candidate.experience_years}",
                f"技能: {candidate.skills}",
                f"教育背景: {candidate.education}",
                f"证书: {candidate.certificates}",
                f"地点偏好: {candidate.location_preference}"
            ]
            
            # 过滤空值
            meaningful_parts = [part for part in text_parts if not part.endswith(": ")]
            candidate_text = " | ".join(meaningful_parts)
            candidate_texts.append(candidate_text)
        
        logger.info(f"开始批量处理 {len(candidates)} 个候选人向量化")
        return self.create_batch_embeddings(candidate_texts)
    
    def create_project_embeddings_batch(self, projects: List[ProjectInfo]) -> List[List[float]]:
        """批量为项目创建向量"""
        project_texts = []
        for project in projects:
            text_parts = [
                f"项目名称: {project.title}",
                f"项目类型: {project.type}",
                f"技术要求: {project.tech_requirements}",
                f"项目描述: {project.description}",
                f"工作方式: {project.work_style}",
                f"项目时长: {project.duration}"
            ]
            
            # 过滤空值
            meaningful_parts = [part for part in text_parts if not part.endswith(": ")]
            project_text = " | ".join(meaningful_parts)
            project_texts.append(project_text)
        
        logger.info(f"开始批量处理 {len(projects)} 个项目向量化")
        return self.create_batch_embeddings(project_texts)
    
    async def create_batch_embeddings_async(
        self, 
        texts: List[str], 
        batch_size: int = 2048,
        progress_callback: callable = None
    ) -> List[List[float]]:
        """异步批量创建向量"""
        import asyncio
        
        # 分批处理
        all_embeddings = []
        total_texts = len(texts)
        
        for i in range(0, total_texts, batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # 在事件循环中运行同步代码
            loop = asyncio.get_event_loop()
            batch_embeddings = await loop.run_in_executor(
                None, 
                self.create_batch_embeddings, 
                batch_texts,
                batch_size
            )
            
            all_embeddings.extend(batch_embeddings)
            
            # 进度回调
            if progress_callback:
                progress_callback(len(all_embeddings), total_texts, f"向量化进度")
        
        return all_embeddings