"""意图识别与 Query 改写单元测试。"""

from __future__ import annotations

import pytest

from app.rag.intent import classify_intent_rules, intent_direct_reply
from app.rag.query_rewrite import rewrite_query_rules
from app.rag.search.service import rrf_fuse_many


def test_intent_chitchat() -> None:
    r = classify_intent_rules("你好")
    assert r.intent == "chitchat"
    assert intent_direct_reply(r.intent)


def test_intent_knowledge_default() -> None:
    r = classify_intent_rules("请假流程需要哪些材料？")
    assert r.intent == "knowledge_qa"
    assert intent_direct_reply(r.intent) is None


def test_intent_clarification_short() -> None:
    r = classify_intent_rules("啊")
    assert r.intent == "clarification"


def test_rewrite_strips_filler() -> None:
    original = "\u8bf7\u95ee\u5e2e\u6211\u67e5\u4e00\u4e0b\u8bf7\u5047\u6d41\u7a0b"  # noqa: E501  # 请问帮我查一下请假流程
    r = rewrite_query_rules(original)
    assert "\u8bf7\u95ee" not in r.primary  # 请问
    assert "\u5e2e\u6211" not in r.primary  # 帮我
    assert "\u8bf7\u5047\u6d41\u7a0b" in r.primary  # 请假流程
    assert r.original == original
    assert len(r.all_queries) >= 1


def test_rrf_fuse_many_merges_queries() -> None:
    a = [{"chunk_id": "c1", "score": 1.0}, {"chunk_id": "c2", "score": 0.5}]
    b = [{"chunk_id": "c2", "score": 0.9}, {"chunk_id": "c3", "score": 0.4}]
    fused = rrf_fuse_many([a, b])
    assert fused[0]["chunk_id"] in {"c1", "c2"}
    assert {h["chunk_id"] for h in fused} == {"c1", "c2", "c3"}


@pytest.mark.asyncio
async def test_rewrite_disabled_keeps_original(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock

    from app.rag import query_rewrite

    monkeypatch.setattr(query_rewrite.settings, "rag_query_rewrite_enabled", True)
    out = await query_rewrite.rewrite_query(AsyncMock(), "原始问题", enabled=False)
    assert out.primary == "原始问题"
    assert out.source == "off"
