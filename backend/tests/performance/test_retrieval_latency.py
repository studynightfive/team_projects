# 性能测试：检索延迟
import pytest

pytestmark = pytest.mark.skip(reason="性能测试需手动执行")

class TestRetrievalLatency:
    async def test_retrieval_p95_latency_under_2s(self): pass
    async def test_retrieval_p95_latency_under_5s_10k_docs(self): pass
