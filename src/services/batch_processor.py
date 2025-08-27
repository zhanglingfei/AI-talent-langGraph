"""
批量处理服务 - 支持高性能批量操作
符合index.html设计：批量嵌入处理(最多2048个/请求)
"""

import asyncio
from typing import List, Dict, Any, Callable, Optional, AsyncIterator
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from src.utils.logger import setup_logger
from src.config import Config

logger = setup_logger(__name__)

class BatchProcessor:
    """批量处理器 - 优化大规模数据处理性能"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    def process_batch_sync(
        self,
        items: List[Any],
        processor_func: Callable[[Any], Any],
        batch_size: int = 50,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """同步批量处理"""
        results = []
        total_items = len(items)
        
        logger.info(f"开始批量处理 {total_items} 个项目，批次大小: {batch_size}")
        
        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]
            batch_results = []
            
            # 提交批次任务到线程池
            future_to_item = {
                self.executor.submit(processor_func, item): item 
                for item in batch
            }
            
            # 收集批次结果
            for future in as_completed(future_to_item):
                try:
                    result = future.result()
                    batch_results.append(result)
                except Exception as e:
                    item = future_to_item[future]
                    logger.error(f"处理项目失败: {item}, 错误: {str(e)}")
                    batch_results.append(None)
            
            results.extend(batch_results)
            
            # 进度回调
            if progress_callback:
                progress_callback(len(results), total_items)
                
            logger.info(f"完成批次 {i//batch_size + 1}/{(total_items-1)//batch_size + 1}")
        
        logger.info(f"批量处理完成，成功处理 {len([r for r in results if r is not None])}/{total_items} 个项目")
        return results
    
    async def process_batch_async(
        self,
        items: List[Any],
        async_processor: Callable[[Any], Any],
        batch_size: int = 50,
        max_concurrent: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """异步批量处理"""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        total_items = len(items)
        
        async def process_with_semaphore(item):
            async with semaphore:
                try:
                    return await async_processor(item)
                except Exception as e:
                    logger.error(f"异步处理失败: {item}, 错误: {str(e)}")
                    return None
        
        logger.info(f"开始异步批量处理 {total_items} 个项目")
        
        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]
            
            # 创建异步任务
            tasks = [process_with_semaphore(item) for item in batch]
            
            # 等待批次完成
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"异步任务异常: {str(result)}")
                    processed_results.append(None)
                else:
                    processed_results.append(result)
            
            results.extend(processed_results)
            
            # 进度回调
            if progress_callback:
                progress_callback(len(results), total_items)
                
            logger.info(f"完成异步批次 {i//batch_size + 1}/{(total_items-1)//batch_size + 1}")
        
        logger.info(f"异步批量处理完成，成功处理 {len([r for r in results if r is not None])}/{total_items} 个项目")
        return results


class EmailBatchProcessor(BatchProcessor):
    """邮件批量处理器"""
    
    def __init__(self):
        super().__init__(max_workers=Config.MAX_RETRIES)
        
    def process_emails_batch(
        self, 
        emails: List[Dict[str, Any]], 
        email_processor,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """批量处理邮件"""
        
        def process_single_email(email_data):
            """处理单个邮件"""
            try:
                # 模拟邮件处理状态
                from src.models import EmailInfo
                from datetime import datetime
                
                email = EmailInfo(**email_data) if isinstance(email_data, dict) else email_data
                
                # 构建处理状态
                state = {
                    "current_email": email,
                    "errors": [],
                    "processing_log": [],
                    "retry_count": 0,
                    "classification_confidence": 0.0,
                    "candidate_info": None,
                    "project_info": None
                }
                
                # 分类邮件
                state = email_processor.classify_email(state)
                
                # 根据分类提取信息
                if state.get("email_type"):
                    if state["email_type"].value == "candidate":
                        state = email_processor.extract_candidate_info(state)
                    elif state["email_type"].value == "project":
                        state = email_processor.extract_project_info(state)
                
                return {
                    "email_id": email.id,
                    "success": len(state["errors"]) == 0,
                    "email_type": state.get("email_type"),
                    "candidate_info": state.get("candidate_info"),
                    "project_info": state.get("project_info"),
                    "errors": state["errors"],
                    "log": state["processing_log"]
                }
                
            except Exception as e:
                logger.error(f"邮件处理失败: {email_data}, 错误: {str(e)}")
                return {
                    "email_id": getattr(email_data, 'id', 'unknown'),
                    "success": False,
                    "errors": [str(e)],
                    "log": []
                }
        
        # 自定义进度回调
        def email_progress_callback(completed: int, total: int):
            if progress_callback:
                progress_callback(completed, total, f"处理邮件: {completed}/{total}")
        
        logger.info(f"开始批量处理 {len(emails)} 封邮件")
        results = self.process_batch_sync(
            emails, 
            process_single_email,
            batch_size=Config.EMAIL_BATCH_SIZE,
            progress_callback=email_progress_callback
        )
        
        # 统计结果
        successful = len([r for r in results if r and r.get("success")])
        failed = len(results) - successful
        
        # 分类统计
        candidates = len([r for r in results if r and r.get("email_type") and r["email_type"].value == "candidate"])
        projects = len([r for r in results if r and r.get("email_type") and r["email_type"].value == "project"])
        
        return {
            "total_processed": len(results),
            "successful": successful,
            "failed": failed,
            "candidates_found": candidates,
            "projects_found": projects,
            "results": results,
            "processing_time": time.time()
        }


class EmbeddingBatchProcessor(BatchProcessor):
    """嵌入批量处理器 - 支持OpenAI批量嵌入"""
    
    def __init__(self):
        super().__init__(max_workers=2)  # 限制并发以符合API限制
        
    def process_embeddings_batch(
        self,
        texts: List[str], 
        embedding_service,
        batch_size: int = 2048,  # OpenAI支持的最大批次大小
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[List[float]]:
        """批量生成嵌入向量"""
        
        def process_batch_embeddings(text_batch):
            """处理一批文本的嵌入"""
            try:
                return embedding_service.create_batch_embeddings(text_batch)
            except Exception as e:
                logger.error(f"批量嵌入失败: {str(e)}")
                # 降级到单个处理
                return [embedding_service.create_embedding(text) for text in text_batch]
        
        def embedding_progress_callback(completed: int, total: int):
            if progress_callback:
                progress_callback(completed, total, f"生成嵌入向量: {completed}/{total}")
        
        logger.info(f"开始批量生成 {len(texts)} 个嵌入向量")
        
        all_embeddings = []
        total_texts = len(texts)
        
        for i in range(0, total_texts, batch_size):
            batch_texts = texts[i:i + batch_size]
            
            try:
                batch_embeddings = embedding_service.create_batch_embeddings(batch_texts)
                all_embeddings.extend(batch_embeddings)
                
                if embedding_progress_callback:
                    embedding_progress_callback(len(all_embeddings), total_texts)
                    
                logger.info(f"完成嵌入批次 {i//batch_size + 1}/{(total_texts-1)//batch_size + 1}")
                
            except Exception as e:
                logger.error(f"批量嵌入失败，降级到单个处理: {str(e)}")
                # 降级到单个处理
                for text in batch_texts:
                    embedding = embedding_service.create_embedding(text)
                    all_embeddings.append(embedding)
                    
                    if embedding_progress_callback:
                        embedding_progress_callback(len(all_embeddings), total_texts)
        
        logger.info(f"批量嵌入完成，生成 {len(all_embeddings)} 个向量")
        return all_embeddings


class MatchingBatchProcessor(BatchProcessor):
    """匹配批量处理器"""
    
    def process_matches_batch(
        self,
        match_requests: List[Dict[str, Any]],
        matching_engine,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """批量处理匹配请求"""
        
        def process_single_match(match_request):
            """处理单个匹配请求"""
            try:
                # 构建匹配状态
                state = {
                    "match_type": match_request.get("match_type"),
                    "match_query_id": match_request.get("query_id"),
                    "query": match_request.get("query", ""),
                    "project_requirements": match_request.get("requirements", {}),
                    "prefiltered_items": [],
                    "match_results": [],
                    "processing_log": [],
                    "errors": []
                }
                
                # 执行多阶段匹配
                if hasattr(matching_engine, 'hard_filter_candidates'):
                    state = matching_engine.hard_filter_candidates(state)
                    state = matching_engine.vector_prefilter_candidates(state)
                    state = matching_engine.hybrid_matching(state)
                else:
                    # 降级到传统匹配
                    state = matching_engine.prefilter_candidates(state)
                    state = matching_engine.ai_matching(state)
                
                return {
                    "query_id": match_request.get("query_id"),
                    "success": len(state["errors"]) == 0,
                    "matches": state.get("match_results", []),
                    "errors": state["errors"],
                    "log": state["processing_log"]
                }
                
            except Exception as e:
                logger.error(f"匹配处理失败: {match_request}, 错误: {str(e)}")
                return {
                    "query_id": match_request.get("query_id"),
                    "success": False,
                    "matches": [],
                    "errors": [str(e)],
                    "log": []
                }
        
        def match_progress_callback(completed: int, total: int):
            if progress_callback:
                progress_callback(completed, total, f"执行匹配: {completed}/{total}")
        
        logger.info(f"开始批量处理 {len(match_requests)} 个匹配请求")
        results = self.process_batch_sync(
            match_requests,
            process_single_match,
            batch_size=10,  # 匹配计算较重，减小批次
            progress_callback=match_progress_callback
        )
        
        return results