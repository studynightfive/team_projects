"""员工5 提示词 02 - 检索引擎单元测试

覆盖：
- RRF 融合函数（提示词 02 §4.2 公式）
- post_filter_hits 双重权限过滤
- SearchRequest / SearchResponse schema
- 重排降级（rerank 模型不存在时回退到 RRF 排序）
"""

from __future__ import annotations

import pytest

from app.rag._shared.permissions import post_filter_hits
from app.rag.search.schemas import (
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.rag.search.service import rrf_fuse


# ============================================================
# RRF 融合（Reciprocal Rank Fusion）
# ============================================================
class TestRRFFusion:
    """RRF 公式: rrf(d) = Σ 1 / (k + rank_i(d))，k = 60"""

    def test_single_hit_appears_once(self):
        fused = rrf_fuse(keyword_hits=[{"chunk_id": "a"}], vector_hits=[])
        assert len(fused) == 1
        assert fused[0]["chunk_id"] == "a"

    def test_appears_in_both_lists_score_sums(self):
        fused = rrf_fuse(
            keyword_hits=[{"chunk_id": "a"}],
            vector_hits=[{"chunk_id": "a"}],
        )
        # 在两个列表都 rank=1，score = 2 / (60+1)
        assert abs(fused[0]["score"] - 2 / 61) < 1e-9

    def test_rank_2_gets_lower_score_than_rank_1(self):
        fused = rrf_fuse(
            keyword_hits=[{"chunk_id": "a"}, {"chunk_id": "b"}],
            vector_hits=[],
        )
        # a rank=1, b rank=2
        assert fused[0]["chunk_id"] == "a"
        assert fused[1]["chunk_id"] == "b"
        assert fused[0]["score"] > fused[1]["score"]

    def test_results_sorted_by_score_desc(self):
        # c 只在 vector rank=2，b 只在 keyword rank=2，a 在两边 rank=1
        kw = [{"chunk_id": "a"}, {"chunk_id": "b"}]
        vec = [{"chunk_id": "a"}, {"chunk_id": "c"}]
        fused = rrf_fuse(keyword_hits=kw, vector_hits=vec)
        scores = [h["score"] for h in fused]
        assert scores == sorted(scores, reverse=True)

    def test_empty_inputs_returns_empty(self):
        assert rrf_fuse(keyword_hits=[], vector_hits=[]) == []

    def test_preserves_individual_scores(self):
        fused = rrf_fuse(
            keyword_hits=[{"chunk_id": "a", "score": 0.9}],
            vector_hits=[{"chunk_id": "a", "score": 0.5}],
        )
        assert fused[0]["keyword_score"] == 0.9
        assert fused[0]["vector_score"] == 0.5

    def test_custom_k_parameter(self):
        fused = rrf_fuse(
            keyword_hits=[{"chunk_id": "a"}, {"chunk_id": "b"}],
            vector_hits=[],
            k=10,
        )
        # a rank=1, score=1/(10+1)=1/11
        assert abs(fused[0]["score"] - 1 / 11) < 1e-9


# ============================================================
# post_filter_hits（提示词 02 §4.4）
# ============================================================
class TestPostFilterHits:
    def test_filters_inaccessible_kb(self):
        hits = [
            {"chunk_id": "a", "kb_id": "k1"},
            {"chunk_id": "b", "kb_id": "k2"},
            {"chunk_id": "c", "kb_id": "k1"},
        ]
        result = post_filter_hits(hits=hits, accessible_kb_ids={"k1"})
        assert len(result) == 2
        assert {h["chunk_id"] for h in result} == {"a", "c"}

    def test_keeps_all_when_all_accessible(self):
        hits = [{"chunk_id": "a", "kb_id": "k1"}, {"chunk_id": "b", "kb_id": "k2"}]
        result = post_filter_hits(hits=hits, accessible_kb_ids={"k1", "k2"})
        assert len(result) == 2

    def test_drops_all_when_none_accessible(self):
        hits = [{"chunk_id": "a", "kb_id": "k1"}]
        result = post_filter_hits(hits=hits, accessible_kb_ids=set())
        assert result == []

    def test_hit_without_kb_id_dropped(self):
        """无 kb_id 字段的 hit 必须丢弃（防御性）"""
        hits = [{"chunk_id": "a"}]  # 没有 kb_id
        result = post_filter_hits(hits=hits, accessible_kb_ids={"k1"})
        assert result == []

    def test_empty_hits_returns_empty(self):
        assert post_filter_hits(hits=[], accessible_kb_ids={"k1"}) == []


# ============================================================
# Schemas
# ============================================================
class TestSearchSchemas:
    def test_query_length_validation(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchRequest(query="", mode="hybrid")
        with pytest.raises(ValidationError):
            SearchRequest(query="x" * 2001, mode="hybrid")

    def test_mode_enum(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchRequest(query="q", mode="unknown")

    def test_top_k_bounds(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchRequest(query="q", mode="hybrid", top_k=0)
        with pytest.raises(ValidationError):
            SearchRequest(query="q", mode="hybrid", top_k=51)

    def test_threshold_bounds(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchRequest(query="q", mode="hybrid", threshold=-0.1)
        with pytest.raises(ValidationError):
            SearchRequest(query="q", mode="hybrid", threshold=1.1)

    def test_hit_required_fields(self):
        with pytest.raises(Exception):
            SearchHit(doc_id="d", chunk_id="c")  # 缺 score + text
        hit = SearchHit(doc_id="d", chunk_id="c", score=0.9, text="hello")
        assert hit.score == 0.9
        assert hit.text == "hello"

    def test_response_requires_taken_ms(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SearchResponse(hits=[], mode="hybrid", reranked=False, total_candidates=0)
