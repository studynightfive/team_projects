"""防止空测试和过期整文件 skip 再次制造虚假质量信号。"""

from __future__ import annotations

import ast
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent


def test_suite_has_no_placeholder_test_functions() -> None:
    placeholders: list[str] = []
    for path in TEST_ROOT.rglob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not node.name.startswith("test_"):
                continue
            executable = [
                statement
                for statement in node.body
                if not (
                    isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                )
            ]
            if len(executable) == 1 and isinstance(executable[0], ast.Pass):
                placeholders.append(f"{path.relative_to(TEST_ROOT)}::{node.name}")
    assert placeholders == [], "发现空测试：\n" + "\n".join(placeholders)


def test_suite_has_no_stale_not_implemented_skips() -> None:
    stale: list[str] = []
    for path in TEST_ROOT.rglob("test_*.py"):
        if path == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8").lower()
        if "skip" in text and ("not yet implemented" in text or "尚未实现" in text):
            stale.append(str(path.relative_to(TEST_ROOT)))
    assert stale == [], "发现过期的未实现 skip：\n" + "\n".join(stale)
