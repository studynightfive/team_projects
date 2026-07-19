# 系统概览服务层
# 员工3 负责
# 方案第9.3节：系统概览所需聚合接口

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.models import Role, User
from app.documents.models import Document
from app.knowledge.models import KnowledgeBase
from app.rag.conversations.all import Conversation, Message
from app.users.dashboard_schemas import DashboardMetrics


async def get_dashboard_metrics(db: AsyncSession) -> DashboardMetrics:
    """获取系统概览指标

    只聚合员工3 负责范围内的数据（用户、角色）。
    其他指标（知识库、文档、问答等）在对应模块就位后补充。
    """
    metrics = DashboardMetrics()

    # 用户统计
    result = await db.execute(
        select(
            func.count(User.id).label("total"),
            func.count().filter(User.status == "active").label("active"),
            func.count().filter(User.status == "disabled").label("disabled"),
        )
    )
    row = result.one()
    metrics.total_users = row.total or 0
    metrics.active_users = row.active or 0
    metrics.disabled_users = row.disabled or 0

    # 角色统计
    result = await db.execute(
        select(func.count(Role.id)).where(Role.status == "active")
    )
    metrics.total_roles = result.scalar() or 0

    result = await db.execute(select(func.count(KnowledgeBase.id)))
    metrics.total_knowledge_bases = result.scalar() or 0

    result = await db.execute(select(func.count(Document.id)))
    metrics.total_documents = result.scalar() or 0

    result = await db.execute(select(func.count(Conversation.id)))
    metrics.total_conversations = result.scalar() or 0

    result = await db.execute(
        select(func.count(Message.id)).where(Message.role == "user")
    )
    metrics.total_chats_today = result.scalar() or 0

    return metrics
