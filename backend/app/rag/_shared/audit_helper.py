"""审计写入包装（员工5 跨模块统一封装）"""
from __future__ import annotations

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import write_audit_log

logger = structlog.get_logger()


def _extract_request_ctx(request: Request | None) -> dict:
    if request is None:
        return {}
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": request.headers.get("x-request-id"),
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
        await write_audit_log(
            db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            result=result,
            **ctx,
        )
    except Exception as exc:
        logger.warning("audit_write_failed", action=action, error=str(exc))