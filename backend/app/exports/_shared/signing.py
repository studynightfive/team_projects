"""下载 URL HMAC 签名（提示词 05 §4.5）"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

from app.common.config import get_export_download_signing_key


def sign_download_token(*, export_id: str, user_id: str, expires_at_unix: int) -> str:
    """生成不可逆猜的下载 token（URL 不含明文密钥）。"""
    payload = f"{export_id}|{user_id}|{expires_at_unix}".encode()
    sig = hmac.new(get_export_download_signing_key().encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=")


def verify_download_token(
    *, export_id: str, user_id: str, expires_at_unix: int, token: str
) -> bool:
    expected = sign_download_token(
        export_id=export_id, user_id=user_id, expires_at_unix=expires_at_unix
    )
    return hmac.compare_digest(expected, token)


def is_expired(expires_at_unix: int, *, now_unix: int | None = None) -> bool:
    now = now_unix if now_unix is not None else int(time.time())
    return now > expires_at_unix
