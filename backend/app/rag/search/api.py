"""检索路由（提示词 02）"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import cast

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_any_permission
from app.common.database import async_session_factory, get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.rag._shared.audit_helper import audit
from app.rag._shared.permissions import new_request_id
from app.rag._shared.sse import format_sse
from app.rag._shared.stream_session import stream_user_session
from app.rag.guard import ensure_safe_query, inspect_query
from app.rag.metrics import record_retrieval_metric
from app.rag.observability import create_trace_id
from app.rag.search import service
from app.rag.search.schemas import (
    GuardCategory,
    QueryGuardRequest,
    QueryGuardResponse,
    RagAnswerRequest,
    SearchHit,
    SearchRequest,
)
from app.rag.search.stream import stream_answer

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])
logger = structlog.get_logger()


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else new_request_id()


def _request_knowledge_base_id(payload: SearchRequest) -> str | None:
    """无引用时使用用户选择顺序中的首个知识库作为运营归属。"""

    if payload.kb_id is not None:
        return payload.kb_id
    if payload.kb_ids:
        return payload.kb_ids[0]
    return None


def _primary_product(
    hits: list[SearchHit],
) -> tuple[str | None, str | None, str | None]:
    """以最终首条引用作为本次问答的主商品，不使用问题文本猜测商品。"""

    if not hits:
        return None, None, None
    hit = hits[0]
    product_name = (hit.doc_title or "").strip()
    if not hit.doc_id.strip() or not product_name:
        return None, None, hit.kb_id
    return hit.doc_id, product_name, hit.kb_id


@router.post("/guard/check")
async def check_query_guard_endpoint(
    payload: QueryGuardRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("retrieval.search", "chat.use", "chat:write")),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[QueryGuardResponse]:
    """输入框防抖预检；最终检索接口仍会再次执行同一缓存判定。"""

    del user
    result = await inspect_query(
        payload.query,
        db=db,
        model_id=payload.chat_model_id,
    )
    return APIResponse(
        data=QueryGuardResponse(
            allowed=result.allowed,
            category=cast(GuardCategory | None, result.category),
            message=None if result.allowed else "输入内容不合法，请修改后重试",
            semantic_checked=result.semantic_checked,
        )
    )


@router.post("/search")
async def search_endpoint(
    request: Request,
    payload: SearchRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("retrieval.search", "retrieval:read")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    response = await service.search(db, user=user, req=payload)
    request_id = _request_id(request)
    product_id, product_name, hit_knowledge_base_id = _primary_product(response.hits)
    metric_knowledge_base_id = (
        hit_knowledge_base_id or _request_knowledge_base_id(payload)
    )
    await record_retrieval_metric(
        db,
        user=user,
        event_type="search",
        request_id=request_id,
        knowledge_base_id=metric_knowledge_base_id,
        hit_count=len(response.hits),
        generated=False,
        cache_hit=False,
        took_ms=response.took_ms,
        primary_product_id=product_id,
        primary_product_name=product_name,
    )
    await audit(
        db,
        action="retrieval_search",
        user_id=user.id,
        resource_type="kb",
        resource_id=metric_knowledge_base_id,
        detail=f"mode={payload.mode} top_k={payload.top_k}",
        request=request,
    )
    await db.commit()
    return APIResponse(data=response.model_dump()).model_dump()


@router.post("/answer")
async def answer_endpoint(
    request: Request,
    payload: RagAnswerRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("retrieval.search", "chat.use", "chat:write")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    response = await service.answer(db, user=user, req=payload)
    request_id = _request_id(request)
    product_id, product_name, hit_knowledge_base_id = _primary_product(response.hits)
    metric_knowledge_base_id = (
        hit_knowledge_base_id or _request_knowledge_base_id(payload)
    )
    await record_retrieval_metric(
        db,
        user=user,
        event_type="answer",
        request_id=request_id,
        knowledge_base_id=metric_knowledge_base_id,
        hit_count=len(response.hits),
        generated=response.generated,
        cache_hit=response.from_cache,
        took_ms=response.took_ms,
        primary_product_id=product_id,
        primary_product_name=product_name,
    )
    await audit(
        db,
        action="rag_answer",
        user_id=user.id,
        resource_type="kb",
        resource_id=metric_knowledge_base_id,
        detail=f"mode={payload.mode} top_k={payload.top_k} generated={response.generated}",
        request=request,
    )
    await db.commit()
    return APIResponse(data=response.model_dump()).model_dump()


@router.post(
    "/answer/stream",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "RAG 流式回答事件",
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
async def answer_stream_endpoint(
    request: Request,
    payload: RagAnswerRequest,
    user: User = Depends(get_current_user),
    _perm: None = Depends(require_any_permission("retrieval.search", "chat.use", "chat:write")),
) -> StreamingResponse:
    # 在创建 SSE 响应前完成守卫，违规输入直接得到标准 422，而不是流内错误。
    user_id = user.id
    request_id = _request_id(request)
    langfuse_trace_id = create_trace_id(request_id)
    async with async_session_factory() as preprocess_db:
        rewrite = await ensure_safe_query(
            payload.query,
            db=preprocess_db,
            model_id=payload.chat_model_id,
            trace_id=langfuse_trace_id,
        )

    async def event_generator() -> AsyncIterator[str]:
        completed = False
        citation_count = 0
        generated = False
        cache_hit = False
        took_ms = 0
        primary_product_id: str | None = None
        primary_product_name: str | None = None
        metric_knowledge_base_id = _request_knowledge_base_id(payload)
        try:
            async with stream_user_session(user_id) as (stream_db, stream_user):
                async for event in stream_answer(
                    stream_db,
                    user=stream_user,
                    req=payload,
                    rewrite=rewrite,
                    trace_id=langfuse_trace_id,
                ):
                    if event.event == "citation":
                        citation_count += 1
                        if primary_product_id is None:
                            event_product_id = event.data.get("doc_id")
                            event_product_name = event.data.get("doc_title")
                            if (
                                isinstance(event_product_id, str)
                                and event_product_id.strip()
                                and isinstance(event_product_name, str)
                                and event_product_name.strip()
                            ):
                                primary_product_id = event_product_id
                                primary_product_name = event_product_name
                                event_knowledge_base_id = event.data.get("kb_id")
                                if (
                                    isinstance(event_knowledge_base_id, str)
                                    and event_knowledge_base_id.strip()
                                ):
                                    metric_knowledge_base_id = event_knowledge_base_id
                    if event.event == "done":
                        completed = True
                        generated = event.data.get("generated") is True
                        cache_hit = event.data.get("from_cache") is True
                        event_took_ms = event.data.get("took_ms")
                        if isinstance(event_took_ms, int) and not isinstance(
                            event_took_ms,
                            bool,
                        ):
                            took_ms = event_took_ms
                    yield format_sse(event=event.event, data=event.data)
                if completed:
                    await record_retrieval_metric(
                        stream_db,
                        user=stream_user,
                        event_type="answer",
                        request_id=request_id,
                        knowledge_base_id=metric_knowledge_base_id,
                        hit_count=citation_count,
                        generated=generated,
                        cache_hit=cache_hit,
                        took_ms=took_ms,
                        primary_product_id=primary_product_id,
                        primary_product_name=primary_product_name,
                    )
                await audit(
                    stream_db,
                    action="rag_answer_stream",
                    user_id=stream_user.id,
                    resource_type="kb",
                    resource_id=metric_knowledge_base_id,
                    detail=(
                        f"mode={payload.mode} top_k={payload.top_k} "
                        f"completed={completed}"
                    ),
                    request=request,
                )
                await stream_db.commit()
        except asyncio.CancelledError:
            logger.info("rag_answer_stream_cancelled", user_id=user_id)
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "rag_answer_stream_failed",
                request_id=request_id,
                error_type=type(exc).__name__,
            )
            yield format_sse(
                event="error",
                data={
                    "event": "error",
                    "code": "rag_stream_failed",
                    "message": "流式回答暂时不可用，请稍后重试。",
                    "request_id": request_id,
                    "retryable": True,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
