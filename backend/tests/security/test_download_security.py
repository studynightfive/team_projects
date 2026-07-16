# 安全测试：下载安全
# 方案第8.4节：任务和下载安全
# 验证导出文件下载的权限和有效期
import pytest

pytestmark = pytest.mark.skip(reason="export module not yet implemented")

class TestDownloadAuthorization:
    async def test_direct_storage_access_rejected(self, client): pass
    async def test_expired_link_rejected(self, client): pass
    async def test_other_user_link_rejected(self, client): pass
    async def test_url_not_guessable(self, client): pass
    async def test_token_not_in_url(self, client): pass
