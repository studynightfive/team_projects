"""将知识库权限与检索核心编译为当前 Python ABI 的原生扩展。"""

from __future__ import annotations

import os
import re
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, setup

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODULE_SOURCES = (
    ("app.knowledge.service", "app/knowledge/service.py"),
    ("app.rag._shared.permissions", "app/rag/_shared/permissions.py"),
    ("app.rag.search.service", "app/rag/search/service.py"),
    ("app.native.license_core", "app/native/license_core.pyx"),
)


def _license_public_key() -> str:
    """读取构建期公钥；公钥只编译进扩展，不写入 Python 运行时配置。"""

    value = os.getenv("NATIVE_LICENSE_PUBLIC_KEY_HEX", "").strip().lower()
    if value and re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise SystemExit("NATIVE_LICENSE_PUBLIC_KEY_HEX 必须是 64 位十六进制公钥")
    return value


def main() -> None:
    # build_ext --inplace 按当前目录定位包，固定到 backend 可同时支持 Docker 与本地构建。
    os.chdir(BACKEND_ROOT)
    extensions = [
        Extension(name, [str(BACKEND_ROOT / source)])
        for name, source in MODULE_SOURCES
    ]
    setup(
        name="knowledge-base-native-core",
        packages=[],
        ext_modules=cythonize(
            extensions,
            compiler_directives={
                "language_level": "3",
                "binding": True,
                "embedsignature": False,
            },
            compile_time_env={
                "LICENSE_PUBLIC_KEY_HEX": _license_public_key(),
            },
            build_dir=str(BACKEND_ROOT / "build" / "cython"),
        ),
        script_args=["build_ext", "--inplace"],
    )


if __name__ == "__main__":
    main()
