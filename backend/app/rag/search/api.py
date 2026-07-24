"""检索路由（提示词 02）"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_any_permission
from app.common.database import get_db
from app.common.models import User
from app.common.schemas import APIResponse
from app.rag._shared.audit_helper import audit
from app.rag._shared.permissions import new_request_id
from app.rag._shared.sse import format_sse
from app.rag.guard import ensure_safe_query
from app.rag.metrics import record_retrieval_metric
from app.rag.search import service
from app.rag.search.schemas import RagAnswerRequest, SearchRequest
from app.rag.search.stream import stream_answer

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])
logger = structlog.get_logger()


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else new_request_id()


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
    await record_retrieval_metric(
        db,
        user=user,
        event_type="search",
        request_id=request_id,
        knowledge_base_id=payload.kb_id,
        hit_count=len(response.hits),
        generated=False,
        cache_hit=False,
        took_ms=response.took_ms,
    )
    await audit(
        db,
        action="retrieval_search",
        user_id=user.id,
        resource_type="kb",
        resource_id=payload.kb_id,
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
    await record_retrieval_metric(
        db,
        user=user,
        event_type="answer",
        request_id=request_id,
        knowledge_base_id=payload.kb_id,
        hit_count=len(response.hits),
        generated=response.generated,
        cache_hit=response.from_cache,
        took_ms=response.took_ms,
    )
    await audit(
        db,
        action="rag_answer",
        user_id=user.id,
        resource_type="kb",
        resource_id=payload.kb_id,
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
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    await ensure_safe_query(payload.query)

    async def event_generator() -> AsyncIterator[str]:
        completed = False
        citation_count = 0
        generated = False
        cache_hit = False
        took_ms = 0
        try:
            async for event in stream_answer(db, user=user, req=payload):
                if event.event == "citation":
                    citation_count += 1
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
                    db,
                    user=user,
                    event_type="answer",
                    request_id=_request_id(request),
                    knowledge_base_id=payload.kb_id,
                    hit_count=citation_count,
                    generated=generated,
                    cache_hit=cache_hit,
                    took_ms=took_ms,
                )
            await audit(
                db,
                action="rag_answer_stream",
                user_id=user.id,
                resource_type="kb",
                resource_id=payload.kb_id,
                detail=f"mode={payload.mode} top_k={payload.top_k} completed={completed}",
                request=request,
            )
            await db.commit()
        except asyncio.CancelledError:
            logger.info("rag_answer_stream_cancelled", user_id=user.id)
            return
        except Exception as exc:  # noqa: BLE001
            request_id = new_request_id()
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
