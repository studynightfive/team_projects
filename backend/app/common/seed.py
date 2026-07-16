# 数据库种子数据
# 员工3 负责
# 初始化默认权限码和管理员角色

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.common.models import Permission, Role, User

logger = structlog.get_logger()

# ============================================================
# 默认权限码（方案第4.3节路由表权限映射）
# ============================================================
DEFAULT_PERMISSIONS: list[dict] = [
    # 普通用户权限
    {"code": "chat.use", "name": "使用问答", "module": "chat", "action": "use"},
    {"code": "retrieval.search", "name": "知识检索", "module": "retrieval", "action": "search"},
    {"code": "knowledge_base.view", "name": "查看知识库", "module": "knowledge_base", "action": "view"},
    {"code": "document.view", "name": "查看文档", "module": "document", "action": "view"},
    {"code": "conversation.view", "name": "查看会话", "module": "conversation", "action": "view"},
    {"code": "export.view", "name": "查看导出", "module": "export", "action": "view"},
    {"code": "export.create", "name": "创建导出", "module": "export", "action": "create"},
    # 管理权限
    {"code": "admin.dashboard.view", "name": "查看系统概览", "module": "admin", "action": "dashboard.view"},
    {"code": "admin.user.view", "name": "查看用户列表", "module": "admin", "action": "user.view"},
    {"code": "admin.user.create", "name": "创建用户", "module": "admin", "action": "user.create"},
    {"code": "admin.user.edit", "name": "编辑用户", "module": "admin", "action": "user.edit"},
    {"code": "admin.role.view", "name": "查看角色列表", "module": "admin", "action": "role.view"},
    {"code": "admin.role.create", "name": "创建角色", "module": "admin", "action": "role.create"},
    {"code": "admin.role.edit", "name": "编辑角色", "module": "admin", "action": "role.edit"},
    {"code": "admin.role.delete", "name": "删除角色", "module": "admin", "action": "role.delete"},
    {"code": "admin.model.view", "name": "查看模型列表", "module": "admin", "action": "model.view"},
    {"code": "admin.model.create", "name": "创建模型", "module": "admin", "action": "model.create"},
    {"code": "admin.model.edit", "name": "编辑模型", "module": "admin", "action": "model.edit"},
    {"code": "admin.model.delete", "name": "删除模型", "module": "admin", "action": "model.delete"},
    {"code": "admin.knowledge_base.view", "name": "管理知识库", "module": "admin", "action": "knowledge_base.view"},
    {"code": "admin.knowledge_base.create", "name": "创建知识库", "module": "admin", "action": "knowledge_base.create"},
    {"code": "admin.knowledge_base.edit", "name": "编辑知识库", "module": "admin", "action": "knowledge_base.edit"},
    {"code": "admin.knowledge_base.delete", "name": "删除知识库", "module": "admin", "action": "knowledge_base.delete"},
    {"code": "admin.document.view", "name": "管理文档", "module": "admin", "action": "document.view"},
    {"code": "admin.document.upload", "name": "上传文档", "module": "admin", "action": "document.upload"},
    {"code": "admin.document.delete", "name": "删除文档", "module": "admin", "action": "document.delete"},
    {"code": "admin.task.view", "name": "查看转换任务", "module": "admin", "action": "task.view"},
    {"code": "admin.retrieval_test.run", "name": "运行命中率测试", "module": "admin", "action": "retrieval_test.run"},
    {"code": "admin.audit.view", "name": "查看审计日志", "module": "admin", "action": "audit.view"},
]


async def seed_permissions(db: AsyncSession) -> list[Permission]:
    """初始化默认权限码（幂等：已存在则跳过）"""
    permissions = []
    for perm_data in DEFAULT_PERMISSIONS:
        result = await db.execute(
            select(Permission).where(Permission.code == perm_data["code"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            permissions.append(existing)
        else:
            perm = Permission(**perm_data)
            db.add(perm)
            permissions.append(perm)

    await db.commit()
    return permissions


async def seed_default_admin(
    db: AsyncSession,
    username: str = "admin",
    password: str = "admin123",
) -> User:
    """创建默认管理员账号（幂等：已存在则跳过）"""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # 获取所有权限
    result = await db.execute(select(Permission))
    all_permissions = result.scalars().all()

    # 创建管理员角色
    result = await db.execute(
        select(Role).where(Role.name == "超级管理员")
    )
    admin_role = result.scalar_one_or_none()
    if not admin_role:
        admin_role = Role(
            name="超级管理员",
            description="拥有所有权限的超级管理员角色",
            permissions=list(all_permissions),
        )
        db.add(admin_role)

    # 创建用户角色
    result = await db.execute(
        select(Role).where(Role.name == "普通用户")
    )
    user_role = result.scalar_one_or_none()
    if not user_role:
        basic_permissions = [
            p for p in all_permissions
            if not p.code.startswith("admin.")
        ]
        user_role = Role(
            name="普通用户",
            description="默认普通用户角色，仅有基础功能权限",
            permissions=basic_permissions,
        )
        db.add(user_role)

    # 创建管理员用户
    user = User(
        username=username,
        display_name="系统管理员",
        password_hash=hash_password(password),
        status="active",
        roles=[admin_role],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("default_admin_created", username=username)
    return user
