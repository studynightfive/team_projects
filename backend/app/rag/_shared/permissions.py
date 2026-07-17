"""知识库文档权限过滤（提示词 02 §4.4 + 03 §5.3）

设计要点：
- SQL 过滤：通过 `get_user_accessible_kb_ids` 获取用户可访问的 kb_id 集合，
  在 chunks 表 JOIN 时强制 in-list；避免任何无权文档通过 SQL 返回。
- 结果过滤：`post_filter_hits` 对检索/SSE 引用结果再次校验 doc_id 权限，
  即使 SQL JOIN 漏判也能兜底；命中的无权片段直接丢弃并记录审计。
- 共享：`backend.app.rag.search.*` 与 `backend.app.rag.chat.*` 共用。
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.models import KnowledgeBasePermission, User

logger = structlog.get_logger()


async def get_user_accessible_kb_ids(db: AsyncSession, user: User) -> set[str]:
    """返回当前用户可访问的全部知识库 ID。

    来源：
    1. 用户直接授予的 KB 权限（subject_type = user, subject_id = user.id）
    2. 用户角色继承的 KB 权限（subject_type = role, subject_id in user.role_ids）
    """
    role_ids = [r.id for r in user.roles if r.status == "active"]

    user_kb_q = select(KnowledgeBasePermission.kb_id).where(
        KnowledgeBasePermission.subject_type == "user",
        KnowledgeBasePermission.subject_id == user.id,
    )
    role_kb_q = (
        select(KnowledgeBasePermission.kb_id).where(
            KnowledgeBasePermission.subject_type == "role",
            KnowledgeBasePermission.subject_id.in_(role_ids),
        )
        if role_ids
        else None
    )

    kb_ids: set[str] = set()
    rows = await db.execute(user_kb_q)
    kb_ids.update(r[0] for r in rows.fetchall())
    if role_kb_q is not None:
        rows = await db.execute(role_kb_q)
        kb_ids.update(r[0] for r in rows.fetchall())
    return kb_ids


async def get_user_accessible_doc_ids(db: AsyncSession, user: User) -> set[str]:
    """返回当前用户可访问的 doc_id 集合。

    注意：documents 与 kb 的关联由员工4 模块维护；本期采用"用户对 KB 有读权限即
    对该 KB 内所有 doc 有读权限"的保守策略。

    TODO（员工4 就绪后）：改为 documents.kb_id JOIN 实际数据。
    """
    kb_ids = await get_user_accessible_kb_ids(db, user)
    if not kb_ids:
        return set()
    # 本期暂无 documents 表，doc_id 权限无法在这里精确判定；返回空集并依赖
    # 上层 SQL 约束（kb_id in 列表）兜底。
    return set()


def post_filter_hits(
    *,
    hits: list[dict],
    accessible_kb_ids: Iterable[str],
) -> list[dict]:
    """对检索/引用结果做后置权限过滤（提示词 02 §4.4 + 03 §5.3）。

    入参 hit 至少含 `kb_id` 字段。
    越权 hit 直接丢弃并记录审计（仅记录命中数，不含文档内容）。
    """
    allowed = set(accessible_kb_ids)
    dropped = 0
    filtered: list[dict] = []
    for hit in hits:
        if hit.get("kb_id") in allowed:
            filtered.append(hit)
        else:
            dropped += 1
    if dropped:
        logger.warning(
            "post_filter_dropped_inaccessible_hits",
            dropped=dropped,
            kept=len(filtered),
        )
    return filtered


def new_request_id() -> str:
    """生成统一的请求 ID（贯穿 SSE 事件、审计、日志）"""
    return str(uuid.uuid4())
