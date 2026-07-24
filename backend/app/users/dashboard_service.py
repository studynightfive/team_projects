"""业务看板与用户激励聚合服务。"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone, tzinfo
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from app.common.config import settings
from app.common.exceptions import ForbiddenException, NotFoundException
from app.common.models import Role, User
from app.common.organization import is_super_admin
from app.common.schemas import PaginatedData
from app.departments.models import Department
from app.documents.models import Document, DocumentStatus
from app.knowledge.models import KnowledgeBase
from app.rag.conversations.all import Conversation, Message
from app.rag.metrics import RetrievalMetric
from app.users.dashboard_schemas import (
    ContributionItem,
    DashboardMetrics,
    DashboardPeriod,
    DashboardScope,
    DepartmentLeaderboardItem,
    IncentiveBadge,
    IncentiveRule,
    NextBadge,
    RateMetric,
    ResponseTimeMetric,
    UserIncentives,
)

POINTS_PER_READY_DOCUMENT = 10
BADGE_DEFINITIONS = (
    ("knowledge_starter", "知识新星", "完成第一份有效知识贡献", 10),
    ("knowledge_builder", "知识共建者", "持续建设可检索的知识内容", 50),
    ("knowledge_leader", "知识领航员", "成为部门知识建设的核心贡献者", 100),
)


def _rate(numerator: int, denominator: int) -> RateMetric:
    value = round(numerator / denominator * 100, 1) if denominator else 0.0
    return RateMetric(
        rate=value,
        numerator=numerator,
        denominator=denominator,
    )


def _business_timezone() -> tzinfo:
    try:
        return ZoneInfo(settings.business_timezone)
    except ZoneInfoNotFoundError:
        if settings.business_timezone == "Asia/Shanghai":
            return timezone(timedelta(hours=8))
        raise


async def _resolve_dashboard_scope(
    db: AsyncSession,
    *,
    user: User,
    requested_department_id: str | None,
) -> tuple[str | None, str]:
    if not is_super_admin(user):
        if user.department_id is None:
            raise ForbiddenException(message="当前管理员尚未归属部门")
        if (
            requested_department_id is not None
            and requested_department_id != user.department_id
        ):
            raise ForbiddenException(message="无权查看其他部门的业务数据")
        requested_department_id = user.department_id

    if requested_department_id is None:
        return None, "全部部门"

    department = await db.get(Department, requested_department_id)
    if department is None:
        raise NotFoundException(message="部门不存在")
    return department.id, department.name


def _document_contribution_subquery(
    *,
    department_id: str | None = None,
) -> Subquery:
    statement = (
        select(
            User.department_id.label("department_id"),
            User.id.label("user_id"),
            func.count(func.distinct(Document.content_hash)).label(
                "contribution_count"
            ),
        )
        .join(Document, Document.created_by == User.id)
        .where(
            User.status == "active",
            Document.status == DocumentStatus.READY.value,
            Document.is_active_index.is_(True),
        )
        .group_by(User.department_id, User.id)
    )
    if department_id is not None:
        statement = statement.where(User.department_id == department_id)
    return statement.subquery()


async def _department_leaderboard(
    db: AsyncSession,
    *,
    department_id: str | None,
    page: int,
    page_size: int,
) -> PaginatedData[DepartmentLeaderboardItem]:
    contributions = _document_contribution_subquery(
        department_id=department_id
    )
    contribution_count = func.coalesce(
        func.sum(contributions.c.contribution_count),
        0,
    )
    points = contribution_count * POINTS_PER_READY_DOCUMENT
    contributor_count = func.count(contributions.c.user_id)

    statement = (
        select(
            Department.id,
            Department.name,
            points.label("points"),
            contribution_count.label("contribution_count"),
            contributor_count.label("contributor_count"),
        )
        .outerjoin(
            contributions,
            contributions.c.department_id == Department.id,
        )
        .group_by(Department.id, Department.name)
        .order_by(
            points.desc(),
            contribution_count.desc(),
            Department.name.asc(),
        )
    )
    count_statement = select(func.count(Department.id))
    if department_id is not None:
        statement = statement.where(Department.id == department_id)
        count_statement = count_statement.where(Department.id == department_id)

    total = int((await db.execute(count_statement)).scalar_one() or 0)
    offset = (page - 1) * page_size
    rows = (await db.execute(statement.offset(offset).limit(page_size))).all()
    items = [
        DepartmentLeaderboardItem(
            rank=offset + index + 1,
            department_id=str(row[0]),
            department_name=str(row[1]),
            points=int(row[2] or 0),
            contribution_count=int(row[3] or 0),
            contributor_count=int(row[4] or 0),
        )
        for index, row in enumerate(rows)
    ]
    return PaginatedData(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


async def get_dashboard_metrics(
    db: AsyncSession,
    *,
    user: User,
    days: Literal[7, 30, 90],
    department_id: str | None,
    leaderboard_page: int,
    leaderboard_page_size: int,
) -> DashboardMetrics:
    """按服务端部门边界聚合真实业务指标。"""

    scope_department_id, scope_department_name = await _resolve_dashboard_scope(
        db,
        user=user,
        requested_department_id=department_id,
    )
    ended_at = datetime.now(timezone.utc)
    started_at = ended_at - timedelta(days=days)

    user_statement = select(
        func.count(User.id),
        func.count().filter(User.status == "active"),
        func.count().filter(User.status == "disabled"),
    )
    if scope_department_id is not None:
        user_statement = user_statement.where(
            User.department_id == scope_department_id
        )
    user_row = (await db.execute(user_statement)).one()

    total_roles = int(
        (
            await db.execute(
                select(func.count(Role.id)).where(Role.status == "active")
            )
        ).scalar_one()
        or 0
    )

    knowledge_statement = select(func.count(KnowledgeBase.id))
    if scope_department_id is not None:
        knowledge_statement = knowledge_statement.where(
            KnowledgeBase.department_id == scope_department_id
        )
    total_knowledge_bases = int(
        (await db.execute(knowledge_statement)).scalar_one() or 0
    )

    document_statement = (
        select(func.count(Document.id))
        .select_from(Document)
        .join(
            KnowledgeBase,
            KnowledgeBase.id == Document.knowledge_base_id,
        )
    )
    if scope_department_id is not None:
        document_statement = document_statement.where(
            KnowledgeBase.department_id == scope_department_id
        )
    total_documents = int(
        (await db.execute(document_statement)).scalar_one() or 0
    )

    conversation_statement = (
        select(func.count(Conversation.id))
        .select_from(Conversation)
        .join(User, User.id == Conversation.user_id)
    )
    if scope_department_id is not None:
        conversation_statement = conversation_statement.where(
            User.department_id == scope_department_id
        )
    total_conversations = int(
        (await db.execute(conversation_statement)).scalar_one() or 0
    )

    local_now = datetime.now(_business_timezone())
    day_start = datetime.combine(
        local_now.date(),
        time.min,
        tzinfo=local_now.tzinfo,
    ).astimezone(timezone.utc)
    chats_statement = (
        select(func.count(Message.id))
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .join(User, User.id == Conversation.user_id)
        .where(
            Message.role == "user",
            Message.created_at >= day_start,
        )
    )
    if scope_department_id is not None:
        chats_statement = chats_statement.where(
            User.department_id == scope_department_id
        )
    total_chats_today = int(
        (await db.execute(chats_statement)).scalar_one() or 0
    )

    coverage_total_statement = select(func.count(KnowledgeBase.id)).where(
        KnowledgeBase.status == "active",
        KnowledgeBase.kind == "enterprise",
    )
    coverage_ready_statement = (
        select(func.count(func.distinct(KnowledgeBase.id)))
        .select_from(KnowledgeBase)
        .join(Document, Document.knowledge_base_id == KnowledgeBase.id)
        .where(
            KnowledgeBase.status == "active",
            KnowledgeBase.kind == "enterprise",
            Document.status == DocumentStatus.READY.value,
            Document.is_active_index.is_(True),
        )
    )
    if scope_department_id is not None:
        coverage_total_statement = coverage_total_statement.where(
            KnowledgeBase.department_id == scope_department_id
        )
        coverage_ready_statement = coverage_ready_statement.where(
            KnowledgeBase.department_id == scope_department_id
        )
    coverage_total = int(
        (await db.execute(coverage_total_statement)).scalar_one() or 0
    )
    coverage_ready = int(
        (await db.execute(coverage_ready_statement)).scalar_one() or 0
    )

    processing_statement = (
        select(
            func.count(Document.id),
            func.count().filter(
                Document.status == DocumentStatus.READY.value
            ),
        )
        .select_from(Document)
        .join(
            KnowledgeBase,
            KnowledgeBase.id == Document.knowledge_base_id,
        )
        .where(
            Document.updated_at >= started_at,
            Document.updated_at <= ended_at,
            Document.status.in_(
                [
                    DocumentStatus.READY.value,
                    DocumentStatus.FAILED.value,
                ]
            ),
        )
    )
    if scope_department_id is not None:
        processing_statement = processing_statement.where(
            KnowledgeBase.department_id == scope_department_id
        )
    processing_row = (await db.execute(processing_statement)).one()
    processed_total = int(processing_row[0] or 0)
    processed_ready = int(processing_row[1] or 0)

    metric_statement = select(
        func.count(RetrievalMetric.id),
        func.count().filter(
            (RetrievalMetric.event_type == "answer")
            & (RetrievalMetric.hit_count > 0)
            & (
                RetrievalMetric.generated.is_(True)
                | RetrievalMetric.cache_hit.is_(True)
            )
        ),
        func.count().filter(
            (RetrievalMetric.event_type == "answer")
            & (RetrievalMetric.hit_count == 0)
            & RetrievalMetric.generated.is_(False)
            & RetrievalMetric.cache_hit.is_(False)
        ),
        func.count().filter(RetrievalMetric.event_type == "answer"),
        func.count().filter(
            (RetrievalMetric.event_type == "answer")
            & RetrievalMetric.cache_hit.is_(True)
        ),
        func.avg(RetrievalMetric.took_ms),
    ).where(
        RetrievalMetric.created_at >= started_at,
        RetrievalMetric.created_at <= ended_at,
    )
    if scope_department_id is not None:
        metric_statement = metric_statement.where(
            RetrievalMetric.department_id == scope_department_id
        )
    metric_row = (await db.execute(metric_statement)).one()
    active_searches = int(metric_row[0] or 0)
    effective_answers = int(metric_row[1] or 0)
    unanswered_queries = int(metric_row[2] or 0)
    answer_count = int(metric_row[3] or 0)
    cache_hits = int(metric_row[4] or 0)
    average_response_ms = round(float(metric_row[5] or 0.0), 1)

    document_processing = _rate(processed_ready, processed_total)
    return DashboardMetrics(
        total_users=int(user_row[0] or 0),
        active_users=int(user_row[1] or 0),
        disabled_users=int(user_row[2] or 0),
        total_roles=total_roles,
        total_knowledge_bases=total_knowledge_bases,
        total_documents=total_documents,
        total_conversations=total_conversations,
        total_chats_today=total_chats_today,
        success_rate=document_processing.rate,
        avg_response_time_ms=average_response_ms,
        period=DashboardPeriod(
            days=days,
            started_at=started_at,
            ended_at=ended_at,
        ),
        scope=DashboardScope(
            department_id=scope_department_id,
            department_name=scope_department_name,
        ),
        knowledge_coverage=_rate(coverage_ready, coverage_total),
        active_searches=active_searches,
        effective_answers=effective_answers,
        unanswered_queries=unanswered_queries,
        document_processing=document_processing,
        answer_cache=_rate(cache_hits, answer_count),
        response_time=ResponseTimeMetric(
            average_ms=average_response_ms,
            sample_count=active_searches,
        ),
        department_leaderboard=await _department_leaderboard(
            db,
            department_id=scope_department_id,
            page=leaderboard_page,
            page_size=leaderboard_page_size,
        ),
    )


def _badges(points: int) -> list[IncentiveBadge]:
    return [
        IncentiveBadge(
            code=code,
            name=name,
            description=description,
            threshold=threshold,
            earned=points >= threshold,
        )
        for code, name, description, threshold in BADGE_DEFINITIONS
    ]


def _next_badge(points: int) -> NextBadge | None:
    for code, name, _description, threshold in BADGE_DEFINITIONS:
        if points < threshold:
            return NextBadge(
                code=code,
                name=name,
                threshold=threshold,
                remaining_points=threshold - points,
            )
    return None


async def get_user_incentives(
    db: AsyncSession,
    *,
    user: User,
    page: int,
    page_size: int,
) -> UserIncentives:
    """返回当前用户的去重贡献，不暴露部门内其他用户详情。"""

    ranked_documents = (
        select(
            Document.id.label("id"),
            Document.title.label("title"),
            Document.created_at.label("occurred_at"),
            func.row_number()
            .over(
                partition_by=Document.content_hash,
                order_by=(Document.created_at.asc(), Document.id.asc()),
            )
            .label("content_rank"),
        )
        .where(
            Document.created_by == user.id,
            Document.status == DocumentStatus.READY.value,
            Document.is_active_index.is_(True),
        )
        .subquery()
    )
    contribution_statement = select(
        ranked_documents.c.id,
        ranked_documents.c.title,
        ranked_documents.c.occurred_at,
    ).where(ranked_documents.c.content_rank == 1)
    total = int(
        (
            await db.execute(
                select(func.count()).select_from(
                    contribution_statement.subquery()
                )
            )
        ).scalar_one()
        or 0
    )
    rows = (
        await db.execute(
            contribution_statement.order_by(
                ranked_documents.c.occurred_at.desc(),
                ranked_documents.c.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    points = total * POINTS_PER_READY_DOCUMENT

    department_rank: int | None = None
    department_member_count = 0
    if user.department_id is not None:
        contributions = _document_contribution_subquery(
            department_id=user.department_id
        )
        member_rows = (
            await db.execute(
                select(
                    User.id,
                    func.coalesce(
                        contributions.c.contribution_count,
                        0,
                    ).label("contribution_count"),
                    User.display_name,
                )
                .outerjoin(
                    contributions,
                    contributions.c.user_id == User.id,
                )
                .where(
                    User.department_id == user.department_id,
                    User.status == "active",
                )
                .order_by(
                    func.coalesce(
                        contributions.c.contribution_count,
                        0,
                    ).desc(),
                    User.display_name.asc(),
                    User.id.asc(),
                )
            )
        ).all()
        department_member_count = len(member_rows)
        own_contribution_count = next(
            (
                int(member_row[1] or 0)
                for member_row in member_rows
                if member_row[0] == user.id
            ),
            None,
        )
        if own_contribution_count is not None:
            department_rank = 1 + sum(
                1
                for member_row in member_rows
                if int(member_row[1] or 0) > own_contribution_count
            )

    contributions_page = PaginatedData(
        items=[
            ContributionItem(
                id=str(row[0]),
                type="ready_document",
                title=str(row[1]),
                points=POINTS_PER_READY_DOCUMENT,
                occurred_at=row[2],
            )
            for row in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )
    return UserIncentives(
        points=points,
        contribution_count=total,
        department_rank=department_rank,
        department_member_count=department_member_count,
        badges=_badges(points),
        next_badge=_next_badge(points),
        rules=[
            IncentiveRule(
                code="ready_unique_document",
                name="有效文档贡献",
                description="成功处理并启用索引的不同内容文档，每份只计一次",
                points=POINTS_PER_READY_DOCUMENT,
            )
        ],
        contributions=contributions_page,
    )
