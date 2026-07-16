# 审计服务层
# 员工3 负责
# 审计日志写入和查询
# 方案第15.5节：不记录 Secret 和敏感正文

from __future__ import annotations

from datetime import datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.schemas import AuditLogResponse
from app.common.models import AuditLog, User

logger = structlog.get_logger()


async def write_audit_log(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    result: str = "success",
    request_id: str | None = None,
) -> None:
    """写入审计日志

    不在审计日志中记录：
    - 密码、密钥、Token
    - 完整请求体
    - 内部路径或 SQL
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
        user_agent=user_agent,
        result=result,
        request_id=request_id,
    )
    db.add(entry)
    # 不在此处 commit，由调用方控制事务


async def list_audit_logs(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    user_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    result: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> tuple[list[AuditLogResponse], int]:
    """分页查询审计日志"""
    query = select(AuditLog)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    if result:
        query = query.where(AuditLog.result == result)
    if created_after:
        query = query.where(AuditLog.created_at >= created_after)
    if created_before:
        query = query.where(AuditLog.created_at <= created_before)

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    result_obj = await db.execute(count_query)
    total = result_obj.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    result_obj = await db.execute(
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result_obj.scalars().all()

    # 批量获取用户名
    user_ids = {log.user_id for log in logs if log.user_id}
    usernames: dict[str, str] = {}
    if user_ids:
        result_obj = await db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        usernames = {row[0]: row[1] for row in result_obj.fetchall()}

    items = [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            username=usernames.get(log.user_id) if log.user_id else None,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            detail=log.detail,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            result=log.result,
            request_id=log.request_id,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return items, total
