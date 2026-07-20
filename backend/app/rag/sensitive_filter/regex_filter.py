"""Layer 1: 基于正则表达式的敏感词过滤

提供快速、确定性的敏感词匹配。适合精确匹配已知的敏感词和模式。
"""

from __future__ import annotations

import re
from typing import ClassVar


class RegexSensitiveFilter:
    """正则敏感词过滤器

    使用预定义的敏感词列表和正则模式进行匹配。
    支持中文和英文敏感词，可扩展。
    """

    # 敏感词列表 — 按类别组织
    SENSITIVE_WORDS: ClassVar[list[str]] = [
        # 政治敏感类
        "反动", "颠覆", "暴乱", "煽动", "颠覆国家政权",
        "分裂国家", "危害国家安全", "恐怖主义", "极端主义",
        # 违法犯罪类
        "黑客", "入侵", "破解", "盗取", "窃取",
        "洗钱", "诈骗", "非法集资", "传销",
        "sql注入", "xss攻击", "csrf", "ddos",
        # 暴力色情类
        "色情", "淫秽", "赌博", "毒品", "制毒",
        "枪支", "弹药", "爆炸物", "管制刀具",
        # 恶意破坏类
        "删除数据库", "删除所有数据", "格式化",
        "rm -rf", "drop table", "shutdown",
        # 隐私侵犯类
        "个人隐私", "窃听", "监控破解", "人肉搜索",
        "社工库", "拖库", "撞库",
    ]

    # 正则模式 — 用于匹配变体和组合
    SENSITIVE_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        # SQL 注入模式
        re.compile(r"(?:drop|alter|truncate)\s+(?:table|database)", re.IGNORECASE),
        re.compile(r"(?:insert\s+into|update\s+.*\s+set|delete\s+from).*(?:--|#|/\*)", re.IGNORECASE),
        re.compile(r"union\s+(?:all\s+)?select", re.IGNORECASE),
        re.compile(r"(?:or|and)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?", re.IGNORECASE),
        # XSS 模式
        re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE),
        re.compile(r"on(?:load|click|error|mouseover)\s*=", re.IGNORECASE),
        # 系统命令注入
        re.compile(r"(?:rm\s+-rf|del\s+/[fsq]|format\s+[cdefg]:)", re.IGNORECASE),
        re.compile(r"(?:/bin/(?:bash|sh|zsh)|cmd\.exe|powershell\.exe)", re.IGNORECASE),
        re.compile(r"`[^`]+`", re.IGNORECASE),
        # 路径遍历
        re.compile(r"(?:\.\./|\.\.\\){2,}"),
        # 敏感政治口号变体
        re.compile(r"(?:打倒|推翻|反抗|对抗).{0,10}(?:政府|国家|党|政权|体制)"),
    ]

    @classmethod
    def check(cls, text: str) -> tuple[bool, list[str]]:
        """检查文本是否包含敏感词

        Args:
            text: 待检查的文本

        Returns:
            tuple: (是否敏感, 匹配到的敏感词/模式列表)
        """
        matched: list[str] = []

        # 1. 精确匹配敏感词
        for word in cls.SENSITIVE_WORDS:
            if word.lower() in text.lower():
                matched.append(f"敏感词: {word}")

        # 2. 正则模式匹配
        for pattern in cls.SENSITIVE_PATTERNS:
            found = pattern.search(text)
            if found:
                matched.append(f"敏感模式: {found.group()[:50]}")

        return (len(matched) > 0, matched)


def check_regex(text: str) -> tuple[bool, list[str]]:
    """Layer 1 入口：正则敏感词检查

    便捷函数，可直接从 service 层调用。
    """
    return RegexSensitiveFilter.check(text)
