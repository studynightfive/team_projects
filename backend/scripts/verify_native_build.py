"""校验运行镜像只保留受保护模块的原生扩展。"""

from __future__ import annotations

from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_PATHS = (
    BACKEND_ROOT / "app/knowledge/service",
    BACKEND_ROOT / "app/rag/_shared/permissions",
    BACKEND_ROOT / "app/rag/search/service",
    BACKEND_ROOT / "app/native/license_core",
)


def main() -> None:
    failures: list[str] = []
    for stem in PROTECTED_PATHS:
        extensions = [
            stem.with_name(f"{stem.name}{suffix}")
            for suffix in EXTENSION_SUFFIXES
        ]
        if not any(path.is_file() for path in extensions):
            failures.append(f"{stem}: 缺少原生扩展")
        if stem.with_suffix(".py").exists() or stem.with_suffix(".pyx").exists():
            failures.append(f"{stem}: 运行镜像仍包含源文件")
    if failures:
        raise SystemExit("\n".join(failures))
    print("原生核心镜像校验通过")


if __name__ == "__main__":
    main()
