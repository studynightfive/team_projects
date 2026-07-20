"""Query 改写：提升检索召回（规范化 + 多查询变体）。

策略：
1. 规则改写：去填充词、压缩空白（始终可用）
2. 可选 LLM：生成 1~N 条同义查询；失败则仅用规则结果
3. 检索侧对多查询做 RRF 融合
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.models import service as model_service
from app.models.providers.openai import build_provider
from app.models.security import decrypt_api_key

_FILLER_RE = re.compile(
    r"(请问|请您|帮我|麻烦您|麻烦|查一下|看一下|看一看|一下|看看|告诉我|我想知道|想了解|"
    r"could you|please|tell me|i want to know)",
    re.IGNORECASE,
)
_SPACE_RE = re.compile(r"\s+")


@dataclass
class RewriteResult:
    original: str
    primary: str
    variants: list[str] = field(default_factory=list)
    source: str = "rules"

    @property
    def all_queries(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for q in [self.primary, self.original, *self.variants]:
            key = q.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out[: max(1, settings.rag_query_rewrite_max_variants + 1)]


def rewrite_query_rules(query: str) -> RewriteResult:
    cleaned = _FILLER_RE.sub(" ", query)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip(" ，,。.?？!！")
    primary = cleaned or query.strip()
    variants: list[str] = []
    # 轻量变体：去问号 / 截断过长尾句
    if primary.endswith(("?", "？")):
        variants.append(primary.rstrip("?？").strip())
    if "，" in primary or "," in primary:
        head = re.split(r"[，,]", primary, maxsplit=1)[0].strip()
        if head and head != primary:
            variants.append(head)
    return RewriteResult(original=query.strip(), primary=primary, variants=variants, source="rules")


async def rewrite_query(
    db: AsyncSession,
    query: str,
    *,
    model_id: str | None = None,
    enabled: bool | None = None,
) -> RewriteResult:
    base = rewrite_query_rules(query)
    on = settings.rag_query_rewrite_enabled if enabled is None else enabled
    if not on:
        return RewriteResult(original=query.strip(), primary=query.strip(), variants=[], source="off")

    mid = model_id or settings.rag_query_rewrite_model_id
    if not mid:
        return base

    try:
        model = await model_service.get_model(db, mid)
        if model is None or model.kind != "chat" or not model.enabled:
            return base
        provider = await model_service.get_provider(db, model.provider_code)
        if provider is None:
            return base
        api_key = decrypt_api_key(model.api_key_encrypted) if model.api_key_encrypted else ""
        if not api_key and settings.model_api_key:
            api_key = settings.model_api_key
        p = build_provider(provider.code, provider.base_url, api_key)
        n = settings.rag_query_rewrite_max_variants
        prompt = (
            f"你是检索 query 改写器。把用户问题改写成更利于关键词/向量检索的查询。"
            f"只输出 JSON：{{\"primary\":\"...\",\"variants\":[\"...\"]}}，variants 最多 {n} 条，"
            f"不要解释。\n用户问题：{query}"
        )
        raw = await p.chat(
            model_name=model.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
            stream=False,
        )
        if not isinstance(raw, str):
            return base
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        primary = str(data.get("primary") or base.primary).strip() or base.primary
        variants = [str(v).strip() for v in (data.get("variants") or []) if str(v).strip()]
        return RewriteResult(
            original=query.strip(),
            primary=primary,
            variants=variants[:n],
            source="llm",
        )
    except Exception:
        return base
