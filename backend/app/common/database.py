# 数据库连接模块
# 使用 SQLAlchemy 2.0 异步引擎
# 采用异步会话管理，支持 PostgreSQL + pgvector

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.common.config import settings

# ============================================================
# 数据库引擎：异步 PostgreSQL 连接
# ============================================================
# 创建异步数据库引擎
# echo=False 表示不输出 SQL 日志（生产环境）
# echo=True 仅在开发调试时使用
if settings.testing:
    # pytest 的测试事件循环彼此隔离，复用池连接会把 asyncpg Future 绑定到旧循环。
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,  # 仅在 debug 模式下输出 SQL 日志
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

# ============================================================
# 异步会话工厂
# ============================================================
# 创建异步会话工厂
# expire_on_commit=False 防止提交后访问属性时触发额外查询
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============================================================
# 声明式基类：所有 ORM 模型继承此类
# ============================================================
class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类
    所有数据库表模型继承此类
    """
    pass


# ============================================================
# 数据库会话依赖注入
# ============================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入函数
    在请求处理期间提供数据库会话
    请求结束后自动关闭会话
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
