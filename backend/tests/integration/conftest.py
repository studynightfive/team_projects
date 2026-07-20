"""Postgres 端到端集成测试的会话 fixture。

未设置可用库或连不上时自动 skip，不阻断默认 CI 单元门禁。
环境变量：TEST_DATABASE_URL（优先）或沿用 DATABASE_URL。
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 触发全部 ORM 表注册
import app.common.models  # noqa: F401
import app.documents.models  # noqa: F401
import app.knowledge.models  # noqa: F401
import app.models.repository  # noqa: F401
import app.rag.search.repository  # noqa: F401
from app.common.database import Base


def _test_database_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_base",
        ),
    )


@pytest_asyncio.fixture
async def pg_session() -> AsyncIterator[AsyncSession]:
    url = _test_database_url()
    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    schema = f"rag_e2e_{uuid.uuid4().hex[:10]}"

    @event.listens_for(engine.sync_engine, "connect")
    def _set_search_path(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}", public')
        cursor.close()

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001 — 连库失败则跳过整组 E2E
        await engine.dispose()
        pytest.skip(f"Postgres 不可用，跳过端到端测试: {exc}")

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    await engine.dispose()
