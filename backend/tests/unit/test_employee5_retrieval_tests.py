"""员工5 提示词 06 - 命中率测试单元测试

覆盖：
- 6 个指标函数（hit_rate / MRR / NDCG@K / Recall@K / Precision@K / MAP@K）
- 边界条件（k=0、零除、空集、超出范围）
- config_hash 可复现性
"""

from __future__ import annotations

import pytest

from app.rag.tests.all import (
    RetrievalTestConfig,
    _aggregate_metrics,
    _average_precision_at_k,
    _hit,
    _ndg_at_k,
    _precision_at_k,
    _recall_at_k,
    _reciprocal_rank,
    _hash_config,
)


class TestHitIndicator:
    """hit: 至少一个 retrieved chunk 在 relevant 集合中"""

    def test_hit_when_any_match(self):
        assert _hit(["a", "b"], {"b", "c"}) is True

    def test_no_hit_when_no_match(self):
        assert _hit(["a", "b"], {"c", "d"}) is False

    def test_empty_retrieved(self):
        assert _hit([], {"a"}) is False

    def test_empty_relevant(self):
        assert _hit(["a"], set()) is False


class TestReciprocalRank:
    """MRR 单条：第一个相关 chunk 的 1/rank"""

    def test_first_match_score_is_1(self):
        assert _reciprocal_rank(["a", "b"], {"a"}) == 1.0

    def test_second_match_score_is_half(self):
        assert _reciprocal_rank(["a", "b"], {"b"}) == 0.5

    def test_third_match_score_is_third(self):
        assert _reciprocal_rank(["a", "b", "c"], {"c"}) == 1 / 3

    def test_no_match_returns_zero(self):
        assert _reciprocal_rank(["a", "b"], {"c"}) == 0.0

    def test_empty_returns_zero(self):
        assert _reciprocal_rank([], {"a"}) == 0.0


class TestNDCGAtK:
    """NDCG@K：DCG / IDCG，[0, 1]"""

    def test_perfect_ranking(self):
        # relevant 在前 k 个全中，NDCG=1
        assert _ndg_at_k(["a", "b", "c"], {"a", "b"}, k=2) == 1.0

    def test_zero_when_no_relevant(self):
        assert _ndg_at_k(["a", "b"], set(), k=5) == 0.0

    def test_zero_when_no_hits(self):
        assert _ndg_at_k(["a", "b"], {"c"}, k=5) == 0.0

    def test_partial_ranking(self):
        # 1 hit in 2 slot, k=2, relevant size 1
        # DCG = 1/log2(2) = 1, IDCG = 1, NDCG = 1
        assert _ndg_at_k(["a", "b"], {"a"}, k=2) == 1.0

    def test_k_zero_returns_zero(self):
        assert _ndg_at_k(["a"], {"a"}, k=0) == 0.0

    def test_score_in_zero_one_range(self):
        score = _ndg_at_k(["a", "b", "c", "d"], {"b", "d"}, k=4)
        assert 0.0 <= score <= 1.0


class TestRecallAtK:
    """Recall@K = |retrieved[:k] ∩ relevant| / |relevant|"""

    def test_full_recall(self):
        assert _recall_at_k(["a", "b", "c"], {"a"}, k=3) == 1.0

    def test_partial_recall(self):
        # 2/3 relevant 在 top 3
        assert _recall_at_k(["a", "b", "c"], {"a", "b", "x"}, k=3) == 2 / 3

    def test_empty_relevant_returns_zero(self):
        """分母为 0，按定义返回 0（避免 ZeroDivisionError）"""
        assert _recall_at_k(["a"], set(), k=5) == 0.0

    def test_k_smaller_than_relevant(self):
        # top 1 只命中 a，relevant {a, b, c} → 1/3
        assert _recall_at_k(["a", "b"], {"a", "b", "c"}, k=1) == 1 / 3


