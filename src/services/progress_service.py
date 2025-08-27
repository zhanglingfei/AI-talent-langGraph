"""
进度跟踪和回调机制服务
提供统一的进度管理和用户反馈接口
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class ProgressStage(str, Enum):
    """进度阶段类型"""
    INITIALIZATION = "initialization"
    EMAIL_CLASSIFICATION = "email_classification"
    INFORMATION_EXTRACTION = "information_extraction"
    VECTOR_GENERATION = "vector_generation"
    DATABASE_STORAGE = "database_storage"
    CANDIDATE_FILTERING = "candidate_filtering"
    MATCHING_ANALYSIS = "matching_analysis"
    RESULT_GENERATION = "result_generation"
    COMPLETION = "completion"

@dataclass
class ProgressInfo:
    """进度信息数据结构"""
    stage: ProgressStage
    current: int
    total: int
    message: str = ""
    start_time: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining: float = 0.0
    percentage: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.total > 0:
            self.percentage = round((self.current / self.total) * 100, 2)
        if self.start_time > 0:
            self.elapsed_time = time.time() - self.start_time
            if self.current > 0 and self.total > self.current:
                rate = self.current / self.elapsed_time
                remaining_items = self.total - self.current
                self.estimated_remaining = remaining_items / rate if rate > 0 else 0

class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, session_id: str, total_stages: int = 1):
        self.session_id = session_id
        self.total_stages = total_stages
        self.current_stage = 0
        self.stages_progress: Dict[ProgressStage, ProgressInfo] = {}
        self.callbacks: List[Callable[[ProgressInfo], None]] = []
        self.session_start_time = time.time()
        self.stage_start_times: Dict[ProgressStage, float] = {}
        self.is_completed = False
        
    def add_callback(self, callback: Callable[[ProgressInfo], None]):
        """添加进度回调函数"""
        self.callbacks.append(callback)
        logger.debug(f"进度跟踪器 {self.session_id} 添加回调，总回调数: {len(self.callbacks)}")
    
    def remove_callback(self, callback: Callable[[ProgressInfo], None]):
        """移除进度回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def start_stage(self, stage: ProgressStage, total_items: int, message: str = ""):
        """开始新阶段"""
        self.current_stage += 1
        self.stage_start_times[stage] = time.time()
        
        progress = ProgressInfo(
            stage=stage,
            current=0,
            total=total_items,
            message=message,
            start_time=self.stage_start_times[stage],
            metadata={
                "stage_number": self.current_stage,
                "total_stages": self.total_stages,
                "session_id": self.session_id
            }
        )
        
        self.stages_progress[stage] = progress
        self._notify_callbacks(progress)
        logger.info(f"开始阶段 {stage.value}: {message} (共{total_items}项)")
    
    def update_progress(
        self, 
        stage: ProgressStage, 
        current: int, 
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """更新阶段进度"""
        if stage not in self.stages_progress:
            logger.warning(f"未找到阶段 {stage.value}，自动创建")
            self.start_stage(stage, current, message)
            return
        
        progress = self.stages_progress[stage]
        progress.current = current
        if message:
            progress.message = message
        if metadata:
            progress.metadata.update(metadata)
        
        # 重新计算时间相关数据
        progress.__post_init__()
        
        self._notify_callbacks(progress)
        
        # 每10%或每100项记录一次详细日志
        if current % max(1, progress.total // 10) == 0 or current % 100 == 0:
            logger.info(f"{stage.value} 进度: {current}/{progress.total} ({progress.percentage}%) - {message}")
    
    def complete_stage(self, stage: ProgressStage, message: str = "阶段完成"):
        """完成阶段"""
        if stage in self.stages_progress:
            progress = self.stages_progress[stage]
            progress.current = progress.total
            progress.message = message
            progress.__post_init__()
            
            stage_time = progress.elapsed_time
            logger.info(f"阶段 {stage.value} 完成，耗时: {stage_time:.2f}秒")
            
            self._notify_callbacks(progress)
    
    def set_error(self, stage: ProgressStage, error_message: str):
        """设置阶段错误"""
        if stage in self.stages_progress:
            progress = self.stages_progress[stage]
            progress.message = f"错误: {error_message}"
            progress.metadata["error"] = True
            progress.metadata["error_message"] = error_message
            
            self._notify_callbacks(progress)
            logger.error(f"{stage.value} 阶段错误: {error_message}")
    
    def complete_session(self, final_message: str = "处理完成"):
        """完成整个会话"""
        self.is_completed = True
        total_time = time.time() - self.session_start_time
        
        completion_progress = ProgressInfo(
            stage=ProgressStage.COMPLETION,
            current=self.total_stages,
            total=self.total_stages,
            message=final_message,
            start_time=self.session_start_time,
            metadata={
                "session_completed": True,
                "total_time": total_time,
                "stages_completed": len(self.stages_progress)
            }
        )
        
        self._notify_callbacks(completion_progress)
        logger.info(f"会话 {self.session_id} 完成，总耗时: {total_time:.2f}秒")
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """获取整体进度信息"""
        completed_stages = len([p for p in self.stages_progress.values() if p.current >= p.total])
        total_time = time.time() - self.session_start_time
        
        return {
            "session_id": self.session_id,
            "stages_completed": completed_stages,
            "total_stages": self.total_stages,
            "overall_percentage": round((completed_stages / self.total_stages) * 100, 2) if self.total_stages > 0 else 0,
            "total_elapsed_time": total_time,
            "is_completed": self.is_completed,
            "current_stages": {stage.value: asdict(progress) for stage, progress in self.stages_progress.items()}
        }
    
    def _notify_callbacks(self, progress: ProgressInfo):
        """通知所有回调函数"""
        for callback in self.callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"进度回调执行失败: {str(e)}")

class ProgressManager:
    """进度管理器 - 管理多个会话的进度跟踪"""
    
    def __init__(self):
        self.trackers: Dict[str, ProgressTracker] = {}
        self.global_callbacks: List[Callable[[str, ProgressInfo], None]] = []
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def create_tracker(self, session_id: str, total_stages: int = 8) -> ProgressTracker:
        """创建新的进度跟踪器"""
        if session_id in self.trackers:
            logger.warning(f"会话 {session_id} 的跟踪器已存在，将覆盖")
        
        tracker = ProgressTracker(session_id, total_stages)
        
        # 添加全局回调
        for global_callback in self.global_callbacks:
            tracker.add_callback(lambda progress, sid=session_id: global_callback(sid, progress))
        
        self.trackers[session_id] = tracker
        logger.info(f"创建进度跟踪器: {session_id}")
        return tracker
    
    def get_tracker(self, session_id: str) -> Optional[ProgressTracker]:
        """获取进度跟踪器"""
        return self.trackers.get(session_id)
    
    def remove_tracker(self, session_id: str):
        """移除进度跟踪器"""
        if session_id in self.trackers:
            del self.trackers[session_id]
            logger.info(f"移除进度跟踪器: {session_id}")
    
    def add_global_callback(self, callback: Callable[[str, ProgressInfo], None]):
        """添加全局回调函数"""
        self.global_callbacks.append(callback)
        
        # 为现有跟踪器添加回调
        for session_id, tracker in self.trackers.items():
            tracker.add_callback(lambda progress, sid=session_id: callback(sid, progress))
    
    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话的进度信息"""
        return {
            session_id: tracker.get_overall_progress() 
            for session_id, tracker in self.trackers.items()
        }
    
    def cleanup_completed_trackers(self, max_age_seconds: int = 3600):
        """清理已完成的跟踪器"""
        current_time = time.time()
        to_remove = []
        
        for session_id, tracker in self.trackers.items():
            if (tracker.is_completed and 
                current_time - tracker.session_start_time > max_age_seconds):
                to_remove.append(session_id)
        
        for session_id in to_remove:
            self.remove_tracker(session_id)
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个已完成的进度跟踪器")
    
    async def create_async_progress_callback(
        self, 
        session_id: str, 
        stage: ProgressStage
    ) -> Callable[[int, int, str], None]:
        """创建异步进度回调函数"""
        tracker = self.get_tracker(session_id)
        if not tracker:
            logger.warning(f"未找到会话 {session_id} 的跟踪器")
            return lambda current, total, message: None
        
        def progress_callback(current: int, total: int, message: str = ""):
            tracker.update_progress(stage, current, message)
        
        return progress_callback
    
    def create_batch_callback(
        self,
        session_id: str,
        stage: ProgressStage
    ) -> Callable[[int, int, str], None]:
        """为批量处理创建进度回调"""
        tracker = self.get_tracker(session_id)
        if not tracker:
            logger.warning(f"未找到会话 {session_id} 的跟踪器，创建默认跟踪器")
            tracker = self.create_tracker(session_id)
        
        def batch_callback(current: int, total: int, message: str = ""):
            # 如果是第一次调用，开始阶段
            if stage not in tracker.stages_progress:
                tracker.start_stage(stage, total, message or f"开始 {stage.value}")
            else:
                tracker.update_progress(stage, current, message)
        
        return batch_callback

# 全局进度管理器实例
progress_manager = ProgressManager()