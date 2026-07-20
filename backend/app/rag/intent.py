"""意图识别：问答入口路由，避免无意义检索。

意图：
- knowledge_qa：需要知识库检索
- chitchat：寒暄/感谢等，直接短答
- clarification：问题过短或含糊，先澄清
- out_of_scope：明显与知识库无关
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings
from app.models import service as model_service
from app.models.providers.openai import build_provider
from app.models.security import decrypt_api_key

IntentLabel = Literal["knowledge_qa", "chitchat", "clarification", "out_of_scope"]

_CHITCHAT_RE = re.compile(
    r"^(你好|您好|嗨|hi|hello|hey|早上好|中午好|晚上好|谢谢|感谢|多谢|"
    r"再见|拜拜|bye|ok|好的|嗯+|哈哈+|在吗)[\s!！。.?？~～]*$",
    re.IGNORECASE,
)
_OUT_OF_SCOPE_HINTS = (
    "今天天气",
    "帮我写代码",
    "讲个笑话",
    "股市",
    "彩票",
)


@dataclass(frozen=True)
class IntentResult:
    intent: IntentLabel
    confidence: float
    reason: str
    source: Literal["rules", "llm"] = "rules"


def classify_intent_rules(question: str) -> IntentResult:
    q = question.strip()
    if len(q) < 2:
        return IntentResult("clarification", 0.9, "问题过短", "rules")
    if _CHITCHAT_RE.match(q):
        return IntentResult("chitchat", 0.95, "寒暄/礼貌用语", "rules")
    lower = q.lower()
    if any(h in q or h in lower for h in _OUT_OF_SCOPE_HINTS) and len(q) < 40:
        return IntentResult("out_of_scope", 0.7, "疑似知识库外闲聊", "rules")
    if len(q) < 4 and "?" not in q and "？" not in q:
        return IntentResult("clarification", 0.75, "表述含糊", "rules")
    return IntentResult("knowledge_qa", 0.8, "默认知识问答", "rules")


async def classify_intent(
    db: AsyncSession,
    question: str,
    *,
    model_id: str | None = None,
    use_llm: bool | None = None,
) -> IntentResult:
    """规则优先；可选 LLM 二次判定（失败则回退规则）。"""
    base = classify_intent_rules(question)
    enabled = settings.rag_intent_llm_enabled if use_llm is None else use_llm
    mid = model_id or settings.rag_intent_model_id
    if not enabled or not mid or base.intent == "chitchat":
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
        prompt = (
            "你是意图分类器。只输出 JSON："
            '{"intent":"knowledge_qa|chitchat|clarification|out_of_scope","confidence":0-1,"reason":"..."}。\n'
            f"用户问题：{question}"
        )
        raw = await p.chat(
            model_name=model.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=120,
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
        intent = data.get("intent")
        if intent not in {"knowledge_qa", "chitchat", "clarification", "out_of_scope"}:
            return base
        conf = float(data.get("confidence") or 0.6)
        return IntentResult(intent, conf, str(data.get("reason") or "llm"), "llm")
    except Exception:
        return base


def intent_direct_reply(intent: IntentLabel) -> str | None:
    """无需检索时可直接回复的文案；需要检索时返回 None。"""
    if intent == "chitchat":
        return "你好，我是知识库助手。可以直接提问文档相关问题，我会基于知识库检索后回答。"
    if intent == "clarification":
        return "你的问题稍微有些简短。可以补充一下想查的主题、文档或具体条件吗？"
    if intent == "out_of_scope":
        return "这个问题看起来不在当前知识库范围内。请换一个与文档/业务相关的问题试试。"
    return None
