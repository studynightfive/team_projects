# 健康检查接口模块
# 提供存活检查（/health/live）和就绪检查（/health/ready）
# 方案第17.4节：监控必须覆盖健康检查

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from tempfile import TemporaryFile

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text

from app.common.config import settings
from app.common.database import engine
from app.rag.guard import guard_readiness_status

router = APIRouter(tags=["health"])


# ============================================================
# 响应模型
# ============================================================
class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: str


class ReadyCheckResponse(BaseModel):
    """就绪检查响应模型"""
    status: str
    checks: dict[str, str]
    timestamp: str


_CHECK_TIMEOUT_SECONDS = 2.0


async def _check_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def _check_redis() -> None:
    client = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=_CHECK_TIMEOUT_SECONDS,
        socket_timeout=_CHECK_TIMEOUT_SECONDS,
    )
    try:
        await client.ping()
    finally:
        await client.aclose()


def _check_storage() -> None:
    root = Path(settings.storage_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with TemporaryFile(dir=root) as probe:
        probe.write(b"health")
        probe.flush()


async def _run_async_check(check: Callable[[], Awaitable[None]]) -> str:
    try:
        await asyncio.wait_for(check(), timeout=_CHECK_TIMEOUT_SECONDS)
    except Exception:
        return "unavailable"
    return "ok"


def _run_storage_check() -> str:
    try:
        _check_storage()
    except Exception:
        return "unavailable"
    return "ok"


# ============================================================
# 存活检查：GET /api/v1/health/live
# 用于 Kubernetes 或 Docker 的 liveness probe
# 只要进程存活就返回 200
# ============================================================
@router.get("/health/live", response_model=HealthCheckResponse)
async def health_live() -> HealthCheckResponse:
    """
    存活检查端点
    返回 200 表示进程正常运行
    用于 Docker HEALTHCHECK 和编排系统
    """
    return HealthCheckResponse(
        status="ok",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )


# ============================================================
# 就绪检查：GET /api/v1/health/ready
# 用于 Kubernetes 或 Docker 的 readiness probe
# 检查数据库、Redis、文件存储和输入安全模型是否可用
# 全部通过返回 200，任一失败返回 503
# ============================================================
@router.get("/health/ready", response_model=ReadyCheckResponse)
async def health_ready() -> ReadyCheckResponse | JSONResponse:
    """
    就绪检查端点
    检查内容：
    1. 数据库连接：执行 SELECT 1
    2. Redis 连接：执行 PING
    3. 文件存储：检查存储目录是否可读写
    4. LLM Guard：启用预热时确认安全模型已经加载
    """
    database_status, redis_status = await asyncio.gather(
        _run_async_check(_check_database),
        _run_async_check(_check_redis),
    )
    checks = {
        "database": database_status,
        "redis": redis_status,
        "storage": _run_storage_check(),
        "llm_guard": guard_readiness_status(),
    }

    # 判断整体状态
    all_ok = all(v == "ok" for v in checks.values())
    status = "ok" if all_ok else "degraded"

    payload = ReadyCheckResponse(
        status=status,
        checks=checks,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    if not all_ok:
        return JSONResponse(
            status_code=503,
            content=payload.model_dump(),
        )

    return payload
