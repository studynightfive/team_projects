"""临时种子数据脚本"""
import asyncio

from app.common.database import async_session_factory
from app.common.seed import (
    seed_default_admin,
    seed_default_knowledge_base,
    seed_demo_accounts,
    seed_permissions,
)


async def seed():
    async with async_session_factory() as db:
        await seed_permissions(db)
        await seed_default_admin(db)
        await seed_demo_accounts(db)
        await seed_default_knowledge_base(db)
        print("种子数据创建完成")


if __name__ == "__main__":
    asyncio.run(seed())
