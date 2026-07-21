"""OpenAI 兼容 Provider（含 DeepSeek / Ollama 兼容模式；提示词 01 §4.3）"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from collections.abc import AsyncIterator, Mapping, Sequence
from urllib.parse import urlsplit

import httpx
import structlog

from app.common.config import settings
from app.common.exceptions import ValidationException

logger = structlog.get_logger()


def validate_provider_base_url(provider_code: str, base_url: str) -> None:
    """校验模型服务地址；非本地 Ollama 不允许明文或内网目标。"""
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValidationException(message="Provider base_url 必须是有效的 HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValidationException(message="Provider base_url 不得包含凭据")
    if provider_code != "ollama" and parsed.scheme != "https":
        raise ValidationException(message="非 Ollama Provider 必须使用 HTTPS")
    hostname = parsed.hostname.lower().rstrip(".")
    if provider_code != "ollama" and (
        hostname == "localhost" or hostname.endswith(".localhost")
    ):
        raise ValidationException(message="仅 Ollama Provider 可访问本机地址")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not _address_is_allowed(provider_code, parsed.scheme, address):
        raise ValidationException(message="Provider base_url 不得指向私有或保留地址")


def _address_is_allowed(
    provider_code: str,
    scheme: str,
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    if address.is_link_local or address.is_multicast or address.is_unspecified:
        return False
    # Clash / 部分代理的 fake-ip 段；开发/测试环境放行，生产仍拒绝。
    if address in ipaddress.ip_network("198.18.0.0/15"):
        return settings.app_environment != "production"
    if provider_code != "ollama":
        return address.is_global
    if scheme == "http":
        return address.is_loopback or address.is_private
    return address.is_global or address.is_loopback or address.is_private


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field} contains a non-string key")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return list(value)


class OpenAICompatibleProvider:
    """OpenAI /chat/completions 与 /embeddings 与 /rerank 的 HTTP 适配。"""

    provider_code = "openai"

    def __init__(self, provider_code: str, base_url: str, api_key: str, timeout: float = 10.0):
        validate_provider_base_url(provider_code, base_url)
        self.provider_code = provider_code
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _client_create(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )

    async def _validate_resolved_host(self) -> None:
        """每次出站前解析全部地址，降低私网解析和 DNS 重绑定风险。"""
        if settings.testing:
            return
        parsed = urlsplit(self.base_url)
        hostname = parsed.hostname
        if hostname is None:
            raise ValidationException(message="Provider base_url 缺少主机名")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            records = await asyncio.get_running_loop().getaddrinfo(
                hostname,
                port,
                type=socket.SOCK_STREAM,
            )
        except (OSError, ValueError) as exc:
            raise ValidationException(message="Provider 主机名无法解析") from exc
        addresses = {
            ipaddress.ip_address(str(record[4][0]).split("%", maxsplit=1)[0])
            for record in records
        }
        if not addresses or any(
            not _address_is_allowed(self.provider_code, parsed.scheme, address)
            for address in addresses
        ):
            raise ValidationException(message="Provider 域名解析到不允许的网络地址")

    async def chat(
        self,
        *,
        model_name: str,
        messages: Sequence[Mapping[str, object]],
        temperature: float = 0.2,
        max_tokens: int | None = None,
        stream: bool = False,
        timeout: float | None = None,
    ) -> AsyncIterator[str] | str:
        await self._validate_resolved_host()
        payload = {
            "model": model_name,
            "messages": list(messages),
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if not stream:
            async with self._client_create() as client:
                r = await client.post("/chat/completions", json=payload)
                r.raise_for_status()
                raw_data: object = r.json()
                data = _mapping(raw_data, field="response")
                choices = _list(data.get("choices"), field="choices")
                if not choices:
                    raise ValueError("choices must not be empty")
                choice = _mapping(choices[0], field="choices[0]")
                message = _mapping(choice.get("message"), field="message")
                content = message.get("content")
                if not isinstance(content, str):
                    raise ValueError("message.content must be a string")
                return content

        async def gen() -> AsyncIterator[str]:
            async with self._client_create() as client:
                async with client.stream("POST", "/chat/completions", json=payload) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:].strip()
                            if chunk == "[DONE]":
                                return
                            try:
                                raw_obj: object = json.loads(chunk)
                                obj = _mapping(raw_obj, field="stream response")
                                choices = _list(obj.get("choices"), field="choices")
                                if not choices:
                                    continue
                                choice = _mapping(choices[0], field="choices[0]")
                                delta_obj = _mapping(choice.get("delta"), field="delta")
                                delta = delta_obj.get("content")
                                if isinstance(delta, str) and delta:
                                    yield delta
                            except (TypeError, ValueError):
                                continue

        return gen()

    async def embed(
        self,
        *,
        model_name: str,
        inputs: list[str],
        timeout: float | None = None,
    ) -> list[list[float]]:
        await self._validate_resolved_host()
        async with self._client_create() as client:
            r = await client.post("/embeddings", json={"model": model_name, "input": inputs})
            r.raise_for_status()
            raw_data: object = r.json()
            data = _mapping(raw_data, field="response")
            rows = _list(data.get("data"), field="data")
            embeddings: list[list[float]] = []
            for index, row_value in enumerate(rows):
                row = _mapping(row_value, field=f"data[{index}]")
                values = _list(row.get("embedding"), field=f"data[{index}].embedding")
                embedding: list[float] = []
                for value in values:
                    if isinstance(value, bool) or not isinstance(value, int | float):
                        raise ValueError("embedding values must be numbers")
                    embedding.append(float(value))
                embeddings.append(embedding)
            return embeddings

    async def rerank(
        self,
        *,
        model_name: str,
        query: str,
        documents: list[str],
        top_n: int = 10,
        timeout: float | None = None,
    ) -> list[dict[str, int | float]]:
        """Cohere 兼容 /rerank 端点。"""
        await self._validate_resolved_host()
        async with self._client_create() as client:
            r = await client.post(
                "/rerank",
                json={"model": model_name, "query": query, "documents": documents, "top_n": top_n},
            )
            r.raise_for_status()
            raw_data: object = r.json()
        data = _mapping(raw_data, field="response")
        rows = _list(data.get("results"), field="results")
        results: list[dict[str, int | float]] = []
        for position, row_value in enumerate(rows):
            row = _mapping(row_value, field=f"results[{position}]")
            index = row.get("index")
            score = row.get("relevance_score")
            if isinstance(index, bool) or not isinstance(index, int):
                raise ValueError("rerank index must be an integer")
            if isinstance(score, bool) or not isinstance(score, int | float):
                raise ValueError("rerank relevance_score must be a number")
            results.append({"index": index, "relevance_score": float(score)})
        return results

    async def test(
        self, *, model_name: str, api_key: str, base_url: str
    ) -> dict[str, object]:
        start = time.time()
        try:
            await self._validate_resolved_host()
            client = httpx.AsyncClient(
                base_url=base_url.rstrip("/"),
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=self.timeout,
            )
            try:
                r = await client.get("/models")
                latency_ms = int((time.time() - start) * 1000)
                if r.status_code == 200:
                    return {
                        "ok": True,
                        "latency_ms": latency_ms,
                        "model_info": {"reachable": True, "status_code": r.status_code},
                    }
                authentication_failed = r.status_code in (401, 403)
                return {
                    "ok": False,
                    "latency_ms": latency_ms,
                    "error_code": (
                        "authentication_failed"
                        if authentication_failed
                        else "provider_unreachable"
                    ),
                    "error_message": (
                        "模型服务认证失败"
                        if authentication_failed
                        else f"HTTP {r.status_code}"
                    ),
                }
            finally:
                await client.aclose()
        except Exception as exc:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "error_code": "network_error",
                "error_message": f"模型服务请求失败（{type(exc).__name__}）",
            }


def build_provider(
    provider_code: str, base_url: str, api_key: str, timeout: float = 10.0
) -> OpenAICompatibleProvider:
    """Provider 工厂：当前全部用 OpenAI 兼容实现（DeepSeek/Ollama 等同样适配）。"""
    if provider_code in ("openai", "deepseek", "ollama", "custom", "anthropic", "dashscope"):
        return OpenAICompatibleProvider(provider_code, base_url, api_key, timeout)
    raise ValueError(f"unsupported provider_code: {provider_code}")