class TestPrecisionAtK:
    """Precision@K = |retrieved[:k] ∩ relevant| / k"""

    def test_full_precision(self):
        assert _precision_at_k(["a", "b"], {"a", "b"}, k=2) == 1.0

    def test_half_precision(self):
        assert _precision_at_k(["a", "b"], {"a"}, k=2) == 0.5

    def test_zero_precision(self):
        assert _precision_at_k(["x", "y"], {"a"}, k=2) == 0.0

    def test_k_zero_returns_zero(self):
        """分母为 0，返回 0（避免 ZeroDivisionError）"""
        assert _precision_at_k(["a"], {"a"}, k=0) == 0.0


class TestAveragePrecisionAtK:
    """MAP@K 单条：AP = Σ (hits/i) / |relevant|"""

    def test_perfect_ordering(self):
        # relevant 全在 top，hits / i 加和 / |relevant|
        # hits=[1, 2], precision at each hit = 1/i
        # AP = (1/1 + 2/2) / 2 = 2/2 = 1.0
        assert _average_precision_at_k(["a", "b"], {"a", "b"}, k=2) == 1.0

    def test_partial_relevant(self):
        # retrieved=[a, x, b], relevant={a, b}
        # precision@1=1/1=1.0, precision@3=2/3
        # AP = (1.0 + 2/3) / 2 = (5/3)/2 = 5/6
        assert abs(_average_precision_at_k(["a", "x", "b"], {"a", "b"}, k=3) - 5 / 6) < 1e-9

    def test_empty_relevant_returns_zero(self):
        assert _average_precision_at_k(["a"], set(), k=3) == 0.0


class TestAggregateMetrics:
    def test_aggregates_all_six(self):
        from app.rag.tests.all import PerQueryResult, RetrievalTestMetrics

        per_query = [
            PerQueryResult(
                query="q1", relevant_chunk_ids=["a"], retrieved_chunk_ids=["a"],
                hit=True, reciprocal_rank=1.0, ndcg=1.0,
                recall=1.0, precision=1.0, latency_ms=10,
            ),
            PerQueryResult(
                query="q2", relevant_chunk_ids=["a"], retrieved_chunk_ids=["b"],
                hit=False, reciprocal_rank=0.0, ndcg=0.0,
                recall=0.0, precision=0.0, latency_ms=10,
            ),
        ]
        m = _aggregate_metrics(per_query)
        assert isinstance(m, RetrievalTestMetrics)
        assert m.hit_rate == 0.5
        assert m.mrr == 0.5
        assert m.ndcg_at_k == 0.5
        assert m.recall_at_k == 0.5
        assert m.precision_at_k == 0.5

    def test_aggregates_empty_returns_zero(self):
        from app.rag.tests.all import RetrievalTestMetrics

        m = _aggregate_metrics([])
        assert m.hit_rate == 0.0
        assert m.mrr == 0.0
        assert m.ndcg_at_k == 0.0


class TestConfigHashReproducibility:
    """config_hash：相同 config 必产生相同 hash（提示词 06 §一 可复现）"""

    def test_same_config_same_hash(self):
        c = RetrievalTestConfig(mode="hybrid", top_k=10, embedding_model_id="m1")
        assert _hash_config(c) == _hash_config(c)

    def test_different_mode_different_hash(self):
        c1 = RetrievalTestConfig(mode="hybrid", top_k=10, embedding_model_id="m1")
        c2 = RetrievalTestConfig(mode="vector", top_k=10, embedding_model_id="m1")
        assert _hash_config(c1) != _hash_config(c2)

    def test_different_top_k_different_hash(self):
        c1 = RetrievalTestConfig(mode="hybrid", top_k=10, embedding_model_id="m1")
        c2 = RetrievalTestConfig(mode="hybrid", top_k=20, embedding_model_id="m1")
        assert _hash_config(c1) != _hash_config(c2)

    def test_different_model_different_hash(self):
        c1 = RetrievalTestConfig(mode="hybrid", top_k=10, embedding_model_id="m1")
        c2 = RetrievalTestConfig(mode="hybrid", top_k=10, embedding_model_id="m2")
        assert _hash_config(c1) != _hash_config(c2)

    def test_hash_is_16_chars(self):
        c = RetrievalTestConfig(mode="hybrid", top_k=10, embedding_model_id="m1")
        h = _hash_config(c)
        assert len(h) == 16