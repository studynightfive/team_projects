"""流式问答（提示词 03）—— schemas + service + api 单文件版

SSE 事件序列：start → delta* → citation* → done | error
服务端真正取消模型调用；引用经 post_filter 权限保护；answer_versions 保留。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_any_permission
from app.common.config import settings
from app.common.database import get_db
from app.common.exceptions import ForbiddenException, ValidationException
from app.common.models import User
from app.documents.permissions import user_can_access_kb
from app.models import service as model_service
from app.models.providers.openai import OpenAICompatibleProvider, build_provider
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
    get_conversation,
    regenerate_answer,
)
from app.rag.guard import ensure_safe_query
from app.rag.search.schemas import SearchRequest
from app.rag.search.service import search as search_rag

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = structlog.get_logger()


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
    metadata_filter: dict[str, object] | None = None
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
) -> list[dict[str, object]]:
    search_resp = await search_rag(
        db,
        user=user,
        req=SearchRequest(
            query=req.question,
            mode="hybrid",
            kb_id=req.kb_id,
            top_k=req.top_k,
            threshold=0.0,
            metadata_filter=req.metadata_filter,
            rerank=bool(req.rerank_model_id),
            rerank_model_id=req.rerank_model_id,
            embedding_model_id=req.embedding_model_id,
        ),
        guard_checked=True,
    )
    # 二次权限过滤（即使 search 内已过滤）
    hits_dicts: list[dict[str, object]] = [h.model_dump() for h in search_resp.hits]
    accessible = await get_user_accessible_kb_ids(db, user)
    safe = post_filter_hits(hits=hits_dicts, accessible_kb_ids=accessible)
    return safe


def _build_prompt(
    question: str, contexts: list[dict[str, object]]
) -> list[dict[str, str]]:
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
    message_id = new_message_id()

    # 1. 创建/获取会话与消息
    if not await user_can_access_kb(db, user, req.kb_id):
        raise ForbiddenException(message="无权访问该知识库")

    if req.conversation_id is None:
        if req.parent_message_id is not None:
            raise ValidationException(message="重新生成必须指定已有会话")
        conv = Conversation(user_id=user.id, kb_id=req.kb_id, title="")
        db.add(conv)
        await db.flush()
        conversation_id = conv.id
    else:
        conv = await get_conversation(
            db,
            conv_id=req.conversation_id,
            user_id=user.id,
        )
        if conv.kb_id != req.kb_id:
            raise ValidationException(message="会话与知识库不匹配")
        conversation_id = conv.id

    if req.parent_message_id is None:
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=req.question,
        )
        db.add(user_msg)
        conv.message_count = (conv.message_count or 0) + 1

    # 2. 处理重新生成
    if req.parent_message_id:
        parent = await db.get(Message, req.parent_message_id)
        if (
            parent is None
            or parent.conversation_id != conversation_id
            or parent.role != "assistant"
        ):
            raise ValidationException(message="父消息不属于当前会话或不可重新生成")
        assistant_msg = await regenerate_answer(db, parent_message_id=req.parent_message_id)
        message_id = assistant_msg.id
    else:
        assistant_msg = Message(conversation_id=conversation_id, role="assistant", content="")
        db.add(assistant_msg)
        await db.flush()
        message_id = assistant_msg.id

    # 返回数据库实际生成的会话和消息 ID，避免客户端持有不存在的临时 ID。
    yield format_sse(
        event="start",
        data={
            "event": "start",
            "request_id": request_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
        },
    )

    # 3. 检索 + 拼 prompt
    try:
        contexts = await _retrieve_context(db, user=user, req=req)
    except Exception as exc:
        logger.warning(
            "chat_retrieval_failed",
            request_id=request_id,
            error_type=type(exc).__name__,
        )
        yield format_sse(
            event="error",
            data={
                "event": "error",
                "code": "retrieval_failed",
                "message": "检索服务暂不可用",
                "request_id": request_id,
                "retryable": True,
            },
        )
        assistant_msg.finish_reason = "error"
        await db.commit()
        return

    # 4. 发送 citations（受 post_filter 保护）
    citations_payload: list[dict[str, object]] = []
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
    if chat_model is None or chat_model.kind != "chat" or not chat_model.enabled:
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
    if provider is None or not provider.enabled:
        yield format_sse(event="error", data={
            "event": "error", "code": "internal_error", "message": "provider not found",
            "request_id": request_id, "retryable": False,
        })
        return
    api_key = decrypt_api_key(chat_model.api_key_encrypted) if chat_model.api_key_encrypted else ""
    p: OpenAICompatibleProvider = build_provider(provider.code, provider.base_url, api_key)

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
        if isinstance(stream, str):
            raise TypeError("流式模型返回了非流式结果")
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
        logger.warning(
            "chat_model_failed",
            request_id=request_id,
            error_type=type(exc).__name__,
        )
        yield format_sse(
            event="error",
            data={
                "event": "error",
                "code": "model_timeout",
                "message": "模型服务暂不可用",
                "request_id": request_id,
                "retryable": True,
            },
        )

    # 6. 落库最终消息
    assistant_msg.content = accumulated
    assistant_msg.citations = citations_payload
    assistant_msg.finish_reason = finish_reason
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
    _perm: None = Depends(require_any_permission("chat.use", "chat:write")),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    await ensure_safe_query(payload.question)

    async def event_gen() -> AsyncIterator[str]:
        try:
            async for chunk in _chat_stream(db, user=user, req=payload):
                yield chunk
        except asyncio.CancelledError:
            # 客户端断开
            return
        except Exception as exc:
            request_id = new_request_id()
            logger.warning(
                "chat_stream_failed",
                request_id=request_id,
                error_type=type(exc).__name__,
            )
            yield format_sse(
                event="error",
                data={
                    "event": "error",
                    "code": "internal_error",
                    "message": "流式问答失败",
                    "request_id": request_id,
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
