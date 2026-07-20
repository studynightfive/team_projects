"""token 估算与会话上下文裁剪（提示词 04 §4.5）"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

# 经验值：1 token ≈ 1 字符（CJK 与英文混合样本，保守估计）
CHARS_PER_TOKEN = 1.0


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return int(len(text) / CHARS_PER_TOKEN)


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    max_chars = int(max_tokens * CHARS_PER_TOKEN)
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


MessageT = TypeVar("MessageT", bound=Mapping[str, object])


def fit_messages_to_budget(messages: list[MessageT], max_tokens: int) -> list[MessageT]:
    """从最新到最旧贪心填充，直到 token 预算耗尽。"""
    kept: list[MessageT] = []
    used = 0
    for msg in reversed(messages):
        content = msg.get("content", "")
        cost = estimate_tokens(content if isinstance(content, str) else "")
        if used + cost > max_tokens and kept:
            break
        kept.append(msg)
        used += cost
    return list(reversed(kept))
