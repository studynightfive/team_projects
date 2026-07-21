# 数据库种子数据
# 员工3 负责
# 初始化默认权限码和管理员角色
# ruff: noqa: E501

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.common.config import settings
from app.common.models import KnowledgeBasePermission, Permission, Role, User
from app.knowledge.models import KnowledgeBase
from app.models.repository import Model, ModelProvider
from app.models.security import encrypt_api_key

logger = structlog.get_logger()

# ============================================================
# 默认权限码（方案第4.3节路由表权限映射）
# ============================================================
DEFAULT_PERMISSIONS: list[dict[str, str]] = [
    # 普通用户权限
    {"code": "chat.use", "name": "使用问答", "module": "chat", "action": "use"},
    {"code": "retrieval.search", "name": "知识检索", "module": "retrieval", "action": "search"},
    {"code": "knowledge_base.view", "name": "查看知识库", "module": "knowledge_base", "action": "view"},
    {"code": "document.view", "name": "查看文档", "module": "document", "action": "view"},
    {"code": "document.upload", "name": "上传文档", "module": "document", "action": "upload"},
    {"code": "conversation.view", "name": "查看会话", "module": "conversation", "action": "view"},
    {"code": "conversation:read", "name": "读取会话", "module": "conversation", "action": "read"},
    {"code": "conversation:write", "name": "写入会话", "module": "conversation", "action": "write"},
    {"code": "conversation:delete", "name": "删除会话", "module": "conversation", "action": "delete"},
    {"code": "export.view", "name": "查看导出", "module": "export", "action": "view"},
    {"code": "export.create", "name": "创建导出", "module": "export", "action": "create"},
    {"code": "export:read", "name": "读取导出任务", "module": "export", "action": "read"},
    {"code": "export:write", "name": "创建导出任务", "module": "export", "action": "write"},
    {"code": "export:download", "name": "下载导出文件", "module": "export", "action": "download"},
    {"code": "export:delete", "name": "删除导出任务", "module": "export", "action": "delete"},
    {"code": "favorite:read", "name": "读取收藏", "module": "favorite", "action": "read"},
    {"code": "favorite:write", "name": "写入收藏", "module": "favorite", "action": "write"},
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
    {"code": "admin.export.cleanup", "name": "清理过期导出任务", "module": "admin", "action": "export.cleanup"},
    {"code": "admin.retrieval_test.run", "name": "运行命中率测试", "module": "admin", "action": "retrieval_test.run"},
    {"code": "admin.audit.view", "name": "查看审计日志", "module": "admin", "action": "audit.view"},
]

SUPER_ADMIN_ROLE_NAME = "超级管理员"
DEFAULT_USER_ROLE_NAME = "普通用户"
KNOWLEDGE_EDITOR_ROLE_NAME = "知识库编辑者"

DEFAULT_USER_PERMISSION_CODES = frozenset(
    {
        "chat.use",
        "retrieval.search",
        "knowledge_base.view",
        "document.view",
        "conversation.view",
        "conversation:read",
        "conversation:write",
        "conversation:delete",
        "export.view",
        "export.create",
        "export:read",
        "export:write",
        "export:download",
        "export:delete",
        "favorite:read",
        "favorite:write",
    }
)

KNOWLEDGE_EDITOR_PERMISSION_CODES = frozenset(
    {
        "chat.use",
        "retrieval.search",
        "knowledge_base.view",
        "document.view",
        "document.upload",
        "conversation.view",
        "conversation:read",
        "conversation:write",
        "export.view",
        "export.create",
        "export:read",
        "export:write",
        "export:download",
        "favorite:read",
        "favorite:write",
        "admin.knowledge_base.view",
        "admin.knowledge_base.create",
        "admin.knowledge_base.edit",
        "admin.document.view",
        "admin.document.upload",
        "admin.task.view",
    }
)


