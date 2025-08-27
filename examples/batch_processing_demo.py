"""
批量处理和流式反馈演示
展示新功能的完整集成使用示例
"""

import asyncio
import time
from typing import List
from src.services.integrated_processing_service import integrated_service
from src.services.streaming_service import stream_manager, StreamEventType
from src.services.progress_service import progress_manager
from src.models import EmailInfo
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 模拟邮件数据
SAMPLE_EMAILS = [
    EmailInfo(
        id="email_1",
        sender="candidate1@example.com",
        subject="求职申请 - 高级Python开发工程师",
        content="""
        您好，我是张三，有5年Python开发经验，熟悉Django、Flask框架，
        具有大型项目经验。我的技能包括：
        - Python、Django、Flask
        - MySQL、PostgreSQL
        - Redis、Elasticsearch
        - AWS、Docker
        希望能够加入贵司团队。
        """,
        timestamp="2024-01-15T10:00:00Z"
    ),
    EmailInfo(
        id="email_2", 
        sender="hr@techcorp.com",
        subject="项目外包需求 - 电商平台开发",
        content="""
        我们需要开发一个电商平台，技术要求如下：
        - 后端: Python/Django或Java/Spring
        - 前端: React或Vue.js
        - 数据库: MySQL
        - 项目周期: 3个月
        - 预算: 50万人民币
        有兴趣的团队请联系我们。
        """,
        timestamp="2024-01-15T11:00:00Z"
    ),
    EmailInfo(
        id="email_3",
        sender="candidate2@example.com", 
        subject="简历投递 - React前端开发",
        content="""
        您好，我是李四，专注前端开发3年，技能如下：
        - React、Vue.js、Angular
        - TypeScript、JavaScript
        - Node.js、Express
        - 移动端开发经验
        期待您的回复。
        """,
        timestamp="2024-01-15T12:00:00Z"
    ),
    EmailInfo(
        id="email_4",
        sender="pm@startup.com",
        subject="AI项目合作机会",
        content="""
        我们是一家AI创业公司，需要以下技术支持：
        - 机器学习算法开发
        - Python、TensorFlow、PyTorch
        - 数据分析和可视化
        - 项目时长: 6个月
        寻找有经验的AI工程师合作。
        """,
        timestamp="2024-01-15T13:00:00Z"
    )
]

async def demo_streaming_callback():
    """演示流式回调的使用"""
    session_id = "demo_session_001"
    
    # 创建流服务
    stream_service = stream_manager.create_stream(session_id)
    
    # 订阅所有事件
    def event_handler(event):
        print(f"[{event.timestamp:.2f}] {event.event_type.value.upper()}: {event.data.get('message', '')}")
        
        if event.event_type == StreamEventType.PROGRESS:
            progress_data = event.data
            print(f"    进度: {progress_data['current']}/{progress_data['total']} ({progress_data['percentage']}%)")
            if 'estimated_remaining' in progress_data:
                print(f"    预估剩余时间: {progress_data['estimated_remaining']:.1f}秒")
        
        elif event.event_type == StreamEventType.RESULT:
            result_data = event.data
            if result_data.get('result_type') == 'email_batch_result':
                result = result_data['result']
                print(f"    邮件处理完成: 成功率 {result.get('success_rate', 0):.1%}")
        
        elif event.event_type == StreamEventType.COMPLETE:
            print("    === 处理完成 ===")
            final_result = event.data.get('final_result', {})
            if 'processing_summary' in final_result:
                summary = final_result['processing_summary']
                print(f"    总结: 处理邮件{summary.get('emails_processed', 0)}封, "
                      f"发现候选人{summary.get('candidates_extracted', 0)}个, "
                      f"项目{summary.get('projects_extracted', 0)}个")
    
    stream_service.subscribe(event_handler)
    
    return session_id

async def demo_progress_tracking():
    """演示进度跟踪的使用"""
    session_id = "demo_session_002"
    
    # 创建进度跟踪器
    tracker = progress_manager.create_tracker(session_id, total_stages=3)
    
    # 添加进度回调
    def progress_callback(progress_info):
        print(f"[进度] {progress_info.stage.value}: {progress_info.current}/{progress_info.total} "
              f"({progress_info.percentage}%) - {progress_info.message}")
        
        if progress_info.elapsed_time > 0:
            print(f"        已用时间: {progress_info.elapsed_time:.1f}秒")
    
    tracker.add_callback(progress_callback)
    
    return session_id

