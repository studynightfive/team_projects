"""导出文件存储路径管理（提示词 05 §4.9）"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.common.config import settings


def root() -> Path:
    p = Path(settings.export_storage_root).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def task_dir(task_id: str) -> Path:
    d = root() / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def task_file_path(task_id: str, filename: str) -> str:
    """返回任务的最终文件路径，并防止路径穿越。"""
    safe_name = os.path.basename(filename)
    if safe_name != filename or ".." in filename:
        raise ValueError("非法文件名")
    return str(task_dir(task_id) / safe_name)


def delete_task_dir(task_id: str) -> None:
    """只删除导出根目录下的单个任务目录。"""
    export_root = root()
    candidate = (export_root / task_id).resolve()
    if candidate.parent != export_root:
        raise ValueError("非法任务目录")
    if candidate.exists():
        shutil.rmtree(candidate)
