# Alembic 迁移环境配置
# 用于管理 PostgreSQL 数据库 schema 变更
# 方案第9.3节：员工3 负责数据库迁移

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config 对象
config = context.config

# 设置日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 从应用配置中获取数据库 URL
from app.common.config import settings  # noqa: E402

config.set_main_option("sqlalchemy.url", settings.database_url)

from app.common.database import Base  # noqa: E402
from app.common.model_registry import load_all_models  # noqa: E402

# Alembic 只会比较已注册到 Base.metadata 的模型；必须显式加载全部业务模块。
load_all_models()

target_metadata = Base.metadata

_MIGRATION_MANAGED_INDEXES = frozenset(
    {
        "ix_chunks_tsv",
        "ix_chunks_metadata",
        "ix_chunks_embedding",
        "uq_knowledge_bases_name_normalized",
        "ix_document_chunks_embedding_vector",
    }
)


def include_object(
    _object: object,
    _name: str | None,
    object_type: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """仅忽略由手写迁移管理且无法完整映射到 ORM 的特殊索引。"""
    return not (
        object_type == "index"
        and reflected
        and compare_to is None
        and _name in _MIGRATION_MANAGED_INDEXES
    )


def run_migrations_offline() -> None:
    """
    离线迁移模式：生成 SQL 脚本，不连接数据库
    用于评审迁移脚本或在无数据库连接的环境中生成迁移
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """执行迁移"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """异步迁移模式：连接数据库并执行迁移"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在线迁移模式：连接数据库并执行迁移"""
    asyncio.run(run_async_migrations())


# 根据迁移模式选择执行方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
