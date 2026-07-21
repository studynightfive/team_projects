"""关键词拆词单测。"""

from app.rag.search.service import extract_search_terms


def test_extract_search_terms_chinese_question() -> None:
    terms = extract_search_terms("一线城市差旅住宿标准是多少？")
    assert any("一线" in term or term == "一线城市" for term in terms)
    assert any("差旅" in term or "住宿" in term for term in terms)
    assert "多少" not in terms


def test_extract_search_terms_keeps_english_tokens() -> None:
    terms = extract_search_terms("如何配置 Redis cache TTL")
    assert "redis" in terms
    assert "cache" in terms
    assert "ttl" in terms
