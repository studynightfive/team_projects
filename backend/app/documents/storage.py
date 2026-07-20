"""Local filesystem storage for original files, markdown packages and assets."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path

from pydantic import JsonValue, TypeAdapter

from app.common.config import Settings
from app.common.config import settings as app_settings

_UNSAFE_NAME = re.compile(r"[^\w.\u4e00-\u9fff\-]+", re.UNICODE)
_MANIFEST_ADAPTER = TypeAdapter(dict[str, JsonValue])


def sanitize_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1].strip()
    name = name.lstrip(".")
    cleaned = _UNSAFE_NAME.sub("_", name).strip("._")
    if not cleaned:
        cleaned = "unnamed"
    return cleaned[:200]


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class DocumentStorage:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else app_settings
        self.root = Path(self.settings.storage_root) / "documents"
        self.root.mkdir(parents=True, exist_ok=True)

    def document_dir(self, document_id: str) -> Path:
        path = self.root / str(document_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def original_dir(self, document_id: str) -> Path:
        path = self.document_dir(document_id) / "original"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def markdown_dir(self, document_id: str) -> Path:
        path = self.document_dir(document_id) / "markdown"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def assets_dir(self, document_id: str) -> Path:
        path = self.document_dir(document_id) / "assets"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def preview_dir(self, document_id: str) -> Path:
        path = self.document_dir(document_id) / "preview"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_original(self, document_id: str, filename: str, data: bytes) -> Path:
        safe = sanitize_filename(filename)
        target = self.original_dir(document_id) / safe
        target.write_bytes(data)
        return target

    def backup_document(self, document_id: str) -> Path:
        target = self._document_target(document_id)
        backup_root = self.root / ".upload-backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / uuid.uuid4().hex
        backup.mkdir()
        try:
            if target.exists():
                shutil.copytree(target, backup / "document")
        except Exception:
            shutil.rmtree(backup, ignore_errors=True)
            raise
        return backup

    def restore_document(self, document_id: str, backup: Path) -> None:
        target = self._document_target(document_id)
        self._validate_backup(backup)
        snapshot = backup / "document"
        if target.exists():
            shutil.rmtree(target)
        if snapshot.exists():
            shutil.move(str(snapshot), str(target))
        shutil.rmtree(backup)

    def discard_backup(self, backup: Path) -> None:
        self._validate_backup(backup)
        if backup.exists():
            shutil.rmtree(backup)

    def write_markdown_package(
        self,
        document_id: str,
        content_md: str,
        manifest: dict[str, JsonValue],
        assets: list[tuple[str, bytes]],
    ) -> tuple[Path, Path, list[Path]]:
        md_path = self.markdown_dir(document_id) / "content.md"
        md_path.write_text(content_md, encoding="utf-8")
        manifest_path = self.document_dir(document_id) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        asset_paths: list[Path] = []
        for name, blob in assets:
            safe = sanitize_filename(name)
            path = self.assets_dir(document_id) / safe
            path.write_bytes(blob)
            asset_paths.append(path)
        return md_path, manifest_path, asset_paths

    def read_markdown(self, document_id: str) -> str:
        return (self.markdown_dir(document_id) / "content.md").read_text(encoding="utf-8")

    def read_manifest(self, document_id: str) -> dict[str, JsonValue]:
        path = self.document_dir(document_id) / "manifest.json"
        if not path.exists():
            return {}
        return _MANIFEST_ADAPTER.validate_json(path.read_bytes())

    def resolve_asset(self, document_id: str, relative_path: str) -> Path:
        base = self.document_dir(document_id).resolve()
        candidate = (base / relative_path).resolve()
        if not candidate.is_relative_to(base):
            raise ValueError("path traversal blocked")
        return candidate

    def clear_derived(self, document_id: str) -> None:
        for name in ("markdown", "assets", "preview"):
            path = self.document_dir(document_id) / name
            if path.exists():
                shutil.rmtree(path)
        manifest = self.document_dir(document_id) / "manifest.json"
        if manifest.exists():
            manifest.unlink()

    def delete_document(self, document_id: str) -> None:
        target = self._document_target(document_id)
        if target.exists():
            shutil.rmtree(target)

    def _document_target(self, document_id: str) -> Path:
        root = self.root.resolve()
        target = (root / str(document_id)).resolve()
        if target.parent != root:
            raise ValueError("invalid document storage path")
        return target

    def _validate_backup(self, backup: Path) -> None:
        backup_root = (self.root / ".upload-backups").resolve()
        if backup.resolve().parent != backup_root:
            raise ValueError("invalid document backup path")
