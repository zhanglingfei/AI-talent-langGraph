"""
流式反馈服务 - 提供实时处理进度反馈
符合index.html设计：支持WebSocket和SSE流式通信
"""

import asyncio
import json
import time
from typing import Dict, Any, Callable, Optional, AsyncIterator, List
from dataclasses import dataclass, asdict
from enum import Enum
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class StreamEventType(str, Enum):
    """流事件类型"""
    PROGRESS = "progress"
    STATUS = "status"
    ERROR = "error"
    RESULT = "result"
    HEARTBEAT = "heartbeat"
    COMPLETE = "complete"

@dataclass
class StreamEvent:
    """流事件数据结构"""
    event_type: StreamEventType
    timestamp: float
    session_id: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

class StreamingService:
    """流式反馈服务"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.subscribers: List[Callable[[StreamEvent], None]] = []
        self.is_active = True
        self.start_time = time.time()
        self.last_heartbeat = time.time()
        
    def subscribe(self, callback: Callable[[StreamEvent], None]):
        """订阅流事件"""
        self.subscribers.append(callback)
        logger.debug(f"新的订阅者加入 {self.session_id}, 总订阅者数: {len(self.subscribers)}")
    
    def unsubscribe(self, callback: Callable[[StreamEvent], None]):
        """取消订阅"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
        logger.debug(f"订阅者退出 {self.session_id}, 剩余订阅者数: {len(self.subscribers)}")
    
    def emit_event(self, event_type: StreamEventType, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """发送流事件"""
        if not self.is_active:
            return
            
        event = StreamEvent(
            event_type=event_type,
            timestamp=time.time(),
            session_id=self.session_id,
            data=data,
            metadata=metadata
        )
        
        # 通知所有订阅者
        for callback in self.subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"流事件回调失败: {str(e)}")
    
    def emit_progress(self, current: int, total: int, message: str = "", stage: str = ""):
        """发送进度事件"""
        progress_data = {
            "current": current,
            "total": total,
            "percentage": round((current / total) * 100, 2) if total > 0 else 0,
            "message": message,
            "stage": stage,
            "elapsed_time": round(time.time() - self.start_time, 2)
        }
        
        # 估算剩余时间
        if current > 0 and total > current:
            elapsed = time.time() - self.start_time
            estimated_total = elapsed * total / current
            estimated_remaining = estimated_total - elapsed
            progress_data["estimated_remaining"] = round(estimated_remaining, 2)
        
        self.emit_event(StreamEventType.PROGRESS, progress_data)
    
    def emit_status(self, status: str, details: Optional[Dict[str, Any]] = None):
        """发送状态事件"""
        status_data = {
            "status": status,
            "details": details or {},
            "session_uptime": round(time.time() - self.start_time, 2)
        }
        self.emit_event(StreamEventType.STATUS, status_data)
    
    def emit_error(self, error_message: str, error_code: Optional[str] = None, traceback: Optional[str] = None):
        """发送错误事件"""
        error_data = {
            "message": error_message,
            "code": error_code,
            "traceback": traceback,
            "timestamp": time.time()
        }
        self.emit_event(StreamEventType.ERROR, error_data)
    
    def emit_result(self, result: Dict[str, Any], result_type: str = "partial"):
        """发送结果事件"""
        result_data = {
            "result": result,
            "result_type": result_type,
            "timestamp": time.time()
        }
        self.emit_event(StreamEventType.RESULT, result_data)
    
    def emit_heartbeat(self):
        """发送心跳事件"""
        heartbeat_data = {
            "timestamp": time.time(),
            "session_uptime": round(time.time() - self.start_time, 2),
            "subscriber_count": len(self.subscribers)
        }
        self.emit_event(StreamEventType.HEARTBEAT, heartbeat_data)
        self.last_heartbeat = time.time()
    
    def complete(self, final_result: Optional[Dict[str, Any]] = None):
        """完成处理"""
        completion_data = {
            "final_result": final_result,
            "total_time": round(time.time() - self.start_time, 2),
            "completed_at": time.time()
        }
        self.emit_event(StreamEventType.COMPLETE, completion_data)
        self.is_active = False
        logger.info(f"流式会话完成: {self.session_id}")
    
    async def start_heartbeat_loop(self, interval: float = 30.0):
        """启动心跳循环"""
        while self.is_active:
            self.emit_heartbeat()
            await asyncio.sleep(interval)

