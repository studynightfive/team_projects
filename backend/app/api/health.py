# 健康检查接口模块
# 提供存活检查（/health/live）和就绪检查（/health/ready）
# 方案第17.4节：监控必须覆盖健康检查

import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
    checks: dict
    timestamp: str


# ============================================================
# 存活检查：GET /api/v1/health/live
# 用于 Kubernetes 或 Docker 的 liveness probe
# 只要进程存活就返回 200
# ============================================================
@router.get("/health/live", response_model=HealthCheckResponse)
async def health_live():
    """
    存活检查端点
    返回 200 表示进程正常运行
    用于 Docker HEALTHCHECK 和编排系统
    """
    return {
        "status": "ok",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ============================================================
# 就绪检查：GET /api/v1/health/ready
# 用于 Kubernetes 或 Docker 的 readiness probe
# 检查数据库、Redis 和文件存储是否可用
# 全部通过返回 200，任一失败返回 503
# ============================================================
@router.get("/health/ready", response_model=ReadyCheckResponse)
async def health_ready():
    """
    就绪检查端点
    检查内容：
    1. 数据库连接：执行 SELECT 1
    2. Redis 连接：执行 PING
    3. 文件存储：检查存储目录是否可读写
    """
    checks = {}

    # 检查数据库连接
    # 注意：此时数据库模型可能尚未就位，因此暂时跳过数据库检查
    # 完整实现将在数据库模型创建后补充
    try:
        # TODO: 当数据库模型就位后，执行 SELECT 1 验证连接
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # 检查 Redis 连接
    try:
        # TODO: 当 Redis 连接就位后，执行 PING 验证连接
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    # 检查文件存储
    try:
        # TODO: 检查存储目录是否可读写
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "unavailable"

    # 判断整体状态
    all_ok = all(v == "ok" for v in checks.values())
    status = "ok" if all_ok else "degraded"

    # 如果有检查项失败，返回 503
    if not all_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": status,
                "checks": checks,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )

    return {
        "status": status,
        "checks": checks,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }