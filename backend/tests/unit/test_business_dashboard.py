"""业务看板口径与指标写入单元测试。"""

from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.models import User
from app.rag.metrics import RetrievalMetric, record_retrieval_metric
from app.users.dashboard_service import _badges, _next_badge, _rate


def _user() -> User:
    user = User(
        id="user-business-dashboard",
        username="business-dashboard",
        display_name="业务看板用户",
        password_hash="test",
        department_id="department-medical",
        status="active",
    )
    user.roles = []
    return user


def test_rate_handles_empty_denominator_without_inventing_success() -> None:
    assert _rate(0, 0).rate == 0.0
    assert _rate(2, 3).rate == 66.7


def test_badges_and_next_badge_follow_real_points() -> None:
    badges = _badges(50)
    assert [item.earned for item in badges] == [True, True, False]
    next_badge = _next_badge(50)
    assert next_badge is not None
    assert next_badge.code == "knowledge_leader"
    assert next_badge.name == "知识领航员"
    assert next_badge.threshold == 100
    assert next_badge.remaining_points == 50
    assert _next_badge(100) is None


async def test_record_retrieval_metric_only_persists_structured_facts() -> None:
    db = MagicMock(spec=AsyncSession)
    db.flush = AsyncMock()

    await record_retrieval_metric(
        db,
        user=_user(),
        event_type="answer",
        request_id="request-1",
        knowledge_base_id="kb-medical",
        hit_count=2,
        generated=True,
        cache_hit=False,
        took_ms=321,
    )

    metric = db.add.call_args.args[0]
    assert isinstance(metric, RetrievalMetric)
    assert metric.user_id == "user-business-dashboard"
    assert metric.department_id == "department-medical"
    assert metric.hit_count == 2
    assert metric.generated is True
    assert metric.cache_hit is False
    assert metric.took_ms == 321
    assert not hasattr(metric, "query")
    assert not hasattr(metric, "answer")


async def test_duplicate_metric_does_not_break_user_request() -> None:
    db = MagicMock(spec=AsyncSession)
    db.flush = AsyncMock(
        side_effect=IntegrityError("duplicate", {}, Exception("duplicate"))
    )

    await record_retrieval_metric(
        db,
        user=_user(),
        event_type="search",
        request_id="request-duplicate",
        knowledge_base_id=None,
        hit_count=0,
        generated=False,
        cache_hit=False,
        took_ms=0,
    )

    db.flush.assert_awaited_once()
