"""交互式创建首个管理员，仅限尚无管理员的环境。"""

import asyncio
import sys
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.database import async_session_factory
from app.common.exceptions import AppException
from app.common.models import Role, User
from app.common.seed import SUPER_ADMIN_ROLE_NAME, seed_builtin_authorization
from app.users.schemas import CreateUserRequest
from app.users.service import create_user


async def _admin_exists(db: AsyncSession, role_id: str) -> bool:
    result = await db.execute(
        select(User.id)
        .join(User.roles)
        .where(Role.id == role_id)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _prepare_bootstrap(db: AsyncSession) -> Role:
    roles = await seed_builtin_authorization(db)
    role = roles[SUPER_ADMIN_ROLE_NAME]
    if await _admin_exists(db, role.id):
        raise RuntimeError("已存在管理员，拒绝再次执行首管理员初始化")
    return role


async def bootstrap_admin() -> bool:
    async with async_session_factory() as db:
        try:
            role = await _prepare_bootstrap(db)
        except RuntimeError as exc:
            print(f"未创建管理员：{exc}", file=sys.stderr)
            return False
        except Exception as exc:
            print(f"未创建管理员（{type(exc).__name__}）", file=sys.stderr)
            return False

        username = input("管理员账号：").strip()
        display_name = input("显示名称（默认同账号）：").strip() or username
        password = getpass("管理员口令（至少 12 位）：")
        confirmation = getpass("再次输入口令：")

        if not 1 <= len(username) <= 150:
            print("未创建管理员：账号长度必须为 1–150 位", file=sys.stderr)
            return False
        if not 1 <= len(display_name) <= 150:
            print("未创建管理员：显示名称长度必须为 1–150 位", file=sys.stderr)
            return False
        if not 12 <= len(password) <= 128:
            print("未创建管理员：口令长度必须为 12–128 位", file=sys.stderr)
            return False
        if password != confirmation:
            print("未创建管理员：两次口令不一致", file=sys.stderr)
            return False
        if await _admin_exists(db, role.id):
            print("未创建管理员：已存在管理员", file=sys.stderr)
            return False

        try:
            user = await create_user(
                db,
                CreateUserRequest(
                    username=username,
                    display_name=display_name,
                    password=password,
                    role_ids=[role.id],
                ),
            )
        except AppException as exc:
            print(f"未创建管理员：{exc.message}", file=sys.stderr)
            return False
        except Exception as exc:
            print(f"未创建管理员（{type(exc).__name__}）", file=sys.stderr)
            return False

    print(f"首管理员 {user.username} 创建完成")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(bootstrap_admin()) else 1)
