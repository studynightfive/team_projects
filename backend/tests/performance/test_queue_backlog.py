# 性能测试：队列积压
import pytest
pytestmark = pytest.mark.skip(reason="性能测试需手动执行")

class TestQueueBacklog:
    async def test_20_concurrent_uploads_processed(self): pass
    async def test_worker_recovery_after_stop(self): pass
