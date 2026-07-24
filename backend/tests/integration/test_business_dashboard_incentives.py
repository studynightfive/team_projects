"""业务看板和用户激励的真实 PostgreSQL 聚合测试。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.common.models import User
from app.departments.models import Department
from app.documents.models import Document, DocumentStatus
from app.knowledge.models import KnowledgeBase
from app.rag.metrics import RetrievalMetric, record_retrieval_metric
from app.users.dashboard_service import (
    get_dashboard_metrics,
    get_user_incentives,
)


def _id() -> str:
    return str(uuid.uuid4())


def _document(
    *,
    knowledge_base_id: str,
    created_by: str,
    content_hash: str,
    title: str,
    version: int = 1,
) -> Document:
    return Document(
        id=_id(),
        knowledge_base_id=knowledge_base_id,
        title=title,
        original_filename=f"{title}.md",
        stored_filename=f"{_id()}.md",
        extension=".md",
        mime_type="text/markdown",
        size_bytes=128,
        content_hash=content_hash,
        version=version,
        status=DocumentStatus.READY.value,
        is_active_index=True,
        created_by=created_by,
    )


async def test_dashboard_scope_and_incentive_deduplication(
    pg_session: AsyncSession,
) -> None:
    department = Department(id=_id(), name="医疗信息部")
    other_department = Department(id=_id(), name="教育信息部")
    pg_session.add_all([department, other_department])
    await pg_session.flush()

    user = User(
        id=_id(),
        username=f"medical-{_id()}",
        display_name="甲用户",
        password_hash=hash_password("test-password"),
        department_id=department.id,
        status="active",
    )
    colleague = User(
        id=_id(),
        username=f"medical-colleague-{_id()}",
        display_name="乙用户",
        password_hash=hash_password("test-password"),
        department_id=department.id,
        status="active",
    )
    other_user = User(
        id=_id(),
        username=f"education-{_id()}",
        display_name="教育用户",
        password_hash=hash_password("test-password"),
        department_id=other_department.id,
        status="active",
    )
    user.roles = []
    colleague.roles = []
    other_user.roles = []
    pg_session.add_all([user, colleague, other_user])
    await pg_session.flush()

    knowledge_base = KnowledgeBase(
        id=_id(),
        name="医疗制度库",
        department_id=department.id,
        kind="enterprise",
        status="active",
    )
    other_knowledge_base = KnowledgeBase(
        id=_id(),
        name="教育制度库",
        department_id=other_department.id,
        kind="enterprise",
        status="active",
    )
    pg_session.add_all([knowledge_base, other_knowledge_base])
    await pg_session.flush()

    duplicated_hash = "a" * 64
    pg_session.add_all(
        [
            _document(
                knowledge_base_id=knowledge_base.id,
                created_by=user.id,
                content_hash=duplicated_hash,
                title="医疗数据标准",
            ),
            _document(
                knowledge_base_id=knowledge_base.id,
                created_by=user.id,
                content_hash=duplicated_hash,
                title="医疗数据标准副本",
                version=2,
            ),
            _document(
                knowledge_base_id=knowledge_base.id,
                created_by=colleague.id,
                content_hash="b" * 64,
                title="电子病历规范",
            ),
            _document(
                knowledge_base_id=other_knowledge_base.id,
                created_by=other_user.id,
                content_hash="c" * 64,
                title="教学管理规范",
            ),
        ]
    )
    pg_session.add_all(
        [
            RetrievalMetric(
                id=_id(),
                user_id=user.id,
                department_id=department.id,
                knowledge_base_id=knowledge_base.id,
                event_type="search",
                hit_count=2,
                generated=False,
                cache_hit=False,
                took_ms=100,
                request_id=_id(),
            ),
            RetrievalMetric(
                id=_id(),
                user_id=user.id,
                department_id=department.id,
                knowledge_base_id=knowledge_base.id,
                event_type="answer",
                hit_count=2,
                generated=True,
                cache_hit=False,
                took_ms=900,
                request_id=_id(),
            ),
            RetrievalMetric(
                id=_id(),
                user_id=user.id,
                department_id=department.id,
                knowledge_base_id=knowledge_base.id,
                event_type="answer",
                hit_count=2,
                generated=False,
                cache_hit=True,
                took_ms=50,
                request_id=_id(),
            ),
            RetrievalMetric(
                id=_id(),
                user_id=user.id,
                department_id=department.id,
                knowledge_base_id=knowledge_base.id,
                event_type="answer",
                hit_count=0,
                generated=False,
                cache_hit=False,
                took_ms=120,
                request_id=_id(),
            ),
            RetrievalMetric(
                id=_id(),
                user_id=other_user.id,
                department_id=other_department.id,
                knowledge_base_id=other_knowledge_base.id,
                event_type="answer",
                hit_count=3,
                generated=True,
                cache_hit=False,
                took_ms=700,
                request_id=_id(),
            ),
        ]
    )
    await pg_session.commit()

    replay_request_id = _id()
    for _ in range(2):
        await record_retrieval_metric(
            pg_session,
            user=user,
            event_type="search",
            request_id=replay_request_id,
            knowledge_base_id=knowledge_base.id,
            hit_count=1,
            generated=False,
            cache_hit=False,
            took_ms=80,
        )
    await pg_session.commit()
    replay_count = (
        await pg_session.execute(
            select(func.count(RetrievalMetric.id)).where(
                RetrievalMetric.request_id == replay_request_id
            )
        )
    ).scalar_one()
    assert replay_count == 1

    dashboard = await get_dashboard_metrics(
        pg_session,
        user=user,
        days=30,
        department_id=department.id,
        leaderboard_page=1,
        leaderboard_page_size=10,
    )
    assert dashboard.scope.department_id == department.id
    assert dashboard.knowledge_coverage.rate == 100.0
    assert dashboard.active_searches == 5
    assert dashboard.effective_answers == 2
    assert dashboard.unanswered_queries == 1
    assert dashboard.answer_cache.rate == 33.3
    assert dashboard.department_leaderboard.total == 1
    assert dashboard.department_leaderboard.items[0].points == 20
    assert dashboard.department_leaderboard.items[0].contribution_count == 2

    incentives = await get_user_incentives(
        pg_session,
        user=user,
        page=1,
        page_size=10,
    )
    assert incentives.points == 10
    assert incentives.contribution_count == 1
    assert incentives.department_rank == 1
    assert incentives.department_member_count == 2
    assert len(incentives.contributions.items) == 1
    assert incentives.badges[0].earned is True
