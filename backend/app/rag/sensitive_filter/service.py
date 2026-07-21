"""敏感词过滤服务 — 编排 Layer 1 (正则) 和 Layer 2 (BERT)

两层过滤策略：
1. Layer 1 (regex): 快速精确匹配，拦截已知敏感词和攻击模式
2. Layer 2 (BERT):  语义意图识别，拦截变体和隐晦表达

只有两个 Layer 都通过的问题才能进入后续检索环节。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from app.rag.sensitive_filter.bert_filter import check_bert
from app.rag.sensitive_filter.regex_filter import check_regex

logger = logging.getLogger(__name__)


class FilterVerdict(str, Enum):
    """过滤判定结果"""
    PASS = "pass"            # 通过
    BLOCK_REGEX = "regex"    # Layer 1 拦截
    BLOCK_BERT = "bert"      # Layer 2 拦截


@dataclass
class FilterResult:
    """敏感词过滤结果"""
    verdict: FilterVerdict
    passed: bool
    # Layer 1 详情
    regex_matches: list[str] = field(default_factory=list)
    # Layer 2 详情
    bert_confidence: float = 0.0
    bert_label: str = ""
    # 汇总
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "verdict": self.verdict.value,
            "regex_matches": self.regex_matches,
            "bert_confidence": round(self.bert_confidence, 4),
            "bert_label": self.bert_label,
            "reason": self.reason,
        }


async def check_sensitive(question: str) -> FilterResult:
    """执行两层敏感词过滤

    流程：
    1. Layer 1 — 正则匹配：快速拦截已知敏感词
    2. Layer 2 — BERT 语义：深度识别隐晦/变体敏感意图

    两层的执行是串行的（先正则后 BERT），正则命中后
    直接拦截，不再执行 BERT 以节省计算资源。

    Args:
        question: 用户输入的问题文本

    Returns:
        FilterResult: 包含 verdict, regex_matches, bert_confidence 等
    """
    result = FilterResult(verdict=FilterVerdict.PASS, passed=True)

    # ================================================================
    # Layer 1: 正则过滤 — O(1) 级别，毫秒级延迟
    # ================================================================
    is_regex_blocked, regex_matches = check_regex(question)
    result.regex_matches = regex_matches

    if is_regex_blocked:
        result.verdict = FilterVerdict.BLOCK_REGEX
        result.passed = False
        rules = "; ".join(regex_matches[:3])
        result.reason = f"正则过滤器拦截 — 命中 {len(regex_matches)} 条规则: {rules}"
        logger.info(
            "sensitive_filter_blocked_regex",
            question_len=len(question),
            match_count=len(regex_matches),
        )
        return result

    # ================================================================
    # Layer 2: BERT 语义过滤 — 百毫秒级延迟（模型预热后更快）
    # ================================================================
    try:
        is_bert_blocked, bert_confidence, bert_label = check_bert(question)
    except Exception as exc:
        # BERT 失败时放行（避免误阻断正常业务），但记录告警
        logger.warning("BERT 过滤异常，降级放行: %s", exc)
        result.bert_confidence = 0.0
        result.bert_label = f"BERT异常降级: {type(exc).__name__}"
        result.reason = "BERT 过滤器暂不可用，降级放行"
        return result

    result.bert_confidence = bert_confidence
    result.bert_label = bert_label

    if is_bert_blocked:
        result.verdict = FilterVerdict.BLOCK_BERT
        result.passed = False
        result.reason = (
            f"BERT 语义过滤器拦截 — 敏感相似度 {bert_confidence:.4f} "
            f"超过阈值 — {bert_label}"
        )
        logger.info(
            "sensitive_filter_blocked_bert",
            question_len=len(question),
            bert_confidence=bert_confidence,
        )
        return result

    # 通过
    logger.debug("sensitive_filter_passed", question_len=len(question))
    return result
