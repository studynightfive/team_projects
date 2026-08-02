"""RAG 用户输入的确定性安全校验。"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.common.exceptions import ValidationException

if TYPE_CHECKING:
    from app.rag.query_rewrite import RewriteResult

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


async def ensure_safe_query(
    value: str,
    *,
    db: AsyncSession | None = None,
    model_id: str | None = None,
    trace_id: str | None = None,
) -> RewriteResult:
    """校验查询并返回同一次模型调用生成的检索改写。"""

    result = await inspect_query(
        value,
        db=db,
        model_id=model_id,
        trace_id=trace_id,
    )
    if not result.allowed:
        category = result.category or "不合规内容"
        logger.warning(
            "rag_input_blocked",
            category=category,
            scanner="semantic" if result.semantic_checked else "keyword-fallback",
        )
        raise ValidationException(message="输入内容不合法，请修改后重试")
    return result


async def inspect_query(
    value: str,
    *,
    db: AsyncSession | None = None,
    model_id: str | None = None,
    trace_id: str | None = None,
) -> RewriteResult:
    """返回安全判定；供输入框预检和最终提交复用。"""

    # 延迟导入可让 query_rewrite 复用本模块的规范化规则而不形成初始化循环。
    from app.rag.query_rewrite import rewrite_query, rewrite_query_rules

    candidate_category = classify_prohibited_input(value)
    if db is None:
        result = rewrite_query_rules(value)
    else:
        result = await rewrite_query(
            db,
            value,
            model_id=model_id,
            trace_id=trace_id,
        )

    if (
        not result.semantic_checked
        and candidate_category is not None
        and (db is None or not settings.rag_semantic_guard_enabled)
    ):
        return replace(
            result,
            allowed=False,
            category=candidate_category,
        )
    return result
