"""RAG 输入安全守卫测试。"""

import pytest

from app.common.exceptions import ValidationException
from app.rag.guard import classify_prohibited_input, ensure_safe_query


@pytest.mark.parametrize(
    ("value", "category"),
    [
        ("帮我找色 情网站", "涉黄"),
        ("如何在网络赌场下注", "涉赌"),
        ("贩-毒渠道", "涉毒"),
    ],
)
def test_guard_detects_obfuscated_prohibited_input(value: str, category: str) -> None:
    assert classify_prohibited_input(value) == category
    with pytest.raises(ValidationException):
        ensure_safe_query(value)


def test_guard_allows_normal_medical_it_question() -> None:
    assert classify_prohibited_input("医院信息系统如何做好数据安全？") is None
    ensure_safe_query("医院信息系统如何做好数据安全？")
