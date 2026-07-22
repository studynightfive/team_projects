# 认证服务层
# 员工3 负责
# 登录、退出、刷新、个人信息、会话管理

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import KnowledgeBaseAccessData, LoginData, MeData, UserRoleData
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.common.config import settings
from app.common.exceptions import (
    InvalidCredentialsException,
    TokenExpiredException,
    TokenInvalidException,
    UnauthorizedException,
    UserDisabledException,
)
from app.common.models import KnowledgeBasePermission, RefreshToken, User
from app.departments.models import Department
from app.departments.schemas import DepartmentBrief

logger = structlog.get_logger()


# ============================================================
# 登录
# ============================================================
async def login(
    db: AsyncSession, username: str, password: str
) -> LoginData:
    """用户登录

    1. 验证用户名和密码
    2. 检查用户状态
    3. 生成 Access Token 和 Refresh Token
    4. 保存 Refresh Token 哈希到数据库
    5. 更新最后登录时间
    """
    # 查询用户（包含角色和权限）
    result = await db.execute(
        select(User).where(User.username == username).with_for_update()
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsException()

    if user.status == "disabled":
        raise UserDisabledException()

    # 收集用户权限
    permissions = await _collect_user_permissions(db, user)
    roles_data = [
        UserRoleData(id=r.id, name=r.name)
        for r in user.roles
        if r.status == "active"
    ]

    # 收集知识库数据权限
    kb_access = await _collect_kb_access(db, user)
    department = await _get_department(db, user)

    # 生成 Token
    access_token = create_access_token(
        user.id,
        permissions,
        session_version=user.session_version,
    )
    raw_refresh_token, token_hash = create_refresh_token(user.id)

    # 保存 Refresh Token 哈希
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token_record)

    # 更新登录时间
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    # 构建用户信息
    me_data = MeData(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        department=department,
        roles=roles_data,
        permissions=permissions,
        knowledge_base_access=kb_access,
    )

    return LoginData(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        user=me_data,
    )


# ============================================================
# 退出
# ============================================================
async def logout(
    db: AsyncSession,
    user_id: str | None,
    refresh_token: str | None = None,
) -> None:
    """用户退出
    撤销指定的 Refresh Token（如果提供），或撤销该用户全部 Refresh Token
    """
    if refresh_token:
        import hashlib
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            ).with_for_update()
        )
        token_record = result.scalar_one_or_none()
        if token_record:
            token_record.revoked_at = datetime.now(timezone.utc)
    elif user_id is not None:
        # 撤销该用户所有未撤销的 Refresh Token
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for token_record in result.scalars().all():
            token_record.revoked_at = datetime.now(timezone.utc)

    await db.commit()


# ============================================================
# 刷新 Token
# ============================================================
async def refresh_access_token(
    db: AsyncSession, raw_refresh_token: str
) -> LoginData:
    """使用 Refresh Token 刷新 Access Token

    1. 验证 Refresh Token 哈希
    2. 检查是否过期或已撤销
    3. 检查用户状态
    4. 撤销旧 Refresh Token
    5. 发新 Token 对
    """
    import hashlib

    token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

    preliminary_result = await db.execute(
        select(RefreshToken.user_id).where(RefreshToken.token_hash == token_hash)
    )
    user_id = preliminary_result.scalar_one_or_none()
    if user_id is None:
        raise TokenInvalidException()

    # 与用户安全更新保持同一加锁顺序，避免刷新与禁用并发时产生可复活的新令牌。
    user_result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    user = user_result.scalar_one_or_none()

    if user is None:
        raise TokenInvalidException()

    if user.status == "disabled":
        raise UserDisabledException()

    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    token_record = result.scalar_one_or_none()

    if token_record is None or token_record.user_id != user.id:
        raise TokenInvalidException()

    if token_record.revoked_at is not None:
        raise TokenInvalidException()

    if token_record.expires_at < datetime.now(timezone.utc):
        raise TokenExpiredException()

    # 撤销旧 Refresh Token
    token_record.revoked_at = datetime.now(timezone.utc)

    # 收集权限
    permissions = await _collect_user_permissions(db, user)
    roles_data = [
        UserRoleData(id=r.id, name=r.name)
        for r in user.roles
        if r.status == "active"
    ]
    kb_access = await _collect_kb_access(db, user)
    department = await _get_department(db, user)

    # 生成新 Token
    access_token = create_access_token(
        user.id,
        permissions,
        session_version=user.session_version,
    )
    new_raw_token, new_token_hash = create_refresh_token(user.id)

    new_token_record = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_token_record)
    await db.commit()

    me_data = MeData(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        department=department,
        roles=roles_data,
        permissions=permissions,
        knowledge_base_access=kb_access,
    )

    return LoginData(
        access_token=access_token,
        refresh_token=new_raw_token,
        user=me_data,
    )


# ============================================================
# 获取当前用户信息
# ============================================================
async def get_me(db: AsyncSession, user_id: str) -> MeData:
    """获取当前用户信息"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException()

    if user.status == "disabled":
        raise UserDisabledException()

    permissions = await _collect_user_permissions(db, user)
    roles_data = [
        UserRoleData(id=r.id, name=r.name)
        for r in user.roles
        if r.status == "active"
    ]
    kb_access = await _collect_kb_access(db, user)
    department = await _get_department(db, user)

    return MeData(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        department=department,
        roles=roles_data,
        permissions=permissions,
        knowledge_base_access=kb_access,
    )


# ============================================================
# 辅助函数
# ============================================================
async def _collect_user_permissions(db: AsyncSession, user: User) -> list[str]:
    """收集用户所有权限码（从角色继承）"""
    permissions: set[str] = set()
    for role in user.roles:
        if role.status != "active":
            continue
        for perm in role.permissions:
            permissions.add(perm.code)
    return sorted(permissions)


async def _get_department(
    db: AsyncSession, user: User
) -> DepartmentBrief | None:
    if user.department_id is None:
        return None
    department = await db.get(Department, user.department_id)
    if department is None:
        return None
    return DepartmentBrief(id=department.id, name=department.name)


async def _collect_kb_access(
    db: AsyncSession, user: User
) -> list[KnowledgeBaseAccessData]:
    """收集用户的知识库数据权限"""
    result = await db.execute(
        select(KnowledgeBasePermission).where(
            KnowledgeBasePermission.subject_type == "user",
            KnowledgeBasePermission.subject_id == user.id,
        )
    )
    user_kb = result.scalars().all()

    # 同时从角色继承知识库权限
    role_ids = [r.id for r in user.roles if r.status == "active"]
    kb_access: dict[str, str] = {}
    if role_ids:
        result = await db.execute(
            select(KnowledgeBasePermission).where(
                KnowledgeBasePermission.subject_type == "role",
                KnowledgeBasePermission.subject_id.in_(role_ids),
            )
        )
        for perm in result.scalars().all():
            if perm.kb_id not in kb_access or perm.access_level == "admin":
                kb_access[perm.kb_id] = perm.access_level

    for perm in user_kb:
        if perm.kb_id not in kb_access or perm.access_level == "admin":
            kb_access[perm.kb_id] = perm.access_level

    return [
        KnowledgeBaseAccessData(kb_id=k, access_level=v)
        for k, v in kb_access.items()
    ]
