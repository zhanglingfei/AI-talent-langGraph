# 批量处理和流式反馈系统

本文档介绍项目中新增的批量处理、流式反馈和进度跟踪功能，这些功能符合 `index.html` 设计规范，提供高性能的大规模数据处理能力。

## 核心特性

### 1. 批量处理机制 (Batch Processing)
- **高并发处理**: 支持多线程和异步批量处理
- **OpenAI API优化**: 支持最多2048个嵌入向量的批量生成
- **自动降级**: 批量失败时自动降级到单个处理
- **错误恢复**: 单个项目失败不影响批次其他项目

### 2. 流式反馈系统 (Streaming Feedback) 
- **实时状态更新**: WebSocket/SSE风格的实时事件流
- **多种事件类型**: 进度、状态、错误、结果、心跳等
- **订阅机制**: 支持多个订阅者接收事件
- **会话管理**: 支持多会话并发处理

### 3. 进度跟踪服务 (Progress Tracking)
- **阶段化管理**: 8个处理阶段的详细进度跟踪
- **时间估算**: 自动计算剩余时间和处理速率
- **回调机制**: 可配置的进度回调函数
- **性能指标**: 详细的性能统计和分析

## 系统架构

```
批量处理层
├── BatchProcessor (基础批量处理器)
├── EmailBatchProcessor (邮件批量处理)
├── EmbeddingBatchProcessor (向量批量处理) 
└── MatchingBatchProcessor (匹配批量处理)

流式反馈层
├── StreamingService (流式服务)
├── ProcessingStreamer (处理流)
├── StreamManager (流管理器)
└── StreamingBatchProcessor (流式批量处理器)

进度跟踪层
├── ProgressTracker (进度跟踪器)
├── ProgressManager (进度管理器)
└── ProgressStage (进度阶段定义)

集成服务层
└── IntegratedProcessingService (集成处理服务)
```

## 主要组件说明

### BatchProcessor
基础批量处理器，提供同步和异步两种处理模式：

```python
from src.services.batch_processor import BatchProcessor

# 创建批量处理器
processor = BatchProcessor(max_workers=4)

# 同步批量处理
results = processor.process_batch_sync(
    items=data_list,
    processor_func=process_function,
    batch_size=50,
    progress_callback=callback_function
)

# 异步批量处理  
results = await processor.process_batch_async(
    items=data_list,
    async_processor=async_process_function,
    batch_size=50,
    max_concurrent=10,
    progress_callback=callback_function
)
```

### EmbeddingBatchProcessor
专门用于向量化处理，符合OpenAI API限制：

```python
from src.services.batch_processor import EmbeddingBatchProcessor

processor = EmbeddingBatchProcessor()

# 批量生成嵌入向量（最多2048个/批次）
embeddings = processor.process_embeddings_batch(
    texts=text_list,
    embedding_service=embedding_service,
    batch_size=2048,
    progress_callback=progress_callback
)
```

### StreamingService
提供实时的处理状态反馈：

```python
from src.services.streaming_service import stream_manager

# 创建流服务
stream_service = stream_manager.create_stream("session_123")

# 订阅事件
def event_handler(event):
    print(f"事件: {event.event_type}, 数据: {event.data}")

stream_service.subscribe(event_handler)

# 发送各种事件
stream_service.emit_progress(current=50, total=100, message="处理中")
stream_service.emit_status("正在分析数据")
stream_service.emit_result({"processed": 50}, "partial")
stream_service.complete({"final_count": 100})
```

### ProgressTracker
详细的进度跟踪和时间估算：

```python
from src.services.progress_service import progress_manager, ProgressStage

# 创建进度跟踪器
tracker = progress_manager.create_tracker("session_123", total_stages=6)

# 开始阶段
tracker.start_stage(ProgressStage.EMAIL_CLASSIFICATION, total_items=100)

# 更新进度
tracker.update_progress(ProgressStage.EMAIL_CLASSIFICATION, current=50, message="处理邮件")

# 完成阶段
tracker.complete_stage(ProgressStage.EMAIL_CLASSIFICATION, "分类完成")
```

## 权重配置系统

符合 `index.html` 设计的匹配权重配置：

```python
# config.py
MATCHING_WEIGHTS = {
    # 标准Qdrant混合搜索权重 (Vector: 70%, Filters: 30%)
    "VECTOR_SIMILARITY": 0.7,
    "METADATA_FILTERS": 0.3,
    
    # 高级混合评分权重
    "HYBRID_VECTOR": 0.4,
    "HYBRID_AI": 0.35, 
    "HYBRID_BUSINESS": 0.25
}
```

在Qdrant服务中的应用：
```python
# 使用加权搜索
results = qdrant_service.search_candidates(
    query="Python开发工程师",
    filters={"experience_years": "5+"},
    use_weighted_search=True  # 启用70/30权重分配
)
```

## 集成使用示例

