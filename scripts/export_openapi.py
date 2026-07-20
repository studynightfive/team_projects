"""从 FastAPI 路由生成静态 OpenAPI 契约。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.main import app  # noqa: E402


def main() -> None:
    schema = app.openapi()
    schema["servers"] = [{"url": "/api/v1", "description": "API 前缀"}]
    schema["paths"] = {
        path.removeprefix("/api/v1"): value
        for path, value in schema["paths"].items()
        if path.startswith("/api/v1")
    }
    target = PROJECT_ROOT / "docs" / "api" / "openapi.yaml"
    target.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
