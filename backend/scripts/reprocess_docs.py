import asyncio
import time

from httpx import AsyncClient


async def main() -> None:
    async with AsyncClient(base_url="http://127.0.0.1:8000", timeout=120.0) as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "adminadmin12"},
        )
        login.raise_for_status()
        token = login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        docs = [
            "6fa694fe-93d7-4850-b246-29eddd8a1fb1",
            "7a7e270f-db3a-400b-bf69-28da4878a8ab",
            "b93ccada-aeba-4ccc-9448-d5a0014f8281",
            "58307ea7-878b-4aea-8b91-ce0f06f6a145",
        ]
        for doc_id in docs:
            resp = await client.post(
                f"/api/v1/documents/{doc_id}/reprocess",
                headers=headers,
                json={},
            )
            print("reprocess", doc_id, resp.status_code, resp.json().get("code"), resp.json().get("message"))

        for round_idx in range(24):
            await asyncio.sleep(5)
            # check via SQL is outside; just wait for worker
            print("waited", (round_idx + 1) * 5, "s")


if __name__ == "__main__":
    asyncio.run(main())
