from unittest.mock import AsyncMock, MagicMock

import pytest

from app.worker import queue
from app.worker import settings as worker_settings


@pytest.mark.asyncio
async def test_enqueue_document_task_uses_task_id_for_idempotency(monkeypatch) -> None:
    redis = AsyncMock()
    create_pool = AsyncMock(return_value=redis)
    monkeypatch.setattr(queue, "create_pool", create_pool)

    await queue.enqueue_document_task(
        "document-id",
        "task-id",
        "redis://redis:6379/0",
    )

    redis.enqueue_job.assert_awaited_once_with(
        "process_document_task",
        "document-id",
        "task-id",
        _job_id="task-id",
    )
    redis.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_worker_redis_health_check_requires_recent_worker_heartbeat(monkeypatch) -> None:
    redis = AsyncMock()
    redis.ping.return_value = True
    redis.get.return_value = b"healthy"
    create_pool = AsyncMock(return_value=redis)
    monkeypatch.setattr(worker_settings, "create_pool", create_pool)

    assert await worker_settings.redis_is_reachable() is True

    create_pool.assert_awaited_once()
    redis.ping.assert_awaited_once_with()
    redis.get.assert_awaited_once_with("arq:queue:health-check")
    redis.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_worker_redis_health_check_rejects_missing_heartbeat(monkeypatch) -> None:
    redis = AsyncMock()
    redis.ping.return_value = True
    redis.get.return_value = None
    monkeypatch.setattr(worker_settings, "create_pool", AsyncMock(return_value=redis))

    assert await worker_settings.redis_is_reachable() is False
    redis.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_worker_redis_health_check_closes_after_ping_failure(monkeypatch) -> None:
    redis = AsyncMock()
    redis.ping.side_effect = ConnectionError("redis unavailable")
    monkeypatch.setattr(worker_settings, "create_pool", AsyncMock(return_value=redis))

    with pytest.raises(ConnectionError, match="redis unavailable"):
        await worker_settings.redis_is_reachable()

    redis.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_scheduled_export_cleanup_reuses_cleanup_service(monkeypatch) -> None:
    session = AsyncMock()
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)
    cleanup_expired = AsyncMock(return_value=2)
    monkeypatch.setattr(worker_settings, "async_session_factory", lambda: session_context)
    monkeypatch.setattr(worker_settings, "cleanup_expired", cleanup_expired)

    assert await worker_settings.cleanup_export_tasks({}) == 2

    cleanup_expired.assert_awaited_once_with(session)
    cleanup_job = next(
        job
        for job in worker_settings.WorkerSettings.cron_jobs
        if job.coroutine is worker_settings.cleanup_export_tasks
    )
    assert cleanup_job.minute == 0
    assert cleanup_job.second == 0
