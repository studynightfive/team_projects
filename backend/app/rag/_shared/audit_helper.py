"""审计写入包装（员工5 跨模块统一封装）"""

from __future__ import annotations

from typing import TypedDict

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import normalize_bounded_audit_text, write_audit_log

logger = structlog.get_logger()


class RequestContext(TypedDict, total=False):
    ip_address: str | None
    user_agent: str | None
    request_id: str | None


def _extract_request_ctx(request: Request | None) -> RequestContext:
    if request is None:
        return {}
    state = getattr(request, "state", None)
    return {
        "ip_address": normalize_bounded_audit_text(
            request.client.host if request.client else None,
            45,
        ),
        "user_agent": normalize_bounded_audit_text(
            request.headers.get("user-agent"),
            500,
        ),
        "request_id": normalize_bounded_audit_text(
            getattr(state, "request_id", None),
            36,
        ),
    }


async def audit(
    db: AsyncSession,
    *,
    action: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    result: str = "success",
    request: Request | None = None,
) -> None:
    """写入一条审计日志。永不抛出异常。"""
    ctx = _extract_request_ctx(request)
    try:
        # savepoint 将审计约束错误与外层业务事务隔离。
        async with db.begin_nested():
            await write_audit_log(
                db,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                result=result,
                ip_address=ctx.get("ip_address"),
                user_agent=ctx.get("user_agent"),
                request_id=ctx.get("request_id"),
            )
    except Exception as exc:
        # 只记录异常类型，避免数据库错误携带 SQL 参数或敏感正文。
        logger.warning("audit_write_failed", error_type=type(exc).__name__)
