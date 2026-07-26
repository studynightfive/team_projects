"""SSE 流生命周期专用数据库会话。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.database import async_session_factory
from app.common.exceptions import UnauthorizedException
from app.common.models import User


@asynccontextmanager
async def stream_user_session(
    user_id: str,
) -> AsyncIterator[tuple[AsyncSession, User]]:
    """让数据库会话覆盖完整 SSE 生成周期。

    FastAPI 路由返回 ``StreamingResponse`` 后，请求级 yield 依赖可能已经退出。
    因此不能把普通请求会话传入延迟执行的流式生成器。
    """

    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None or user.status != "active":
            raise UnauthorizedException(message="登录状态已失效，请重新登录")
        try:
            yield session, user
        except BaseException:
            await session.rollback()
            raise
