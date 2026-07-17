"""token 估算与会话上下文裁剪（提示词 04 §4.5）"""

from __future__ import annotations

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


def fit_messages_to_budget(messages: list[dict], max_tokens: int) -> list[dict]:
    """从最新到最旧贪心填充，直到 token 预算耗尽。"""
    kept: list[dict] = []
    used = 0
    for msg in reversed(messages):
        cost = estimate_tokens(msg.get("content", ""))
        if used + cost > max_tokens and kept:
            break
        kept.append(msg)
        used += cost
    return list(reversed(kept))
