# cython: language_level=3
"""许可证签名验证核心。

该文件只在镜像构建阶段存在，运行镜像仅保留编译后的扩展。Python 层只能获得
布尔结果，不提供序列号读取接口。
"""

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


DEF LICENSE_PUBLIC_KEY_HEX = ""

cdef str _PRODUCT = "knowledge-base-platform"
cdef str _PUBLIC_KEY_HEX = LICENSE_PUBLIC_KEY_HEX


cdef object _parse_expiration(object value):
    cdef str raw
    cdef object parsed
    if not isinstance(value, str):
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def license_is_valid(str path):
    """验证许可证，但不向 Python 返回序列号、载荷或签名内容。"""

    cdef object document
    cdef object signed_payload
    cdef object serial_number
    cdef object expires_at
    cdef object signature
    cdef bytes canonical
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            return False
        signature = document.get("signature")
        serial_number = document.get("serial")
        expires_at = _parse_expiration(document.get("expires_at"))
        if (
            document.get("product") != _PRODUCT
            or not isinstance(serial_number, str)
            or len(serial_number.strip()) < 8
            or expires_at is None
            or expires_at <= datetime.now(timezone.utc)
            or not isinstance(signature, str)
        ):
            return False
        signed_payload = {
            key: value
            for key, value in document.items()
            if key != "signature"
        }
        canonical = json.dumps(
            signed_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(_PUBLIC_KEY_HEX)
        ).verify(base64.b64decode(signature, validate=True), canonical)
        return True
    except (
        InvalidSignature,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return False
