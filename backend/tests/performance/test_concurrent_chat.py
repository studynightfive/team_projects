# 性能测试：并发问答
import pytest

pytestmark = pytest.mark.skip(reason="性能测试需手动执行")

class TestConcurrentChat:
    async def test_10_concurrent_sse_requests(self): pass
    async def test_50_concurrent_sse_requests(self): pass
