"""ARQ enqueue helpers shared by API services."""

from arq.connections import RedisSettings, create_pool


async def enqueue_document_task(document_id: str, task_id: str, redis_url: str) -> None:
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    try:
        await redis.enqueue_job(
            "process_document_task",
            document_id,
            task_id,
            _job_id=task_id,
        )
    finally:
        await redis.aclose()


async def enqueue_document_tasks(
    tasks: list[tuple[str, str]],
    redis_url: str,
) -> dict[str, str]:
    """复用一个 Redis 连接池入队一批文档，返回 task_id 到安全错误类型的映射。"""
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    failures: dict[str, str] = {}
    try:
        for document_id, task_id in tasks:
            try:
                await redis.enqueue_job(
                    "process_document_task",
                    document_id,
                    task_id,
                    _job_id=task_id,
                )
            except Exception as exc:
                failures[task_id] = type(exc).__name__
    finally:
        await redis.aclose()
    return failures


async def enqueue_export_task(task_id: str, redis_url: str) -> None:
    redis = await create_pool(RedisSettings.from_dsn(redis_url))
    try:
        await redis.enqueue_job("process_export_task", task_id, _job_id=f"export:{task_id}")
    finally:
        await redis.aclose()
