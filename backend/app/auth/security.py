# 安全工具模块
# 员工3 负责
# 方案第5.3节：密码使用 Argon2，Refresh Token 只保存哈希
# JWT Token 生成与验证

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.common.config import settings

# ============================================================
# 密码哈希器（Argon2）
# ============================================================
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """使用 Argon2 哈希密码"""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerificationError, InvalidHashError):
        return False


# ============================================================
# JWT Token 管理
# ============================================================
def create_access_token(
    user_id: str,
    permissions: list[str],
    session_version: int = 0,
) -> str:
    """创建 Access Token（短期，默认 30 分钟）"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "permissions": permissions,
        "session_version": session_version,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """创建 Refresh Token（长期，默认 7 天）

    返回 (raw_token, token_hash)
    raw_token 发给客户端，token_hash 存入数据库
    """
    raw_token = str(uuid.uuid4()) + "." + str(uuid.uuid4())
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def decode_access_token(token: str) -> dict[str, object]:
    """解码并验证 Access Token

    成功返回 payload，失败抛出 jwt.PyJWTError
    """
    raw_payload: object = jwt.decode(
        token,
        settings.secret_key,
        algorithms=["HS256"],
        options={"require": ["exp", "sub", "type"]},
    )
    if not isinstance(raw_payload, dict):
        raise jwt.InvalidTokenError("token payload must be an object")
    payload: dict[str, object] = {}
    for key, value in raw_payload.items():
        if not isinstance(key, str):
            raise jwt.InvalidTokenError("token payload key must be a string")
        payload[key] = value
    return payload


def verify_token_type(payload: dict[str, object], expected_type: str = "access") -> bool:
    """验证 Token 类型"""
    return payload.get("type") == expected_type
