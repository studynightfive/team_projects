# 集成测试：导出到下载流程
# 验证从导出任务创建到文件下载的完整链路
import pytest

pytestmark = pytest.mark.skip(reason="export module not yet implemented")

class TestExportToDownload:
    async def test_create_export_then_download(self, client, user_headers): pass
    async def test_export_file_content_matches_selection(self, client, user_headers): pass
    async def test_other_user_cannot_download_export(self, client): pass
    async def test_expired_export_cannot_download(self, client): pass
