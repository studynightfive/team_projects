# Worker 任务队列配置
# 员工4：文档转换；员工5：导出任务

from typing import cast

from arq import cron
from arq.connections import ArqRedis, RedisSettings, create_pool
from sqlalchemy import select

from app.common.config import settings
from app.common.database import async_session_factory
from app.documents.models import DocumentTask, TaskStatus
from app.documents.service import DocumentService
from app.exports.all import ExportTask, _run_export, cleanup_expired

_WORKER_HEALTH_KEY = "arq:queue:health-check"


async def process_document_task(
    _ctx: dict[str, object], document_id: str, task_id: str
) -> str:
    """异步文档转换任务入口。"""
    async with async_session_factory() as session:
        service = DocumentService(session)
        await service.process_document(document_id, task_id)
        await session.commit()
    return "ok"


async def process_export_task(_ctx: dict[str, object], task_id: str) -> str:
    """异步导出任务入口。"""
    async with async_session_factory() as session:
        await _run_export(session, task_id)
    return "ok"


async def reconcile_document_tasks(ctx: dict[str, object]) -> int:
    """周期性补投数据库中仍处于 queued 的任务，收敛提交后进程崩溃的丢任务窗口。"""
    redis = cast(ArqRedis, ctx["redis"])
    async with async_session_factory() as session:
        result = await session.execute(
            select(DocumentTask)
            .where(DocumentTask.status == TaskStatus.QUEUED.value)
            .order_by(DocumentTask.created_at.asc())
            .limit(100)
        )
        tasks = list(result.scalars())
    for task in tasks:
        await redis.enqueue_job(
            "process_document_task",
            task.document_id,
            task.id,
            _job_id=task.id,
        )
    return len(tasks)


async def reconcile_export_tasks(ctx: dict[str, object]) -> int:
    """补投创建后仍处于 pending 的导出任务。"""
    redis = cast(ArqRedis, ctx["redis"])
    async with async_session_factory() as session:
        result = await session.execute(
            select(ExportTask)
            .where(ExportTask.status == "pending")
            .order_by(ExportTask.created_at.asc())
            .limit(100)
        )
        tasks = list(result.scalars())
    for task in tasks:
        await redis.enqueue_job(
            "process_export_task",
            task.id,
            _job_id=f"export:{task.id}",
        )
    return len(tasks)


async def cleanup_export_tasks(ctx: dict[str, object]) -> int:
    """周期性清理已过期且处于终态的导出任务。"""
    del ctx
    async with async_session_factory() as session:
        return await cleanup_expired(session)


async def cleanup_deleted_documents(ctx: dict[str, object]) -> int:
    """周期性物理清理已超过回收站保留期的文档。"""
    del ctx
    async with async_session_factory() as session:
        return await DocumentService(session).purge_expired_documents()


async def redis_is_reachable() -> bool:
    """同时验证 Redis 与 ARQ Worker 最近写入的事件循环心跳。"""
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        redis_ok = bool(await redis.ping())
        worker_heartbeat = await redis.get(_WORKER_HEALTH_KEY)
        return redis_ok and worker_heartbeat is not None
    finally:
        await redis.aclose()


class WorkerSettings:
    """arq Worker 配置"""

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [process_document_task, process_export_task]
    cron_jobs = [
        cron(reconcile_document_tasks, second={15, 45}),
        cron(reconcile_export_tasks, second={20, 50}),
        cron(cleanup_export_tasks, minute=0),
        cron(cleanup_deleted_documents, hour=2, minute=30),
    ]
    job_timeout = 3600
    keep_result = 3600
    # 心跳过期可发现 Redis 断连或事件循环被同步解析卡死，而不只检查 PID。
    health_check_interval = 10
    # Office/PDF/OCR 都是高内存任务，限制并发以避免单容器资源争抢。
    max_jobs = 4