async def seed_permissions(db: AsyncSession) -> list[Permission]:
    """幂等初始化默认权限码，并纠正遗留字段。"""
    permissions: list[Permission] = []
    for perm_data in DEFAULT_PERMISSIONS:
        result = await db.execute(
            select(Permission).where(Permission.code == perm_data["code"])
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            perm = Permission(**perm_data)
            db.add(perm)
            permissions.append(perm)
            continue

        existing.name = perm_data["name"]
        existing.module = perm_data["module"]
        existing.action = perm_data["action"]
        permissions.append(existing)

    await db.commit()
    return permissions


async def _upsert_role(
    db: AsyncSession,
    *,
    name: str,
    description: str,
    permissions: list[Permission],
) -> Role:
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role is None:
        role = Role(name=name, description=description, status="active")
        db.add(role)
    role.description = description
    role.status = "active"
    role.permissions = list(permissions)
    await db.flush()
    return role


async def seed_builtin_authorization(db: AsyncSession) -> dict[str, Role]:
    """幂等初始化内建角色，并以当前白名单纠正遗留授权。"""
    permissions = await seed_permissions(db)
    role_specs = (
        (
            SUPER_ADMIN_ROLE_NAME,
            "拥有全部平台管理与业务权限",
            permissions,
        ),
        (
            DEFAULT_USER_ROLE_NAME,
            "默认普通用户角色，可使用知识库、检索、问答、收藏和下载功能",
            [
                permission
                for permission in permissions
                if permission.code in DEFAULT_USER_PERMISSION_CODES
            ],
        ),
        (
            KNOWLEDGE_EDITOR_ROLE_NAME,
            "知识库维护角色，可创建知识库、上传文档和查看任务",
            [
                permission
                for permission in permissions
                if permission.code in KNOWLEDGE_EDITOR_PERMISSION_CODES
            ],
        ),
    )
    roles: dict[str, Role] = {}
    for name, description, role_permissions in role_specs:
        roles[name] = await _upsert_role(
            db,
            name=name,
            description=description,
            permissions=role_permissions,
        )
    await db.commit()
    logger.info("builtin_authorization_seeded", roles=list(roles))
    return roles


async def _upsert_user(
    db: AsyncSession,
    *,
    username: str,
    display_name: str,
    password: str,
    roles: list[Role],
) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username=username,
            display_name=display_name,
            password_hash="",
            status="active",
        )
        db.add(user)
    user.display_name = display_name
    user.password_hash = hash_password(password)
    user.status = "active"
    user.roles = list(roles)
    await db.flush()
    return user


async def seed_demo_accounts(db: AsyncSession) -> list[User]:
    """创建或重置交付演示账号，并拒绝绕过配置安全门禁。"""
    if not settings.auto_seed_demo_data or len(settings.demo_seed_password) < 12:
        raise RuntimeError(
            "演示账号播种需要 AUTO_SEED_DEMO_DATA=true "
            "且 DEMO_SEED_PASSWORD 至少 12 位"
        )

    result = await db.execute(
        select(Role).where(
            Role.name.in_(
                {
                    SUPER_ADMIN_ROLE_NAME,
                    DEFAULT_USER_ROLE_NAME,
                    KNOWLEDGE_EDITOR_ROLE_NAME,
                }
            )
        )
    )
    roles = {role.name: role for role in result.scalars().all()}
    if len(roles) != 3:
        raise RuntimeError("内建角色尚未完成初始化")

    admin_role = roles[SUPER_ADMIN_ROLE_NAME]
    user_role = roles[DEFAULT_USER_ROLE_NAME]
    editor_role = roles[KNOWLEDGE_EDITOR_ROLE_NAME]

    users = [
        await _upsert_user(
            db,
            username="admin",
            display_name="系统管理员",
            password=settings.demo_seed_password,
            roles=[admin_role],
        ),
        await _upsert_user(
            db,
            username="liuhaiwang",
            display_name="刘海旺",
            password=settings.demo_seed_password,
            roles=[user_role],
        ),
        await _upsert_user(
            db,
            username="qmxl",
            display_name="知识库编辑者",
            password=settings.demo_seed_password,
            roles=[editor_role],
        ),
    ]
    await db.commit()
    logger.info("demo_accounts_seeded", usernames=[user.username for user in users])
    return users


