# 性能测试：大文件处理
# 不要求每次 CI 运行，可手动或定期执行
import pytest
pytestmark = pytest.mark.skip(reason="性能测试需手动执行，使用 pytest --run-perf 标志")

class TestLargeFileProcessing:
    async def test_50mb_pdf_processing(self): pass
    async def test_100mb_docx_processing(self): pass
