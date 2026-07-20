"""审计上下文与事务隔离的聚焦回归测试。"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.audit.service import write_audit_log
from app.common.database import async_session_factory
from app.main import request_id_middleware
from app.rag._shared import audit_helper


def _request_with_headers(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": "/test",
            "raw_path": b"/test",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "supplied_request_id",
    [str(uuid.uuid4()).upper(), "x" * 1000],
)
async def test_request_id_middleware_stores_normalized_uuid(
    supplied_request_id: str,
) -> None:
    request = _request_with_headers(
        [(b"x-request-id", supplied_request_id.encode("ascii"))]
    )

    async def call_next(received_request: Request) -> Response:
        request_id = received_request.state.request_id
        assert str(uuid.UUID(request_id)) == request_id
        return Response()

    response = await request_id_middleware(request, call_next)

    assert response.headers["X-Request-ID"] == request.state.request_id
    assert len(request.state.request_id) == 36


def test_request_context_caps_headers_and_uses_normalized_state() -> None:
    request = _request_with_headers(
        [
            (b"user-agent", b"u" * 800),
            (b"x-request-id", b"untrusted-header-value"),
        ]
    )
    request.scope["client"] = ("i" * 80, 12345)
    request.state.request_id = str(uuid.uuid4())

    context = audit_helper._extract_request_ctx(request)

    assert context["ip_address"] == "i" * 45
    assert context["user_agent"] == "u" * 500
    assert context["request_id"] == request.state.request_id


@pytest.mark.asyncio
async def test_write_audit_log_normalizes_bounded_fields_and_flushes() -> None:
    db = MagicMock(spec=AsyncSession)
    db.flush = AsyncMock()

    await write_audit_log(
        db,
        action="\r\n" + "a" * 120,
        resource_type="\x00" + "t" * 120,
        resource_id="r" * 80,
        ip_address="i" * 80,
        user_agent="u" * 800,
        result="s" * 40,
        request_id="q" * 80,
    )

    entry = db.add.call_args.args[0]
    assert entry.action == "a" * 100
    assert entry.resource_type == "t" * 100
    assert entry.resource_id == "r" * 36
    assert entry.ip_address == "i" * 45
    assert entry.user_agent == "u" * 500
    assert entry.result == "s" * 20
    assert entry.request_id == "q" * 36
    db.flush.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_audit_failure_does_not_poison_outer_transaction(monkeypatch) -> None:
    async def fail_inside_savepoint(
        db: AsyncSession,
        **_kwargs: object,
    ) -> None:
        await db.execute(text("SELECT 1 / 0"))

    monkeypatch.setattr(audit_helper, "write_audit_log", fail_inside_savepoint)

    async with async_session_factory() as db:
        async with db.begin():
            await audit_helper.audit(db, action="transaction_isolation_test")
            assert (await db.execute(text("SELECT 1"))).scalar_one() == 1
