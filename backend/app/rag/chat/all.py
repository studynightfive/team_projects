"""流式问答（提示词 03）—— schemas + service + api 单文件版

SSE 事件序列：start → delta* → citation* → done | error
服务端真正取消模型调用；引用经 post_filter 权限保护；answer_versions 保留。
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.common.config import settings
from app.common.database import get_db
from app.common.models import User
from app.models import service as model_service
from app.models.providers.openai import build_provider
from app.models.security import decrypt_api_key
from app.rag._shared.permissions import (
    get_user_accessible_kb_ids,
    new_request_id,
    post_filter_hits,
)
from app.rag._shared.sse import format_keepalive, format_sse, new_message_id
from app.rag.conversations.all import (
    Conversation,
    Message,
    regenerate_answer,
)
from app.rag.search.service import search as search_rag

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ============================================================
# Schemas
# ============================================================
class ChatStreamRequest(BaseModel):
    conversation_id: str | None = None
    kb_id: str
    question: str = Field(min_length=1, max_length=4000)
    chat_model_id: str
    embedding_model_id: str
    rerank_model_id: str | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    metadata_filter: dict[str, Any] | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    parent_message_id: str | None = None  # 重新生成时指向原 assistant 消息


# ============================================================
# 检索上下文拼装（提示词 03 §5.6 + 引用权限）
# ============================================================
async def _retrieve_context(
    db: AsyncSession,
    *,
    user: User,
    req: ChatStreamRequest,
) -> list[dict]:
    search_resp = await search_rag(
        db,
        user=user,
        req=type(
            "R",
            (),
            {
                "query": req.question,
                "mode": "hybrid",
                "kb_id": req.kb_id,
                "top_k": req.top_k,
                "threshold": 0.0,
                "metadata_filter": req.metadata_filter,
                "rerank": bool(req.rerank_model_id),
                "rerank_model_id": req.rerank_model_id,
                "embedding_model_id": req.embedding_model_id,
            },
        )(),
    )
    # 二次权限过滤（即使 search 内已过滤）
    hits_dicts = [h.model_dump() for h in search_resp.hits]
    accessible = await get_user_accessible_kb_ids(db, user)
    safe = post_filter_hits(hits=hits_dicts, accessible_kb_ids=accessible)
    return safe


def _build_prompt(question: str, contexts: list[dict]) -> list[dict]:
    """仅基于 context 回答；明示未引用。"""
    if not contexts:
        context_text = "（暂无检索结果）"
    else:
        context_text = "\n\n---\n\n".join(
            f"[{i + 1}] doc={c.get('doc_id')} chunk={c.get('chunk_id')} page={c.get('page')}\n{c.get('text', '')}"  # noqa: E501
            for i, c in enumerate(contexts)
        )
    system = (
        "你是一名严谨的问答助手。只能基于给定的 context 回答问题；"
        "若 context 不包含答案，必须回答“未在文档中找到相关引用”。\n\n"
        f"## Context\n{context_text}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": question}]


# ============================================================
# SSE 事件生成
# ============================================================
async def _chat_stream(
    db: AsyncSession,
    *,
    user: User,
    req: ChatStreamRequest,
) -> AsyncIterator[str]:
    request_id = new_request_id()
    conversation_id = req.conversation_id or str(uuid.uuid4())
    message_id = new_message_id()

    # start 事件
    yield format_sse(
        event="start",
        data={
            "event": "start",
            "request_id": request_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
        },
    )

    # 1. 创建/获取会话与消息
    if req.conversation_id is None:
        conv = Conversation(user_id=user.id, kb_id=req.kb_id, title="")
        db.add(conv)
        await db.flush()
        conversation_id = conv.id
        # 把首条 user 消息落库
        user_msg = Message(conversation_id=conversation_id, role="user", content=req.question)
        db.add(user_msg)

    # 2. 处理重新生成
    if req.parent_message_id:
        assistant_msg = await regenerate_answer(db, parent_message_id=req.parent_message_id)
        message_id = assistant_msg.id
    else:
        assistant_msg = Message(conversation_id=conversation_id, role="assistant", content="")
        db.add(assistant_msg)
        await db.flush()
        message_id = assistant_msg.id

    # 3. 检索 + 拼 prompt
    try:
        contexts = await _retrieve_context(db, user=user, req=req)
    except Exception as exc:
        yield format_sse(
            event="error",
            data={
                "event": "error",
                "code": "retrieval_failed",
                "message": str(exc)[:200],
                "request_id": request_id,
                "retryable": True,
            },
        )
        assistant_msg.finish_reason = "error"
        await db.commit()
        return

    # 4. 发送 citations（受 post_filter 保护）
    citations_payload = []
    for c in contexts:
        evt = {
            "event": "citation",
            "doc_id": c.get("doc_id"),
            "chunk_id": c.get("chunk_id"),
            "doc_title": c.get("doc_title"),
            "page": c.get("page"),
            "score": c.get("score"),
            "text": c.get("text"),
            "position": c.get("position"),
        }
        citations_payload.append(evt)
        yield format_sse(event="citation", data=evt)

    messages = _build_prompt(req.question, contexts)

    # 5. 调模型流式
    chat_model = await model_service.get_model(db, req.chat_model_id)
    if chat_model is None or chat_model.kind != "chat":
        yield format_sse(
            event="error",
            data={
                "event": "error",
                "code": "internal_error",
                "message": "chat model not found",
                "request_id": request_id,
                "retryable": False,
            },
        )
        return
    provider = await model_service.get_provider(db, chat_model.provider_code)
    api_key = decrypt_api_key(chat_model.api_key_encrypted) if chat_model.api_key_encrypted else ""
    p = build_provider(provider.code, provider.base_url, api_key)

    finish_reason = "stop"
    accumulated = ""
    flush_token_counter = 0
    last_keepalive = time.time()

    try:
        stream = await p.chat(
            model_name=chat_model.model_name,
            messages=messages,
            temperature=req.temperature,
            stream=True,
            timeout=settings.model_provider_timeout_seconds,
        )
        # provider 返回 AsyncIterator
        async for delta in stream:
            if not delta:
                continue
            accumulated += delta
            flush_token_counter += 1
            yield format_sse(event="delta", data={"event": "delta", "text": delta})
            # 周期性把内容写回数据库（提示词 03 §5.6）
            if flush_token_counter >= settings.chat_stream_flush_every_tokens:
                assistant_msg.content = accumulated
                await db.flush()
                flush_token_counter = 0
            # 心跳
            if time.time() - last_keepalive > settings.chat_sse_keepalive_seconds:
                yield format_keepalive()
                last_keepalive = time.time()
    except asyncio.CancelledError:
        finish_reason = "cancelled"
        yield format_sse(
            event="error",
            data={
                "event": "error",
                "code": "cancelled",
                "message": "client disconnected",
                "request_id": request_id,
                "retryable": True,
            },
        )
    except Exception as exc:
        finish_reason = "error"
        yield format_sse(
            event="error",
            data={
                "event": "error",
                "code": "model_timeout",
                "message": str(exc)[:200],
                "request_id": request_id,
                "retryable": True,
            },
        )

    # 6. 落库最终消息
    assistant_msg.content = accumulated
    assistant_msg.citations = citations_payload
    assistant_msg.finish_reason = finish_reason
    conv = await db.get(Conversation, conversation_id)
    if conv is not None:
        conv.last_message_at = datetime.now(timezone.utc)
        conv.message_count = (conv.message_count or 0) + 1
        # 自动标题生成：流式结束后若 title 仍空，用聊天模型生成 ≤20 字
        if not conv.title and accumulated:
            try:
                title_stream = await p.chat(
                    model_name=chat_model.model_name,
                    messages=[
                        {"role": "user", "content": f"用不超过 20 个字总结：{accumulated[:200]}"}
                    ],
                    temperature=0.2,
                    stream=False,
                    max_tokens=64,
                    timeout=settings.model_provider_timeout_seconds,
                )
                title_text = title_stream if isinstance(title_stream, str) else ""
                conv.title = (title_text or "新会话")[:20]
            except Exception:
                conv.title = "新会话"

    yield format_sse(
        event="done",
        data={
            "event": "done",
            "finish_reason": finish_reason,
            "answer_version": assistant_msg.answer_version,
        },
    )
    await db.commit()


# ============================================================
# 路由
# ============================================================
@router.post("/stream")
async def chat_stream_endpoint(
    request: Request,
    payload: ChatStreamRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_permission("chat:write")),
    db: AsyncSession = Depends(get_db),
):
    async def event_gen():
        try:
            async for chunk in _chat_stream(db, user=user, req=payload):
                yield chunk
        except asyncio.CancelledError:
            # 客户端断开
            return
        except Exception as exc:
            yield format_sse(
                event="error",
                data={
                    "event": "error",
                    "code": "internal_error",
                    "message": str(exc)[:200],
                    "request_id": new_request_id(),
                    "retryable": False,
                },
            )

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
