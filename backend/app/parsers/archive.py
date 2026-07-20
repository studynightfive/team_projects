"""压缩容器文档的资源边界预检。"""

from __future__ import annotations

import zipfile
from pathlib import Path, PurePosixPath

from app.common.config import settings
from app.common.exceptions import AppException
from app.common.schemas import ErrorCode

ZIP_DOCUMENT_EXTENSIONS = frozenset(
    {".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp", ".epub"}
)


def validate_zip_container(source_path: str) -> None:
    """在第三方解析器解压前限制条目数、体积和压缩比。"""
    path = Path(source_path)
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > settings.archive_max_entries:
                raise _unsafe_archive("压缩容器条目过多")

            total_uncompressed = 0
            for entry in entries:
                normalized_name = entry.filename.replace("\\", "/")
                archive_path = PurePosixPath(normalized_name)
                if archive_path.is_absolute() or ".." in archive_path.parts:
                    raise _unsafe_archive("压缩容器包含非法路径")
                if entry.flag_bits & 0x1:
                    raise _unsafe_archive("不支持加密压缩容器")
                if entry.file_size > settings.archive_max_entry_bytes:
                    raise _unsafe_archive("压缩容器单个条目过大")

                total_uncompressed += entry.file_size
                if total_uncompressed > settings.archive_max_uncompressed_bytes:
                    raise _unsafe_archive("压缩容器解压后总量过大")
                if entry.file_size > 0:
                    if entry.compress_size <= 0:
                        raise _unsafe_archive("压缩容器压缩比异常")
                    ratio = entry.file_size / entry.compress_size
                    if ratio > settings.archive_max_compression_ratio:
                        raise _unsafe_archive("压缩容器压缩比异常")
    except (OSError, zipfile.BadZipFile) as exc:
        raise _unsafe_archive("压缩容器损坏或格式无效") from exc


def _unsafe_archive(message: str) -> AppException:
    return AppException(
        code=ErrorCode.UPLOAD_INVALID,
        message=message,
        status_code=422,
    )