async def demo_batch_processing():
    """演示完整的批量处理流程"""
    print("=== 批量处理和流式反馈演示 ===\n")
    
    # 设置回调
    session_id = await demo_streaming_callback()
    print(f"会话ID: {session_id}\n")
    
    # 开始批量处理
    print("开始批量处理邮件...")
    start_time = time.time()
    
    try:
        result = await integrated_service.process_emails_with_streaming(
            emails=SAMPLE_EMAILS,
            session_id=session_id,
            enable_streaming=True,
            enable_progress_tracking=True
        )
        
        processing_time = time.time() - start_time
        
        print(f"\n=== 处理完成 (耗时: {processing_time:.2f}秒) ===")
        print(f"会话ID: {result['session_id']}")
        
        summary = result['processing_summary']
        print(f"邮件处理: {summary['emails_processed']} 封")
        print(f"候选人提取: {summary['candidates_extracted']} 个")
        print(f"项目提取: {summary['projects_extracted']} 个")
        print(f"候选人保存: {summary['candidates_saved']} 个")
        print(f"项目保存: {summary['projects_saved']} 个")
        print(f"匹配生成: {summary['matches_generated']} 个")
        
        print(f"\n成功率统计:")
        success_rates = summary['success_rate']
        print(f"  邮件处理: {success_rates['email_processing']:.1%}")
        print(f"  候选人存储: {success_rates['candidate_storage']:.1%}")
        print(f"  项目存储: {success_rates['project_storage']:.1%}")
        
        performance = result['performance_metrics']
        print(f"\n性能指标:")
        print(f"  处理速度: {performance['items_per_second']:.2f} 邮件/秒")
        print(f"  完成阶段: {performance['stages_completed']}")
        
        # 展示部分结果
        if result['detailed_results']['candidates']:
            print(f"\n发现的候选人:")
            for i, candidate in enumerate(result['detailed_results']['candidates'][:2]):
                print(f"  {i+1}. {candidate.get('name', 'Unknown')} - {candidate.get('title', 'Unknown')}")
        
        if result['detailed_results']['projects']:
            print(f"\n发现的项目:")
            for i, project in enumerate(result['detailed_results']['projects'][:2]):
                print(f"  {i+1}. {project.get('title', 'Unknown')} - {project.get('type', 'Unknown')}")
        
    except Exception as e:
        print(f"处理失败: {str(e)}")
        
    finally:
        # 清理资源
        integrated_service.cleanup_session(session_id)
        print(f"\n会话 {session_id} 已清理")

async def demo_individual_services():
    """演示各个服务的单独使用"""
    print("\n=== 单独服务演示 ===")
    
    # 1. 批量向量化演示
    print("\n1. 批量向量化演示:")
    from src.services.embedding_service import EmbeddingService
    
    embedding_service = EmbeddingService()
    texts = [
        "Python开发工程师，5年经验",
        "React前端开发，3年经验", 
        "电商平台开发项目",
        "AI项目合作机会"
    ]
    
    print(f"   正在为 {len(texts)} 个文本生成向量...")
    embeddings = embedding_service.create_batch_embeddings(texts)
    print(f"   完成! 生成了 {len(embeddings)} 个向量")
    
    # 2. Qdrant搜索演示
    print("\n2. 向量搜索演示:")
    from src.services.qdrant_service import QdrantService
    
    try:
        qdrant_service = QdrantService()
        
        # 搜索候选人
        search_results = qdrant_service.search_candidates(
            query="Python开发经验丰富",
            limit=3,
            use_weighted_search=True
        )
        print(f"   搜索结果: 找到 {len(search_results)} 个相关候选人")
        
        for i, result in enumerate(search_results[:2]):
            score = result.get('final_score', result.get('similarity_score', 0))
            print(f"   {i+1}. 相似度: {score:.3f} - {result.get('name', 'Unknown')}")
            
    except Exception as e:
        print(f"   Qdrant搜索演示跳过 (需要Qdrant服务): {str(e)}")

if __name__ == "__main__":
    # 设置日志
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 运行演示
    asyncio.run(demo_batch_processing())
    asyncio.run(demo_individual_services())
    
    print("\n=== 演示结束 ===")