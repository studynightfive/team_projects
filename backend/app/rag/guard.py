"""RAG 用户输入的确定性安全校验。"""

from __future__ import annotations

import re
import unicodedata

import structlog

from app.common.exceptions import ValidationException

logger = structlog.get_logger()

_CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "涉黄": (
        "色情",
        "成人视频",
        "成人影片",
        "无码影片",
        "裸露影像",
        "露骨内容",
        "黄色网站",
        "裸聊",
        "淫秽",
        "约炮",
        "性服务",
        "卖淫",
        "嫖娼",
    ),
    "涉赌": (
        "赌博",
        "博彩",
        "赌场",
        "赌钱",
        "赌局",
        "下注",
        "赌资",
        "洗码",
        "百家乐",
        "轮盘",
        "老虎机",
        "牌九",
        "德州扑克",
        "casino",
        "gambling",
        "betting",
    ),
    "涉毒": (
        "毒品",
        "制毒",
        "贩毒",
        "吸毒",
        "冰毒",
        "海洛因",
        "摇头丸",
        "麻古",
        "可卡因",
        "k粉",
        "违禁粉末",
        "cocaine",
        "heroin",
        "methamphetamine",
        "芬太尼滥用",
    ),
}


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)


def classify_prohibited_input(value: str) -> str | None:
    normalized = _normalize(value)
    for category, terms in _CATEGORY_TERMS.items():
        if any(_normalize(term) in normalized for term in terms):
            return category
    return None


async def ensure_safe_query(value: str) -> None:
    """拦截明确违规词条；不执行概率模型判断，避免误杀正常问题。"""
    category = classify_prohibited_input(value)
    if category is not None:
        logger.warning("rag_input_blocked", category=category, scanner="keyword")
        raise ValidationException(message=f"输入内容涉及{category}，无法进行检索或问答")
