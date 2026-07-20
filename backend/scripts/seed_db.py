"""仅用于隔离演示环境的数据播种脚本。"""
import asyncio

from app.common.database import async_session_factory
from app.common.seed import (
    seed_builtin_authorization,
    seed_default_knowledge_base,
    seed_demo_accounts,
)


async def seed() -> None:
    async with async_session_factory() as db:
        await seed_builtin_authorization(db)
        await seed_demo_accounts(db)
        await seed_default_knowledge_base(db)
        print("演示数据播种完成")


if __name__ == "__main__":
    asyncio.run(seed())
