"""业务看板查询参数契约测试。"""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.common.database import get_db
from app.common.schemas import PaginatedData
from app.main import app
from app.users import dashboard_router
from app.users.dashboard_schemas import UserIncentives


@pytest.fixture
async def dashboard_client(monkeypatch: pytest.MonkeyPatch):
    async def fake_user() -> SimpleNamespace:
        return SimpleNamespace(id="dashboard-user", department_id=None)

    async def fake_db():
        yield object()

    async def fake_incentives(
        _db: object,
        *,
        user: SimpleNamespace,
        page: int,
        page_size: int,
    ) -> UserIncentives:
        assert user.id == "dashboard-user"
        return UserIncentives(
            points=0,
            contribution_count=0,
            department_rank=None,
            department_member_count=0,
            badges=[],
            next_badge=None,
            rules=[],
            contributions=PaginatedData(
                items=[],
                page=page,
                page_size=page_size,
                total=0,
            ),
        )

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_db] = fake_db
    monkeypatch.setattr(
        dashboard_router,
        "get_user_incentives",
        fake_incentives,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def test_incentive_page_size_parses_from_query_string(
    dashboard_client: AsyncClient,
) -> None:
    response = await dashboard_client.get(
        "/api/v1/me/incentives?page=1&page_size=10"
    )

    assert response.status_code == 200
    assert response.json()["data"]["contributions"]["page_size"] == 10


async def test_incentive_page_size_rejects_unsupported_value(
    dashboard_client: AsyncClient,
) -> None:
    response = await dashboard_client.get(
        "/api/v1/me/incentives?page=1&page_size=15"
    )

    assert response.status_code == 422
