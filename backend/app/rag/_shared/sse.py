"""SSE 事件格式化（提示词 03 §4）"""
from __future__ import annotations

import json
import uuid
from typing import Any


def _json_default(obj: Any) -> Any:
    try:
        return obj.model_dump()
    except AttributeError:
        return str(obj)


def format_sse(*, event: str, data: Any, event_id: str | None = None) -> str:
    """将事件序列化为 SSE 字符串（utf-8，单事件多 data 行）。"""
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False, default=_json_default)
    else:
        payload = str(data)
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    for line in payload.split("\n"):
        lines.append(f"data: {line}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def format_keepalive() -> str:
    return ": keepalive\n\n"


def new_message_id() -> str:
    return str(uuid.uuid4())