class ProcessingStreamer:
    """处理过程流式反馈器"""
    
    def __init__(self, stream_service: StreamingService, stage_name: str):
        self.stream_service = stream_service
        self.stage_name = stage_name
        self.stage_start_time = time.time()
        self.current_step = 0
        self.total_steps = 0
    
    def set_total_steps(self, total: int):
        """设置总步骤数"""
        self.total_steps = total
        self.stream_service.emit_status(
            f"开始阶段: {self.stage_name}",
            {"total_steps": total, "stage": self.stage_name}
        )
    
    def update_progress(self, step: int, message: str = ""):
        """更新进度"""
        self.current_step = step
        self.stream_service.emit_progress(
            current=step,
            total=self.total_steps,
            message=message,
            stage=self.stage_name
        )
    
    def log_step(self, step_name: str, result: Optional[Dict[str, Any]] = None):
        """记录步骤"""
        self.current_step += 1
        self.update_progress(self.current_step, f"执行: {step_name}")
        
        if result:
            self.stream_service.emit_result(result, "step_result")
    
    def complete_stage(self, stage_result: Optional[Dict[str, Any]] = None):
        """完成阶段"""
        stage_time = round(time.time() - self.stage_start_time, 2)
        completion_data = {
            "stage": self.stage_name,
            "stage_time": stage_time,
            "steps_completed": self.current_step,
            "result": stage_result
        }
        self.stream_service.emit_result(completion_data, "stage_complete")

class StreamingBatchProcessor:
    """流式批量处理器"""
    
    def __init__(self, stream_service: StreamingService):
        self.stream_service = stream_service
    
    def create_batch_callback(self, stage_name: str, total_items: int) -> Callable[[int, int, str], None]:
        """创建批量处理回调"""
        def batch_callback(completed: int, total: int, message: str = ""):
            self.stream_service.emit_progress(
                current=completed,
                total=total,
                message=message,
                stage=stage_name
            )
            
            # 每10%或每100个项目发送中间结果
            if completed % max(1, total // 10) == 0 or completed % 100 == 0:
                self.stream_service.emit_result({
                    "stage": stage_name,
                    "completed": completed,
                    "total": total,
                    "progress_percentage": round((completed / total) * 100, 2)
                }, "batch_progress")
        
        return batch_callback
    
    async def stream_async_batch(
        self,
        items: List[Any],
        processor_func: Callable[[Any], Any],
        stage_name: str,
        batch_size: int = 50
    ) -> List[Any]:
        """异步流式批量处理"""
        total_items = len(items)
        results = []
        
        callback = self.create_batch_callback(stage_name, total_items)
        
        # 导入批量处理器
        from src.services.batch_processor import BatchProcessor
        batch_processor = BatchProcessor()
        
        try:
            self.stream_service.emit_status(f"开始批量处理: {stage_name}", {
                "total_items": total_items,
                "batch_size": batch_size
            })
            
            # 执行异步批量处理
            results = await batch_processor.process_batch_async(
                items=items,
                async_processor=processor_func,
                batch_size=batch_size,
                progress_callback=callback
            )
            
            self.stream_service.emit_result({
                "stage": stage_name,
                "total_processed": len(results),
                "successful": len([r for r in results if r is not None]),
                "failed": len([r for r in results if r is None])
            }, "batch_complete")
            
            return results
            
        except Exception as e:
            self.stream_service.emit_error(f"批量处理失败: {str(e)}", "batch_processing_error")
            raise

# 全局流服务管理器
class StreamManager:
    """流服务管理器"""
    
    _instance = None
    _streams: Dict[str, StreamingService] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_stream(self, session_id: str) -> StreamingService:
        """创建流服务"""
        if session_id in self._streams:
            logger.warning(f"流会话已存在: {session_id}")
            return self._streams[session_id]
        
        stream_service = StreamingService(session_id)
        self._streams[session_id] = stream_service
        logger.info(f"创建新的流会话: {session_id}")
        return stream_service
    
    def get_stream(self, session_id: str) -> Optional[StreamingService]:
        """获取流服务"""
        return self._streams.get(session_id)
    
    def remove_stream(self, session_id: str):
        """移除流服务"""
        if session_id in self._streams:
            self._streams[session_id].is_active = False
            del self._streams[session_id]
            logger.info(f"移除流会话: {session_id}")
    
    def get_active_streams(self) -> List[str]:
        """获取活跃流列表"""
        return [sid for sid, stream in self._streams.items() if stream.is_active]
    
    def cleanup_inactive_streams(self):
        """清理非活跃流"""
        inactive_sessions = [
            sid for sid, stream in self._streams.items() 
            if not stream.is_active or (time.time() - stream.last_heartbeat) > 300
        ]
        
        for session_id in inactive_sessions:
            self.remove_stream(session_id)
        
        if inactive_sessions:
            logger.info(f"清理了 {len(inactive_sessions)} 个非活跃流会话")

# 全局实例
stream_manager = StreamManager()