async def _ensure_kb_role_permission(
    db: AsyncSession,
    *,
    role_name: str,
    kb_id: str,
    access_level: str,
) -> None:
    role_result = await db.execute(select(Role).where(Role.name == role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        return
    existing_result = await db.execute(
        select(KnowledgeBasePermission).where(
            KnowledgeBasePermission.subject_type == "role",
            KnowledgeBasePermission.subject_id == role.id,
            KnowledgeBasePermission.kb_id == kb_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is None:
        db.add(
            KnowledgeBasePermission(
                subject_type="role",
                subject_id=role.id,
                kb_id=kb_id,
                access_level=access_level,
            )
        )
    else:
        existing.access_level = access_level


async def _ensure_default_kb_permissions(db: AsyncSession, kb_id: str) -> None:
    await _ensure_kb_role_permission(
        db, role_name="超级管理员", kb_id=kb_id, access_level="admin"
    )
    await _ensure_kb_role_permission(
        db, role_name="普通用户", kb_id=kb_id, access_level="read"
    )
    await _ensure_kb_role_permission(
        db, role_name="知识库编辑者", kb_id=kb_id, access_level="admin"
    )


async def seed_default_knowledge_base(db: AsyncSession) -> KnowledgeBase:
    """创建默认交付演示知识库（幂等）。"""
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.name == "默认知识库")
    )
    existing = result.scalar_one_or_none()
    if existing:
        await _ensure_default_kb_permissions(db, existing.id)
        await db.commit()
        return existing

    kb = KnowledgeBase(
        name="默认知识库",
        description="用于基础交付演示的默认知识集合，可上传文档后直接检索。",
        chunk_size=800,
        chunk_overlap=120,
    )
    db.add(kb)
    await db.flush()

    await _ensure_default_kb_permissions(db, kb.id)

    await db.commit()
    await db.refresh(kb)
    logger.info("default_knowledge_base_created", kb_id=kb.id)
    return kb


async def seed_default_embedding_model(db: AsyncSession) -> None:
    """配置默认 Qwen embedding 模型（幂等）。"""
    provider = await db.get(ModelProvider, "dashscope")
    if provider is None:
        provider = ModelProvider(
            code="dashscope",
            display_name="阿里云 DashScope",
            base_url=settings.dashscope_base_url,
            enabled=True,
        )
        db.add(provider)
    else:
        provider.display_name = "阿里云 DashScope"
        provider.base_url = settings.dashscope_base_url
        provider.enabled = True

    legacy_names = {
        settings.qwen_embedding_model,
        "text-embedding-v2",
        "text-embedding-v4",
        "qwen3-embedding-0.6b",
        "Qwen3-Embedding-0.6B",
    }
    result = await db.execute(
        select(Model).where(
            Model.provider_code == "dashscope",
            Model.kind == "embedding",
            Model.model_name.in_(legacy_names),
        ).limit(1)
    )
    model = result.scalar_one_or_none()
    if model is None:
        model = Model(
            provider_code="dashscope",
            model_name=settings.qwen_embedding_model,
            kind="embedding",
            parameters={"input_type": "document"},
            dimensions=settings.qwen_embedding_dimensions,
            distance="cosine",
            enabled=True,
        )
        db.add(model)
    model.model_name = settings.qwen_embedding_model
    model.dimensions = settings.qwen_embedding_dimensions
    model.distance = "cosine"
    model.enabled = True
    model.parameters = {**(model.parameters or {}), "input_type": "document"}
    if settings.dashscope_api_key:
        model.api_key_encrypted = encrypt_api_key(settings.dashscope_api_key)
    await db.commit()
    logger.info(
        "default_embedding_model_seeded",
        provider="dashscope",
        model=settings.qwen_embedding_model,
        api_key_set=bool(settings.dashscope_api_key),
    )


async def seed_default_chat_model(db: AsyncSession) -> None:
    """配置默认 RAG 聊天模型（幂等；经 DEEPSEEK_* 注入，可指向 MiniMax 等 OpenAI 兼容端点）。"""
    is_minimax = "minimax" in settings.deepseek_base_url.lower() or settings.deepseek_chat_model.lower().startswith(
        "minimax"
    )
    provider_display = "MiniMax" if is_minimax else "DeepSeek"
    provider = await db.get(ModelProvider, "deepseek")
    if provider is None:
        provider = ModelProvider(
            code="deepseek",
            display_name=provider_display,
            base_url=settings.deepseek_base_url,
            enabled=True,
        )
        db.add(provider)
    else:
        provider.display_name = provider_display
        provider.base_url = settings.deepseek_base_url
        provider.enabled = True

    legacy_names = {
        settings.deepseek_chat_model,
        "deepseek-chat",
        "deepseek-v4-pro",
        "MiniMax-M3",
    }
    result = await db.execute(
        select(Model).where(
            Model.provider_code == "deepseek",
            Model.kind == "chat",
            Model.model_name.in_(legacy_names),
        ).limit(1)
    )
    model = result.scalar_one_or_none()
    if model is None:
        model = Model(
            provider_code="deepseek",
            model_name=settings.deepseek_chat_model,
            kind="chat",
            parameters={"temperature": 0.2, "max_tokens": settings.rag_answer_max_tokens},
            enabled=True,
        )
        db.add(model)
    model.model_name = settings.deepseek_chat_model
    model.enabled = True
    model.parameters = {
        **(model.parameters or {}),
        "temperature": (model.parameters or {}).get("temperature", 0.2),
        "max_tokens": settings.rag_answer_max_tokens,
    }
    if settings.deepseek_api_key:
        model.api_key_encrypted = encrypt_api_key(settings.deepseek_api_key)
    await db.commit()
    logger.info(
        "default_chat_model_seeded",
        provider="deepseek",
        model=settings.deepseek_chat_model,
        api_key_set=bool(settings.deepseek_api_key),
    )
