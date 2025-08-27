"""
集成处理服务 - 整合批量处理、流式反馈和进度跟踪
演示新功能的完整集成使用
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Callable
from src.services.batch_processor import EmailBatchProcessor, EmbeddingBatchProcessor, MatchingBatchProcessor
from src.services.streaming_service import StreamingService, ProcessingStreamer, stream_manager
from src.services.progress_service import ProgressManager, ProgressStage, progress_manager
from src.services.qdrant_service import QdrantService
from src.services.embedding_service import EmbeddingService
from src.utils.logger import setup_logger
from src.models import EmailInfo, CandidateInfo, ProjectInfo
from src.nodes.email_processing_nodes import EmailProcessor
from src.nodes.matching_nodes import MatchingEngine

logger = setup_logger(__name__)

class IntegratedProcessingService:
    """集成处理服务 - 提供完整的批量处理工作流"""
    
    def __init__(self):
        self.email_processor = EmailProcessor()
        self.matching_engine = MatchingEngine()
        self.qdrant_service = QdrantService()
        self.embedding_service = EmbeddingService()
        
        # 批量处理器
        self.email_batch_processor = EmailBatchProcessor()
        self.embedding_batch_processor = EmbeddingBatchProcessor()
        self.matching_batch_processor = MatchingBatchProcessor()
    
    async def process_emails_with_streaming(
        self,
        emails: List[EmailInfo],
        session_id: Optional[str] = None,
        enable_streaming: bool = True,
        enable_progress_tracking: bool = True
    ) -> Dict[str, Any]:
        """
        带有流式反馈的邮件批量处理
        集成批量处理、进度跟踪和流式反馈功能
        """
        # 创建会话ID
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 设置流式服务
        stream_service = None
        progress_tracker = None
        
        if enable_streaming:
            stream_service = stream_manager.create_stream(session_id)
            logger.info(f"启用流式反馈服务: {session_id}")
        
        if enable_progress_tracking:
            progress_tracker = progress_manager.create_tracker(session_id, total_stages=6)
            
            # 如果启用了流式服务，将进度事件转发到流
            if stream_service:
                def progress_to_stream(progress_info):
                    stream_service.emit_progress(
                        progress_info.current,
                        progress_info.total,
                        progress_info.message,
                        progress_info.stage.value
                    )
                
                progress_tracker.add_callback(progress_to_stream)
        
        try:
            # 阶段1: 初始化
            if progress_tracker:
                progress_tracker.start_stage(ProgressStage.INITIALIZATION, 1, "系统初始化")
                progress_tracker.complete_stage(ProgressStage.INITIALIZATION)
            
            if stream_service:
                stream_service.emit_status("开始邮件处理", {
                    "total_emails": len(emails),
                    "session_id": session_id
                })
            
            # 阶段2: 邮件分类和信息提取
            if progress_tracker:
                progress_tracker.start_stage(ProgressStage.EMAIL_CLASSIFICATION, len(emails), "邮件分类处理")
            
            # 创建批量处理回调
            email_progress_callback = None
            if progress_tracker:
                def email_callback(current, total, message):
                    progress_tracker.update_progress(ProgressStage.EMAIL_CLASSIFICATION, current, message)
                email_progress_callback = email_callback
            
            # 执行邮件批量处理
            email_results = self.email_batch_processor.process_emails_batch(
                [email.model_dump() if hasattr(email, 'model_dump') else email for email in emails],
                self.email_processor,
                progress_callback=email_progress_callback
            )
            
            if progress_tracker:
                progress_tracker.complete_stage(ProgressStage.EMAIL_CLASSIFICATION, "邮件分类完成")
            
            # 提取成功处理的候选人和项目
            candidates = []
            projects = []
            
            for result in email_results["results"]:
                if result and result.get("success"):
                    if result.get("candidate_info"):
                        candidates.append(result["candidate_info"])
                    if result.get("project_info"):
                        projects.append(result["project_info"])
            
            if stream_service:
                stream_service.emit_result({
                    "email_processing_complete": True,
                    "candidates_found": len(candidates),
                    "projects_found": len(projects),
                    "total_processed": email_results["total_processed"],
                    "success_rate": email_results["successful"] / email_results["total_processed"] if email_results["total_processed"] > 0 else 0
                }, "email_batch_result")
            
            # 阶段3: 向量生成
            total_items = len(candidates) + len(projects)
            if total_items > 0 and progress_tracker:
                progress_tracker.start_stage(ProgressStage.VECTOR_GENERATION, total_items, "生成向量表示")
            
            # 批量生成候选人向量
            candidate_embeddings = []
            if candidates:
                if progress_tracker:
                    def embedding_callback(current, total, message):
                        progress_tracker.update_progress(ProgressStage.VECTOR_GENERATION, current, f"候选人向量化: {message}")
                    
                candidate_objects = [CandidateInfo(**c) if isinstance(c, dict) else c for c in candidates]
                candidate_embeddings = self.embedding_service.create_candidate_embeddings_batch(candidate_objects)
            
            # 批量生成项目向量
            project_embeddings = []
            if projects:
                if progress_tracker:
                    def project_embedding_callback(current, total, message):
                        base_current = len(candidate_embeddings) + current
                        progress_tracker.update_progress(ProgressStage.VECTOR_GENERATION, base_current, f"项目向量化: {message}")
                
                project_objects = [ProjectInfo(**p) if isinstance(p, dict) else p for p in projects]
                project_embeddings = self.embedding_service.create_project_embeddings_batch(project_objects)
            
            if progress_tracker:
                progress_tracker.complete_stage(ProgressStage.VECTOR_GENERATION, "向量生成完成")
            
            # 阶段4: 数据库存储
            storage_total = len(candidates) + len(projects)
            if storage_total > 0 and progress_tracker:
                progress_tracker.start_stage(ProgressStage.DATABASE_STORAGE, storage_total, "存储到向量数据库")
            
            # 存储候选人
            saved_candidates = 0
            for i, (candidate, embedding) in enumerate(zip(candidates, candidate_embeddings)):
                try:
                    candidate_data = candidate if isinstance(candidate, dict) else candidate.model_dump()
                    if self.qdrant_service.save_candidate(candidate_data):
                        saved_candidates += 1
                    
                    if progress_tracker:
                        progress_tracker.update_progress(ProgressStage.DATABASE_STORAGE, i + 1, f"存储候选人 {i+1}/{len(candidates)}")
                except Exception as e:
                    logger.error(f"存储候选人失败: {str(e)}")
            
            # 存储项目
            saved_projects = 0
            for i, (project, embedding) in enumerate(zip(projects, project_embeddings)):
                try:
                    project_data = project if isinstance(project, dict) else project.model_dump()
                    if self.qdrant_service.save_project(project_data):
                        saved_projects += 1
                    
                    if progress_tracker:
                        progress_tracker.update_progress(ProgressStage.DATABASE_STORAGE, len(candidates) + i + 1, f"存储项目 {i+1}/{len(projects)}")
                except Exception as e:
                    logger.error(f"存储项目失败: {str(e)}")
            
            if progress_tracker:
                progress_tracker.complete_stage(ProgressStage.DATABASE_STORAGE, "数据库存储完成")
            
            # 阶段5: 匹配分析（如果有候选人和项目）
            matches = []
            if candidates and projects:
                if progress_tracker:
                    progress_tracker.start_stage(ProgressStage.MATCHING_ANALYSIS, len(candidates) * len(projects), "执行匹配分析")
                
                # 准备匹配请求
                match_requests = []
                for i, candidate in enumerate(candidates):
                    for j, project in enumerate(projects):
                        match_request = {
                            "match_type": "candidate_project",
                            "query_id": f"match_{i}_{j}",
                            "query": f"匹配候选人 {candidate.get('name', 'unknown')} 与项目 {project.get('title', 'unknown')}",
                            "requirements": project.get('tech_requirements', {}),
                            "candidate": candidate,
                            "project": project
                        }
                        match_requests.append(match_request)
                
                # 批量匹配处理
                if match_requests:
                    def matching_callback(current, total, message):
                        if progress_tracker:
                            progress_tracker.update_progress(ProgressStage.MATCHING_ANALYSIS, current, message)
                    
                    matches = self.matching_batch_processor.process_matches_batch(
                        match_requests,
                        self.matching_engine,
                        progress_callback=matching_callback
                    )
                
                if progress_tracker:
                    progress_tracker.complete_stage(ProgressStage.MATCHING_ANALYSIS, "匹配分析完成")
            
            # 阶段6: 结果汇总
            if progress_tracker:
                progress_tracker.start_stage(ProgressStage.RESULT_GENERATION, 1, "生成最终结果")
            
            # 构建最终结果
            final_result = {
                "session_id": session_id,
                "processing_summary": {
                    "emails_processed": len(emails),
                    "candidates_extracted": len(candidates),
                    "projects_extracted": len(projects),
                    "candidates_saved": saved_candidates,
                    "projects_saved": saved_projects,
                    "matches_generated": len(matches),
                    "success_rate": {
                        "email_processing": email_results["successful"] / email_results["total_processed"] if email_results["total_processed"] > 0 else 0,
                        "candidate_storage": saved_candidates / len(candidates) if candidates else 1.0,
                        "project_storage": saved_projects / len(projects) if projects else 1.0
                    }
                },
                "detailed_results": {
                    "email_results": email_results,
                    "candidates": candidates[:10],  # 限制返回数量
                    "projects": projects[:10],
                    "top_matches": sorted(matches, key=lambda x: len(x.get("matches", [])), reverse=True)[:10] if matches else []
                },
                "performance_metrics": {
                    "total_processing_time": 0,
                    "stages_completed": 6,
                    "items_per_second": 0
                }
            }
            
            if progress_tracker:
                progress_tracker.complete_stage(ProgressStage.RESULT_GENERATION, "结果生成完成")
                progress_tracker.complete_session("批量处理完成")
                
                # 添加性能指标
                overall_progress = progress_tracker.get_overall_progress()
                final_result["performance_metrics"]["total_processing_time"] = overall_progress["total_elapsed_time"]
                final_result["performance_metrics"]["items_per_second"] = len(emails) / overall_progress["total_elapsed_time"] if overall_progress["total_elapsed_time"] > 0 else 0
            
            if stream_service:
                stream_service.complete(final_result)
            
            logger.info(f"批量处理完成 - 会话: {session_id}, 处理邮件: {len(emails)}, 候选人: {saved_candidates}, 项目: {saved_projects}")
            return final_result
            
        except Exception as e:
            error_msg = f"批量处理失败: {str(e)}"
            logger.error(error_msg)
            
            if stream_service:
                stream_service.emit_error(error_msg)
                stream_service.complete({"error": error_msg, "session_id": session_id})
            
            if progress_tracker:
                progress_tracker.set_error(ProgressStage.COMPLETION, error_msg)
            
            raise
    
    async def create_streaming_callback(self, session_id: str) -> Callable[[Dict[str, Any]], None]:
        """创建流式回调函数"""
        def callback(event):
            stream_service = stream_manager.get_stream(session_id)
            if stream_service:
                if "progress" in event:
                    stream_service.emit_progress(**event["progress"])
                elif "status" in event:
                    stream_service.emit_status(**event["status"])
                elif "result" in event:
                    stream_service.emit_result(event["result"])
                elif "error" in event:
                    stream_service.emit_error(event["error"])
        
        return callback
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        progress_tracker = progress_manager.get_tracker(session_id)
        if progress_tracker:
            return progress_tracker.get_overall_progress()
        return None
    
    def cleanup_session(self, session_id: str):
        """清理会话资源"""
        stream_manager.remove_stream(session_id)
        progress_manager.remove_tracker(session_id)
        logger.info(f"清理会话: {session_id}")

# 全局实例
integrated_service = IntegratedProcessingService()