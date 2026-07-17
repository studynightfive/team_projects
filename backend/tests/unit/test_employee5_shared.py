"""员工5 共享层单元测试

覆盖：
- text.py：token 估算 / 截断 / 上下文裁剪
- sse.py：SSE 事件格式化 / 心跳 / ID
"""

from __future__ import annotations

import json

from app.rag._shared.sse import format_keepalive, format_sse, new_message_id
from app.rag._shared.text import (
    estimate_tokens,
    fit_messages_to_budget,
    truncate_to_tokens,
)


# ============================================================
# text.py - token 估算（提示词 04 §4.5）
# ============================================================
class TestEstimateTokens:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_simple_ascii(self):
        # 100 chars / 1.0 = 100 tokens
        assert estimate_tokens("a" * 100) == 100

    def test_cjk_counts_each_char(self):
        # CJK 也是 1 char = 1 token（保守估计）
        text = "中文测试" * 10  # 40 chars
        assert estimate_tokens(text) == 40


class TestTruncateToTokens:
    def test_truncates_long_text(self):
        result = truncate_to_tokens("abcdefghij", max_tokens=3)
        assert result == "abc"

    def test_short_text_unchanged(self):
        assert truncate_to_tokens("abc", max_tokens=100) == "abc"

    def test_zero_max_returns_empty(self):
        assert truncate_to_tokens("anything", max_tokens=0) == ""

    def test_negative_max_returns_empty(self):
        assert truncate_to_tokens("anything", max_tokens=-1) == ""


class TestFitMessagesToBudget:
    """从最新到最旧贪心填充"""

    def test_empty_messages(self):
        assert fit_messages_to_budget([], max_tokens=100) == []

    def test_single_message_under_budget(self):
        msgs = [{"content": "hello world"}]
        result = fit_messages_to_budget(msgs, max_tokens=100)
        assert result == msgs

    def test_caps_at_budget_from_newest(self):
        # 5 条消息，每条 30 chars（约 30 tokens），budget = 60 tokens
        msgs = [{"content": "x" * 30, "i": i} for i in range(5)]
        result = fit_messages_to_budget(msgs, max_tokens=60)
        # 应保留最新的 2 条（30+30=60）
        assert len(result) == 2
        assert result[0]["i"] == 3
        assert result[1]["i"] == 4

    def test_empty_content_messages(self):
        msgs = [{"content": ""}, {"content": "abc"}, {"content": ""}]
        result = fit_messages_to_budget(msgs, max_tokens=100)
        # 都应保留（总 cost=3，远小于 budget）
        assert len(result) == 3

    def test_zero_cost_messages_kept(self):
        """content 缺失视为 0 cost，在 budget 内会被保留；不会触发预算耗尽 break"""
        msgs = [{"content": "x" * 1000}, {"no_content": True}, {"content": "y" * 5}]
        result = fit_messages_to_budget(msgs, max_tokens=100)
        # 从最新到最旧贪心: y5(cost=5, used=5) → no_content(cost=0, used=5) → x1000(cost=1000, 5+1000>100 and kept → break)
        # 因此保留 2 条（y5 + no_content）
        assert len(result) == 2
        assert result[1] == {"content": "y" * 5}
        assert result[0] == {"no_content": True}


# ============================================================
# sse.py - SSE 事件格式化（提示词 03 §4）
# ============================================================
class TestFormatSSE:
    def test_basic_event(self):
        out = format_sse(event="start", data={"event": "start", "id": 1})
        # 必须含 event: 与 data: 行
        assert "event: start" in out
        assert "data: " in out
        assert out.endswith("\n\n")  # SSE 事件以空行结束

    def test_data_is_json_string(self):
        out = format_sse(event="delta", data={"event": "delta", "text": "hi"})
        # 解析 data: 行（可能有 id 前缀和多个 data 行）
        data_line = [l for l in out.split("\n") if l.startswith("data: ")][0]
        payload = data_line[6:]
        obj = json.loads(payload)
        assert obj == {"event": "delta", "text": "hi"}

    def test_event_id_when_provided(self):
        out = format_sse(event="x", data={"y": 1}, event_id="evt-42")
        assert "id: evt-42" in out

    def test_no_id_line_when_none(self):
        out = format_sse(event="x", data={"y": 1})
        assert "id: " not in out

    def test_multiline_data_split(self):
        """raw string 含换行必须拆为多个 data: 行（SSE 协议要求）"""
        out = format_sse(event="x", data="line1\nline2")
        # 应有两行 data: line1 / data: line2
        data_lines = [l for l in out.split("\n") if l.startswith("data: ")]
        assert len(data_lines) == 2
        assert data_lines[0].endswith("line1")
        assert data_lines[1].endswith("line2")

    def test_string_data_passed_through(self):
        out = format_sse(event="raw", data="just a string")
        assert "data: just a string" in out

    def test_unicode_preserved(self):
        out = format_sse(event="x", data={"text": "中文测试"})
        assert "中文测试" in out


class TestFormatKeepalive:
    def test_is_sse_comment(self):
        out = format_keepalive()
        # SSE 心跳以 ":" 开头，被视为注释，客户端不会触发事件
        assert out.startswith(":")

    def test_ends_with_double_newline(self):
        out = format_keepalive()
        assert out.endswith("\n\n")


class TestNewMessageId:
    def test_returns_uuid_string(self):
        mid = new_message_id()
        import uuid

        # 能被 uuid.UUID 解析
        uuid.UUID(mid)

    def test_unique(self):
        ids = {new_message_id() for _ in range(100)}
        assert len(ids) == 100