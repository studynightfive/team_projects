"""Patch OpenAPI spec with sensitive-filter schemas and path.

Run via: uv run python scripts/patch_openapi_sensitive_filter.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    spec_path = PROJECT_ROOT / "docs" / "api" / "openapi.yaml"
    with open(spec_path, encoding="utf-8") as f:
        spec = json.load(f)

    schemas = spec["components"]["schemas"]

    # SensitiveCheckRequest
    schemas["SensitiveCheckRequest"] = {
        "properties": {
            "question": {
                "type": "string",
                "maxLength": 4000,
                "minLength": 1,
                "title": "Question",
                "description": "待检查的问题文本",
            }
        },
        "required": ["question"],
        "title": "SensitiveCheckRequest",
        "type": "object",
    }

    # SensitiveCheckResponse
    schemas["SensitiveCheckResponse"] = {
        "properties": {
            "passed": {
                "type": "boolean",
                "title": "Passed",
                "description": "是否通过检查",
            },
            "verdict": {
                "type": "string",
                "title": "Verdict",
                "description": "过滤判定: pass / regex / bert",
            },
            "reason": {
                "type": "string",
                "default": "",
                "title": "Reason",
                "description": "拦截原因（仅 blocked 时有值）",
            },
            "regex_matches": {
                "items": {"type": "string"},
                "type": "array",
                "title": "Regex Matches",
                "description": "Layer 1 正则匹配结果",
            },
            "bert_confidence": {
                "type": "number",
                "default": 0.0,
                "title": "Bert Confidence",
                "description": "Layer 2 BERT 置信度 (0.0-1.0)",
            },
            "bert_label": {
                "type": "string",
                "default": "",
                "title": "Bert Label",
                "description": "BERT 匹配的敏感意图标签",
            },
        },
        "required": ["passed", "verdict"],
        "title": "SensitiveCheckResponse",
        "type": "object",
    }

    # APIResponse[SensitiveCheckResponse]
    schemas["APIResponse_SensitiveCheckResponse_"] = {
        "properties": {
            "code": {"type": "integer", "title": "Code", "default": 0},
            "message": {
                "type": "string",
                "title": "Message",
                "default": "success",
            },
            "data": {
                "anyOf": [
                    {"$ref": "#/components/schemas/SensitiveCheckResponse"},
                    {"type": "null"},
                ],
                "title": "Data",
            },
            "request_id": {
                "type": "string",
                "title": "Request Id",
                "default": "",
            },
        },
        "title": "APIResponse[SensitiveCheckResponse]",
        "type": "object",
    }

    # Sort schemas alphabetically
    spec["components"]["schemas"] = {
        k: schemas[k] for k in sorted(schemas.keys(), key=str.lower)
    }

    # Insert /sensitive-check path after /retrieval-tests/runs/{run_id}
    new_path = {
        "post": {
            "tags": ["sensitive-filter"],
            "summary": "敏感词检查",
            "description": "对用户输入的问题进行两层敏感词过滤",
            "operationId": "sensitive_check_endpoint_api_v1_sensitive_check_post",
            "requestBody": {
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/SensitiveCheckRequest"
                        }
                    }
                },
                "required": True,
            },
            "responses": {
                "200": {
                    "description": "Successful Response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/APIResponse_SensitiveCheckResponse_"
                            }
                        }
                    },
                },
                "401": {
                    "description": "未登录、Token 无效或已过期",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/APIErrorResponse"
                            }
                        }
                    },
                },
                "403": {
                    "description": "已登录但权限不足",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/APIErrorResponse"
                            }
                        }
                    },
                },
                "422": {
                    "description": "请求参数错误",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/APIErrorResponse"
                            }
                        }
                    },
                },
            },
            "security": [{"BearerAuth": []}],
        }
    }

    paths = spec["paths"]
    new_paths = {}
    inserted = False
    for pk, pv in paths.items():
        new_paths[pk] = pv
        if pk == "/retrieval-tests/runs/{run_id}":
            new_paths["/sensitive-check"] = new_path
            inserted = True

    if not inserted:
        print("ERROR: insertion point /retrieval-tests/runs/{run_id} not found")
        sys.exit(1)

    spec["paths"] = new_paths

    # Verify $ref was written correctly
    result = json.dumps(spec, ensure_ascii=False, indent=2)
    if "$ref" not in result:
        print("ERROR: $ref missing from output!")
        sys.exit(1)

    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(result + "\n")

    print(f"Done. Wrote {len(result)} chars to {spec_path}")


if __name__ == "__main__":
    main()
