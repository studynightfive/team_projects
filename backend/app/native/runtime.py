"""原生核心加载与许可证执行边界。"""

from __future__ import annotations

from importlib import import_module
from importlib.machinery import EXTENSION_SUFFIXES
from importlib.util import find_spec
from pathlib import Path

PROTECTED_MODULES = (
    "app.knowledge.service",
    "app.rag._shared.permissions",
    "app.rag.search.service",
    "app.native.license_core",
)


def native_core_loaded() -> bool:
    """只检查模块来源是否为 CPython 扩展，不导入受保护业务模块。"""

    for module_name in PROTECTED_MODULES:
        spec = find_spec(module_name)
        origin = spec.origin if spec is not None else None
        if origin is None or not any(
            origin.endswith(suffix) for suffix in EXTENSION_SUFFIXES
        ):
            return False
    return True


def _native_license_is_valid(license_file: str) -> bool:
    # 动态导入避免 Python 类型层依赖扩展实现；跨边界仍只保留布尔结果。
    module = import_module("app.native.license_core")
    validator = getattr(module, "license_is_valid", None)
    return bool(callable(validator) and validator(license_file))


def enforce_native_core(
    *,
    required: bool,
    license_required: bool,
    license_file: str,
) -> None:
    """在服务启动前执行原生模块和许可证的故障关闭校验。"""

    if not required:
        return
    if not native_core_loaded():
        raise RuntimeError("知识库原生核心未加载，服务拒绝启动")
    if license_required and (
        not license_file.strip()
        or not Path(license_file).is_file()
        or not _native_license_is_valid(license_file)
    ):
        raise RuntimeError("知识库原生核心许可证无效，服务拒绝启动")
