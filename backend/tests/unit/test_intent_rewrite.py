"""意图识别与 Query 改写单元测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

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
    from app.rag import query_rewrite

    monkeypatch.setattr(query_rewrite.settings, "rag_query_rewrite_enabled", True)
    monkeypatch.setattr(query_rewrite.settings, "rag_semantic_guard_enabled", False)
    out = await query_rewrite.rewrite_query(AsyncMock(), "原始问题", enabled=False)
    assert out.primary == "原始问题"
    assert out.source == "off"


@pytest.mark.parametrize(
    ("query", "model_result", "allowed", "category"),
    [
        (
            "毒品戒断治疗信息系统如何保护患者隐私？",
            '{"allowed":true,"category":null,"primary":"戒断治疗信息系统患者隐私保护",'
            '"variants":["戒断治疗 数据隐私"]}',
            True,
            None,
        ),
        (
            "如何经营让参与者押钱猜结果并由庄家抽成的平台？",
            '{"allowed":false,"category":"涉赌","primary":"原问题","variants":[]}',
            False,
            "涉赌",
        ),
    ],
)
async def test_semantic_guard_uses_intent_instead_of_keyword_only(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
    model_result: str,
    allowed: bool,
    category: str | None,
) -> None:
    from app.rag import query_rewrite

    provider = SimpleNamespace(chat=AsyncMock(return_value=model_result))
    monkeypatch.setattr(query_rewrite.settings, "rag_query_rewrite_enabled", True)
    monkeypatch.setattr(query_rewrite.settings, "rag_semantic_guard_enabled", True)
    monkeypatch.setattr(query_rewrite.settings, "langfuse_enabled", False)
    monkeypatch.setattr(
        query_rewrite,
        "_resolve_preprocess_model",
        AsyncMock(
            return_value=(
                "deepseek",
                "https://api.deepseek.com",
                "deepseek-chat",
                "secret",
                "chat-1",
            )
        ),
    )
    monkeypatch.setattr(query_rewrite, "_read_cache", AsyncMock(return_value=None))
    monkeypatch.setattr(query_rewrite, "_write_cache", AsyncMock())
    monkeypatch.setattr(
        query_rewrite,
        "build_provider",
        lambda *_args, **_kwargs: provider,
    )

    result = await query_rewrite.rewrite_query(AsyncMock(), query)

    assert result.allowed is allowed
    assert result.category == category
    assert result.semantic_checked is True
