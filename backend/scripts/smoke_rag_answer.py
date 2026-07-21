import asyncio

from httpx import AsyncClient


async def main() -> None:
    async with AsyncClient(base_url="http://127.0.0.1:8000", timeout=60.0) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "adminadmin12"},
        )
        login.raise_for_status()
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        kbs = await client.get("/api/v1/knowledge-bases", headers=headers)
        kb_id = kbs.json()["data"]["items"][0]["id"]
        body = {
            "query": "一线城市差旅住宿标准是多少？",
            "mode": "hybrid",
            "kb_id": kb_id,
            "top_k": 8,
            "threshold": 0.0,
            "rerank": False,
        }
        r1 = await client.post("/api/v1/retrieval/answer", headers=headers, json=body)
        print("status", r1.status_code)
        print("body", r1.text[:500])
        payload = r1.json()
        d1 = payload.get("data") or {}
        print(
            "first",
            "hits",
            len(d1.get("hits") or []),
            "generated",
            d1.get("generated"),
            "cache",
            d1.get("from_cache"),
            "took",
            d1.get("took_ms"),
            "code",
            payload.get("code"),
            "message",
            payload.get("message"),
        )
        if d1.get("hits"):
            print("hit0", d1["hits"][0].get("doc_title"), d1["hits"][0].get("score"))
        print("answer", (d1.get("answer") or "")[:160])
        r2 = await client.post("/api/v1/retrieval/answer", headers=headers, json=body)
        print("status2", r2.status_code)
        payload2 = r2.json()
        d2 = payload2.get("data") or {}
        print(
            "second",
            "hits",
            len(d2.get("hits") or []),
            "cache",
            d2.get("from_cache"),
            "took",
            d2.get("took_ms"),
            "code",
            payload2.get("code"),
            "message",
            payload2.get("message"),
        )


if __name__ == "__main__":
    asyncio.run(main())
