"""Langfuse 观测适配必须保护正文，并在故障时保持 RAG 可用。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.rag import observability


class _ObservationContext:
    def __init__(self, current: object) -> None:
        self.current = current

    def __enter__(self) -> object:
        return self.current

    def __exit__(self, *_args: object) -> None:
        return None


def test_observation_hides_content_by_default(monkeypatch) -> None:
    current = SimpleNamespace(update=Mock())
    client = SimpleNamespace(
        start_as_current_observation=Mock(
            return_value=_ObservationContext(current)
        )
    )
    monkeypatch.setattr(observability, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(observability.settings, "langfuse_capture_content", False)

    with observability.observe(
        "rag-answer",
        as_type="chain",
        input_value="不应上传的问题正文",
        metadata={"hit_count": 2},
    ) as observation:
        observability.update_observation(
            observation,
            output_value="不应上传的答案正文",
            metadata={"cache_hit": False},
        )

    call = client.start_as_current_observation.call_args
    assert call.kwargs["input"] is None
    current.update.assert_called_once_with(metadata={"cache_hit": False})


def test_observation_start_failure_is_noop(monkeypatch) -> None:
    client = SimpleNamespace(
        start_as_current_observation=Mock(
            side_effect=ConnectionError("langfuse unavailable")
        )
    )
    monkeypatch.setattr(observability, "get_langfuse_client", lambda: client)

    with observability.observe("rag-search", as_type="retriever") as observation:
        assert observation is None
