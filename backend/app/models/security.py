"""模型 API Key Fernet 加解密（提示词 01 §4.2）"""
from __future__ import annotations

from app.common.config import get_model_key_fernet


def encrypt_api_key(plain: str) -> str:
    if not plain:
        return ""
    return get_model_key_fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    if not encrypted:
        return ""
    return get_model_key_fernet().decrypt(encrypted.encode()).decode()