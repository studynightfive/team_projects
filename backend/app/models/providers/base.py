"""Provider 抽象（提示词 01 §4.3）"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProviderBase(Protocol):
    provider_code: str

    async def chat(
        self,
        *,
        model_name: str,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        stream: bool = False,
        timeout: float = 10.0,
    ) -> AsyncIterator[str] | str: ...

    async def embed(
        self,
        *,
        model_name: str,
        inputs: list[str],
        timeout: float = 10.0,
    ) -> list[list[float]]: ...

    async def rerank(
        self,
        *,
        model_name: str,
        query: str,
        documents: list[str],
        top_n: int = 10,
        timeout: float = 10.0,
    ) -> list[dict]: ...

    async def test(self, *, model_name: str, api_key: str, base_url: str) -> dict: ...
