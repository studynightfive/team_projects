import asyncio
import os

from app.models.providers.openai import build_provider


async def main() -> None:
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    base = os.environ.get("DASHSCOPE_BASE_URL", "")
    model = os.environ.get("QWEN_EMBEDDING_MODEL", "")
    dims = os.environ.get("QWEN_EMBEDDING_DIMENSIONS", "")
    print("model=", model, "dims=", dims, "base=", base, "key_set=", bool(key))
    if not key:
        print("result=MISSING_KEY")
        return
    p = build_provider("dashscope", base, key, timeout=30.0)
    try:
        vectors = await p.embed(model_name=model, inputs=["一线城市差旅住宿标准"])
        print("result=OK", "n=", len(vectors), "dim=", len(vectors[0]) if vectors else 0)
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        body = ""
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                body = resp.text[:240]
            except Exception:
                body = ""
        print("result=FAIL", "type=", type(exc).__name__, "status=", status, "body=", body)

asyncio.run(main())
