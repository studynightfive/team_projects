# 核心数据库模型
# 员工3 负责：User、Role、Permission、RefreshToken、AuditLog
# 方案第5.1节：核心实体定义
# 方案第9.3节：员工3 负责数据库迁移

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database import Base

# ============================================================
# 关联表：user_roles（用户与角色多对多）
# ============================================================
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# ============================================================
# 关联表：role_permissions（角色与权限多对多）
# ============================================================
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "permission_id",
        String(36),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ============================================================
# User 模型
# ============================================================
class User(Base):
    """用户模型（方案第5.1节）"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(
        String(150), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )  # active, disabled
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关联
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=user_roles, back_populates="users", lazy="selectin"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


# ============================================================
# Role 模型
# ============================================================
class Role(Base):
    """角色模型（方案第5.1节）"""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, disabled
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关联
    users: Mapped[list["User"]] = relationship(
        "User", secondary=user_roles, back_populates="roles", lazy="selectin"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


# ============================================================
# Permission 模型
# ============================================================
class Permission(Base):
    """权限码模型（方案第5.1节）"""

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=role_permissions, back_populates="permissions", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, code={self.code})>"


# ============================================================
# KnowledgeBasePermission 模型（知识库数据权限）
# ============================================================
class KnowledgeBasePermission(Base):
    """知识库数据权限模型（方案第5.1节）
    定义用户或角色对知识库的访问级别
    """

    __tablename__ = "knowledge_base_permissions"
    __table_args__ = (
        UniqueConstraint(
            "subject_type", "subject_id", "kb_id", name="uq_kb_permission_subject_kb"
        ),
        Index("ix_kb_permissions_subject_type", "subject_type"),
        Index("ix_kb_permissions_subject_id", "subject_id"),
        Index("ix_kb_permissions_kb_id", "kb_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)  # user, role
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False)
    kb_id: Mapped[str] = mapped_column(String(36), nullable=False)
    access_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="read"
    )  # read, write, admin
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBasePermission("
            f"subject={self.subject_type}:{self.subject_id}, "
            f"kb={self.kb_id}, level={self.access_level})>"
        )


# ============================================================
# RefreshToken 模型
# ============================================================
class RefreshToken(Base):
    """刷新令牌模型
    存储 Refresh Token 的哈希值，支持会话撤销
    方案第5.3节：Refresh Token 只保存哈希
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
        Index("ix_refresh_tokens_token_hash", "token_hash", unique=True),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    user: Mapped["User"] = relationship("User")


# ============================================================
# AuditLog 模型
# ============================================================
class AuditLog(Base):
    """审计日志模型
    方案第9.3节：员工3 负责审计日志
    方案第15.5节：不记录 Secret 和敏感正文
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(36))
    detail: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    result: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success"
    )  # success, failure, denied
    request_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 关联
    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action})>"
