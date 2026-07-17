# Worker 任务队列配置
# 员工4：文档转换；员工5：导出任务

from arq.connections import RedisSettings

from app.common.config import settings
from app.common.database import async_session_factory
from app.documents.service import DocumentService


async def process_document_task(ctx: dict, document_id: str, task_id: str) -> str:
    """异步文档转换任务入口。"""
    async with async_session_factory() as session:
        service = DocumentService(session)
        await service.process_document(document_id, task_id)
        await session.commit()
    return "ok"


class WorkerSettings:
    """arq Worker 配置"""

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [process_document_task]
    job_timeout = 3600
    keep_result = 3600
    max_jobs = 10
