"""真实通知中心接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.common.database import get_db
from app.common.exceptions import ForbiddenException, NotFoundException
from app.common.models import User
from app.common.schemas import APIResponse
from app.notifications.models import Notification
from app.notifications.schemas import (
    NotificationAction,
    NotificationAudience,
    NotificationListResponse,
    NotificationResponse,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
NOTIFICATION_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "knowledge-base-platform-notifications")


def _has_admin_permission(user: User) -> bool:
    for role in user.roles:
        if role.status != "active":
            continue
        for permission in role.permissions:
            if permission.code.startswith("admin."):
                return True
    return False


def _serialize(item: Notification) -> NotificationResponse:
    action = None
    if item.action_label and item.action_to:
        action = NotificationAction(label=item.action_label, to=item.action_to)
    return NotificationResponse(
        id=item.id,
        audience=item.audience,  # type: ignore[arg-type]
        category=item.category,  # type: ignore[arg-type]
        title=item.title,
        description=item.description,
        read=item.is_read,
        created_at=item.created_at,
        action=action,
    )


async def _ensure_default_notifications(
    db: AsyncSession,
    *,
    user: User,
    audience: NotificationAudience,
) -> None:
    if audience == "admin":
        if not _has_admin_permission(user):
            raise ForbiddenException(message="无权查看管理通知")
        rows = [
            _seed_row(
                "admin",
                None,
                "task-watch",
                "任务",
                "文档处理任务需要关注",
                "请在任务中心查看最近的文档处理状态和失败原因。",
                "查看任务",
                "/admin/tasks",
            ),
            _seed_row(
                "admin",
                None,
                "model-real-api",
                "系统",
                "模型配置已接入真实后端",
                "DeepSeek 聊天模型已可在模型管理中维护，密钥不会回显。",
                "查看模型",
                "/admin/models",
            ),
            _seed_row(
                "admin",
                None,
                "kb-permission-boundary",
                "知识",
                "知识库权限由管理中心维护",
                "普通用户只能浏览可访问知识库，创建知识库已收敛到管理中心。",
                "查看知识库",
                "/admin/knowledge-bases",
            ),
            _seed_row(
                "admin",
                None,
                "demo-account-permissions",
                "安全",
                "演示账号已完成权限区分",
                "管理员、普通用户和知识库编辑者账号已按角色返回真实权限码。",
                "查看用户",
                "/admin/users",
            ),
        ]
    else:
        rows = [
            _seed_row(
                "user",
                user.id,
                "kb-real-api",
                "知识",
                "企业知识库已切换真实接口",
                "知识库列表会按当前账号权限读取真实后端数据。",
                "查看知识库",
                "/knowledge",
            ),
            _seed_row(
                "user",
                user.id,
                "document-pipeline",
                "任务",
                "文档上传后会自动处理",
                "上传文档会转成 Markdown 并切块，处理完成后可用于 RAG 问答。",
                "开始检索",
                "/",
            ),
            _seed_row(
                "user",
                user.id,
                "profile-real-api",
                "安全",
                "账号资料来自统一认证",
                "个人资料会从登录态和 /api/v1/me 读取，不再使用固定演示身份。",
                "查看偏好",
                "/preferences",
            ),
        ]
    for row in rows:
        await db.execute(insert(Notification).values(**row).on_conflict_do_nothing())
    await db.commit()


def _seed_row(
    audience: str,
    user_id: str | None,
    key: str,
    category: str,
    title: str,
    description: str,
    action_label: str,
    action_to: str,
) -> dict[str, object]:
    owner = user_id or "global"
    return {
        "id": str(uuid.uuid5(NOTIFICATION_NAMESPACE, f"{audience}:{owner}:{key}")),
        "audience": audience,
        "user_id": user_id,
        "category": category,
        "title": title,
        "description": description,
        "action_label": action_label,
        "action_to": action_to,
        "is_read": False,
    }


def _base_query(audience: NotificationAudience, user: User):
    if audience == "admin":
        return select(Notification).where(
            Notification.audience == "admin",
            Notification.user_id.is_(None),
        )
    return select(Notification).where(
        Notification.audience == "user",
        Notification.user_id == user.id,
    )


@router.get("")
async def list_notifications_endpoint(
    audience: NotificationAudience = Query("user"),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_default_notifications(db, user=user, audience=audience)
    base = _base_query(audience, user)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    unread = (
        await db.execute(
            select(func.count()).select_from(
                base.where(Notification.is_read.is_(False)).subquery()
            )
        )
    ).scalar() or 0
    result = await db.execute(
        base.order_by(Notification.created_at.desc()).limit(page_size)
    )
    items = [_serialize(item).model_dump() for item in result.scalars()]
    return APIResponse(
        data=NotificationListResponse(items=items, total=total, unread=unread).model_dump(),
        request_id=str(uuid.uuid4()),
    ).model_dump()


@router.patch("/{notification_id}/read")
async def mark_notification_read_endpoint(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notification = await db.get(Notification, notification_id)
    if notification is None:
        raise NotFoundException(message="通知不存在")
    if notification.audience == "admin":
        if notification.user_id is not None or not _has_admin_permission(user):
            raise ForbiddenException(message="无权操作此通知")
    elif notification.user_id != user.id:
        raise ForbiddenException(message="无权操作此通知")
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return APIResponse(
        data=_serialize(notification).model_dump(),
        request_id=str(uuid.uuid4()),
    ).model_dump()


@router.post("/mark-all-read")
async def mark_all_notifications_read_endpoint(
    audience: NotificationAudience = Query("user"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_default_notifications(db, user=user, audience=audience)
    result = await db.execute(_base_query(audience, user))
    for notification in result.scalars():
        notification.is_read = True
    await db.commit()
    return APIResponse(request_id=str(uuid.uuid4())).model_dump()
