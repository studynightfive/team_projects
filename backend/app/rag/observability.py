"""Langfuse 可选观测适配；未配置或上报失败时不影响业务请求。"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Literal, cast

import structlog
from langfuse import Langfuse, propagate_attributes
from langfuse.types import TraceContext

from app.common.config import settings

logger = structlog.get_logger()
ObservationType = Literal[
    "span",
    "agent",
    "tool",
    "chain",
    "retriever",
    "evaluator",
    "guardrail",
    "generation",
    "embedding",
]
SpanObservationType = Literal[
    "span",
    "agent",
    "tool",
    "chain",
    "retriever",
    "evaluator",
    "guardrail",
]


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    """只在配置完整时创建单例，避免每个请求重复启动 OTel 导出线程。"""

    if not settings.langfuse_enabled:
        return None
    if not settings.langfuse_public_key.strip() or not settings.langfuse_secret_key.strip():
        logger.warning("langfuse_disabled_missing_credentials")
        return None
    try:
        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_base_url,
            environment=settings.langfuse_environment,
            release=settings.langfuse_release or None,
            tracing_enabled=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("langfuse_initialization_failed", error_type=type(exc).__name__)
        return None


def create_trace_id(seed: str) -> str | None:
    client = get_langfuse_client()
    if client is None:
        return None
    try:
        return client.create_trace_id(seed=seed)
    except Exception as exc:  # noqa: BLE001
        logger.info("langfuse_trace_id_failed", error_type=type(exc).__name__)
        return None


@contextmanager
def observe(
    name: str,
    *,
    as_type: ObservationType = "span",
    trace_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
    metadata: dict[str, object] | None = None,
    input_value: object | None = None,
) -> Iterator[Any | None]:
    """创建当前 observation；正文只有在运维显式开启时才会传给 Langfuse。"""

    client = get_langfuse_client()
    if client is None:
        yield None
        return

    content = input_value if settings.langfuse_capture_content else None
    trace_context: TraceContext | None = (
        cast(TraceContext, {"trace_id": trace_id})
        if trace_id is not None
        else None
    )
    try:
        attributes = propagate_attributes(
            user_id=user_id,
            session_id=session_id,
            metadata=metadata,
            trace_name=name,
            tags=["rag", settings.app_environment],
        )
        observation: Any
        if as_type == "generation":
            observation = client.start_as_current_observation(
                trace_context=trace_context,
                name=name,
                as_type="generation",
                input=content,
                metadata=metadata,
                model=model,
            )
        elif as_type == "embedding":
            observation = client.start_as_current_observation(
                trace_context=trace_context,
                name=name,
                as_type="embedding",
                input=content,
                metadata=metadata,
                model=model,
            )
        else:
            observation = client.start_as_current_observation(
                trace_context=trace_context,
                name=name,
                as_type=as_type,
                input=content,
                metadata=metadata,
            )
    except Exception as exc:  # noqa: BLE001
        logger.info("langfuse_observation_start_failed", error_type=type(exc).__name__)
        yield None
        return

    with attributes:
        with observation as current:
            yield current


def update_observation(
    observation: Any | None,
    *,
    output_value: object | None = None,
    metadata: dict[str, object] | None = None,
    level: Literal["DEBUG", "DEFAULT", "WARNING", "ERROR"] | None = None,
    status_message: str | None = None,
) -> None:
    if observation is None:
        return
    values: dict[str, object] = {}
    if output_value is not None and settings.langfuse_capture_content:
        values["output"] = output_value
    if metadata is not None:
        values["metadata"] = metadata
    if level is not None:
        values["level"] = level
    if status_message is not None:
        values["status_message"] = status_message
    try:
        observation.update(**values)
    except Exception as exc:  # noqa: BLE001
        logger.info("langfuse_observation_update_failed", error_type=type(exc).__name__)


def shutdown_langfuse() -> None:
    client = get_langfuse_client()
    if client is None:
        return
    try:
        client.shutdown()
    except Exception as exc:  # noqa: BLE001
        logger.info("langfuse_shutdown_failed", error_type=type(exc).__name__)