### 完整的批量处理流程
```python
from src.services.integrated_processing_service import integrated_service

# 执行带有流式反馈的批量处理
result = await integrated_service.process_emails_with_streaming(
    emails=email_list,
    session_id="batch_001", 
    enable_streaming=True,
    enable_progress_tracking=True
)

# 获取处理结果
print(f"处理邮件: {result['processing_summary']['emails_processed']}")
print(f"候选人: {result['processing_summary']['candidates_extracted']}")
print(f"项目: {result['processing_summary']['projects_extracted']}")
print(f"匹配: {result['processing_summary']['matches_generated']}")
```

### 事件订阅和处理
```python
# 创建事件处理器
def handle_stream_events(event):
    if event.event_type == "progress":
        data = event.data
        print(f"进度: {data['current']}/{data['total']} ({data['percentage']}%)")
        if 'estimated_remaining' in data:
            print(f"预估剩余: {data['estimated_remaining']:.1f}秒")
    
    elif event.event_type == "result":
        result_data = event.data
        if result_data.get('result_type') == 'batch_complete':
            print(f"批次完成: {result_data['result']}")

# 订阅流事件
stream_service = stream_manager.get_stream("batch_001")
stream_service.subscribe(handle_stream_events)
```

## 性能优化特性

### 1. 批量向量化优化
- **批次大小优化**: 自动使用2048的批次大小，符合OpenAI API限制
- **并发控制**: 限制并发请求数量，避免API限流
- **错误恢复**: 批量失败时自动降级到单个处理

### 2. 数据库批量操作
- **批量插入**: Qdrant支持批量点插入操作
- **并发写入**: 多线程并发写入向量数据库
- **索引优化**: 合理的向量索引配置

### 3. 内存管理
- **分批处理**: 大数据集分批处理，避免内存溢出
- **流式处理**: 流式处理大文件，降低内存占用
- **资源清理**: 自动清理完成的会话资源

## 监控和调试

### 进度监控
```python
# 获取会话整体进度
progress = progress_manager.get_tracker("session_123").get_overall_progress()

print(f"完成阶段: {progress['stages_completed']}/{progress['total_stages']}")
print(f"总进度: {progress['overall_percentage']}%")
print(f"运行时间: {progress['total_elapsed_time']:.2f}秒")
```

### 性能分析
```python
# 获取性能指标
performance = result['performance_metrics']
print(f"处理速度: {performance['items_per_second']:.2f} 项/秒")
print(f"总处理时间: {performance['total_processing_time']:.2f}秒")
```

### 错误处理
```python
# 流式错误处理
def error_handler(event):
    if event.event_type == "error":
        error_data = event.data
        logger.error(f"处理错误: {error_data['message']}")
        if 'traceback' in error_data:
            logger.debug(f"错误详情: {error_data['traceback']}")

stream_service.subscribe(error_handler)
```

## 配置参数

### 批量处理配置
```python
# config.py 中的相关配置
EMAIL_BATCH_SIZE = 10        # 邮件批处理大小
MAX_RETRIES = 3              # 最大重试次数
EMBEDDING_BATCH_SIZE = 2048  # 向量化批次大小（OpenAI限制）
```

### 流式服务配置  
```python
# 心跳间隔
HEARTBEAT_INTERVAL = 30.0    # 秒

# 会话超时
SESSION_TIMEOUT = 3600       # 秒

# 最大订阅者数量
MAX_SUBSCRIBERS = 10
```

## 使用最佳实践

### 1. 批量处理最佳实践
- 根据数据大小选择合适的批次大小
- 为长时间运行的批处理启用进度跟踪
- 使用异步处理提高并发性能
- 实现适当的错误恢复机制

### 2. 流式反馈最佳实践
- 订阅必要的事件类型，避免信息过载
- 实现事件处理的错误捕获
- 及时清理完成的会话资源
- 使用心跳机制监控连接状态

### 3. 进度跟踪最佳实践
- 合理设置阶段划分，提供有意义的进度信息
- 使用回调函数实现自定义进度处理
- 监控性能指标，优化处理流程
- 为用户提供时间估算信息

## 故障排除

### 常见问题和解决方案

1. **批量处理卡住**
   - 检查线程池配置
   - 验证数据格式正确性
   - 查看错误日志获取详细信息

2. **流式事件丢失**
   - 确认订阅函数正确注册
   - 检查事件类型匹配
   - 验证会话ID有效性

3. **进度跟踪不准确**
   - 确认阶段总数设置正确
   - 检查进度更新调用时机
   - 验证回调函数执行正常

4. **内存使用过高**
   - 减小批次大小
   - 启用流式处理
   - 及时清理会话资源

## 扩展和定制

系统设计具有良好的可扩展性，支持以下定制：

1. **自定义批量处理器**: 继承`BatchProcessor`类
2. **自定义事件类型**: 扩展`StreamEventType`枚举
3. **自定义进度阶段**: 扩展`ProgressStage`枚举  
4. **自定义回调机制**: 实现特定的回调函数

## 总结

新的批量处理和流式反馈系统提供了：

- **高性能**: 支持大规模数据的高效处理
- **实时反馈**: 提供详细的处理状态和进度信息
- **可扩展性**: 模块化设计，易于扩展和定制
- **可靠性**: 完善的错误处理和恢复机制
- **符合规范**: 严格按照`index.html`设计实现

这些功能显著提升了系统的用户体验和处理能力，特别适用于大规模的人才匹配和邮件处理场景。