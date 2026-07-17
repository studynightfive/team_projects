"""OpenAI 兼容 Provider（含 DeepSeek / Ollama 兼容模式；提示词 01 §4.3）"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx
import structlog

logger = structlog.get_logger()


class OpenAICompatibleProvider:
    """OpenAI /chat/completions 与 /embeddings 与 /rerank 的 HTTP 适配。"""

    provider_code = "openai"

    def __init__(self, provider_code: str, base_url: str, api_key: str, timeout: float = 10.0):
        self.provider_code = provider_code
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _client_get(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        return self._client

    async def chat(
        self,
        *,
        model_name: str,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        stream: bool = False,
        timeout: float | None = None,
    ) -> AsyncIterator[str] | str:
        client = await self._client_get()
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if not stream:
            r = await client.post("/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

        async def gen() -> AsyncIterator[str]:
            async with client.stream("POST", "/chat/completions", json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:].strip()
                        if chunk == "[DONE]":
                            return
                        try:
                            obj = json.loads(chunk)
                            delta = obj["choices"][0]["delta"].get("content")
                            if delta:
                                yield delta
                        except Exception:
                            continue

        return gen()

    async def embed(
        self,
        *,
        model_name: str,
        inputs: list[str],
        timeout: float | None = None,
    ) -> list[list[float]]:
        client = await self._client_get()
        r = await client.post("/embeddings", json={"model": model_name, "input": inputs})
        r.raise_for_status()
        return [item["embedding"] for item in r.json()["data"]]

    async def rerank(
        self,
        *,
        model_name: str,
        query: str,
        documents: list[str],
        top_n: int = 10,
        timeout: float | None = None,
    ) -> list[dict]:
        """Cohere 兼容 /rerank 端点。"""
        client = await self._client_get()
        r = await client.post(
            "/rerank",
            json={"model": model_name, "query": query, "documents": documents, "top_n": top_n},
        )
        r.raise_for_status()
        data = r.json()
        return [
            {"index": item["index"], "relevance_score": item["relevance_score"]}
            for item in data.get("results", [])
        ]

    async def test(self, *, model_name: str, api_key: str, base_url: str) -> dict:
        start = time.time()
        try:
            client = httpx.AsyncClient(
                base_url=base_url.rstrip("/"),
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=self.timeout,
            )
            try:
                r = await client.get("/models")
                latency_ms = int((time.time() - start) * 1000)
                if r.status_code in (200, 401):
                    return {
                        "ok": True,
                        "latency_ms": latency_ms,
                        "model_info": {"reachable": True, "status_code": r.status_code},
                    }
                return {
                    "ok": False,
                    "latency_ms": latency_ms,
                    "error_code": "provider_unreachable",
                    "error_message": f"HTTP {r.status_code}",
                }
            finally:
                await client.aclose()
        except Exception as exc:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "error_code": "network_error",
                "error_message": str(exc)[:200],
            }


def build_provider(provider_code: str, base_url: str, api_key: str, timeout: float = 10.0):
    """Provider 工厂：当前全部用 OpenAI 兼容实现（DeepSeek/Ollama 等同样适配）。"""
    if provider_code in ("openai", "deepseek", "ollama", "custom", "anthropic"):
        return OpenAICompatibleProvider(provider_code, base_url, api_key, timeout)
    raise ValueError(f"unsupported provider_code: {provider_code}")
