"""RAG 用户输入安全守卫。"""

from __future__ import annotations

import asyncio
import re
import threading
import unicodedata
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from typing import Literal, Protocol, TypeVar

import structlog

from app.common.config import settings
from app.common.exceptions import AppException, ValidationException
from app.common.schemas import ErrorCode

logger = structlog.get_logger()

_CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "涉黄": (
        "色情",
        "成人视频",
        "成人影片",
        "无码影片",
        "裸露影像",
        "露骨内容",
        "黄色网站",
        "裸聊",
        "淫秽",
        "约炮",
        "性服务",
        "卖淫",
        "嫖娼",
    ),
    "涉赌": (
        "赌博",
        "博彩",
        "赌场",
        "赌钱",
        "赌局",
        "下注",
        "赌资",
        "洗码",
        "百家乐",
        "轮盘",
        "老虎机",
        "牌九",
        "德州扑克",
        "casino",
        "gambling",
        "betting",
    ),
    "涉毒": (
        "毒品",
        "制毒",
        "贩毒",
        "吸毒",
        "冰毒",
        "海洛因",
        "摇头丸",
        "麻古",
        "可卡因",
        "k粉",
        "违禁粉末",
        "cocaine",
        "heroin",
        "methamphetamine",
        "芬太尼滥用",
    ),
}

ScannerName = Literal["ban_topics", "prompt_injection"]
T = TypeVar("T")


class PromptScanner(Protocol):
    def scan(self, prompt: str) -> tuple[str, bool, float]: ...


@dataclass(frozen=True)
class ScannerBinding:
    name: ScannerName
    scanner: PromptScanner


@dataclass(frozen=True)
class GuardRejection:
    scanner: ScannerName
    score: float


_scanner_bindings: tuple[ScannerBinding, ...] | None = None
_scanner_init_lock = threading.Lock()
_scanner_inference_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE)


def classify_prohibited_input(value: str) -> str | None:
    normalized = _normalize(value)
    for category, terms in _CATEGORY_TERMS.items():
        if any(_normalize(term) in normalized for term in terms):
            return category
    return None


def _configured_topics() -> list[str]:
    return [item.strip() for item in settings.llm_guard_ban_topics.split("|") if item.strip()]


def _build_scanners() -> tuple[ScannerBinding, ...]:
    from llm_guard.input_scanners.ban_topics import MODEL_BGE_M3_V2, BanTopics
    from llm_guard.input_scanners.prompt_injection import MatchType, PromptInjection

    topics = _configured_topics()
    if not topics:
        raise RuntimeError("LLM Guard banned topics are empty")
    return (
        ScannerBinding(
            name="ban_topics",
            scanner=BanTopics(
                topics=topics,
                threshold=settings.llm_guard_ban_topics_threshold,
                model=MODEL_BGE_M3_V2,
            ),
        ),
        ScannerBinding(
            name="prompt_injection",
            scanner=PromptInjection(
                threshold=settings.llm_guard_prompt_injection_threshold,
                match_type=MatchType.FULL,
            ),
        ),
    )


def _get_scanners() -> tuple[ScannerBinding, ...]:
    global _scanner_bindings

    if _scanner_bindings is not None:
        return _scanner_bindings
    with _scanner_init_lock:
        if _scanner_bindings is None:
            logger.info("llm_guard_models_loading")
            _scanner_bindings = _build_scanners()
            logger.info(
                "llm_guard_models_ready",
                scanners=[binding.name for binding in _scanner_bindings],
            )
    return _scanner_bindings


def _get_executor() -> ThreadPoolExecutor:
    global _executor

    if _executor is not None:
        return _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=settings.llm_guard_thread_workers,
                thread_name_prefix="llm-guard",
            )
    return _executor


def _scan_with_models(value: str) -> GuardRejection | None:
    with _scanner_inference_lock:
        prompt = value
        for binding in _get_scanners():
            prompt, is_valid, score = binding.scanner.scan(prompt)
            if settings.debug:
                logger.info(
                    "llm_guard_scan_result",
                    scanner=binding.name,
                    is_valid=is_valid,
                    score=round(float(score), 4),
                )
            if not is_valid:
                return GuardRejection(scanner=binding.name, score=score)
    return None


async def _run_in_guard_pool(callback: Callable[[], T], *, timeout: float | None) -> T:
    future = asyncio.get_running_loop().run_in_executor(_get_executor(), callback)
    if timeout is None:
        return await future
    return await asyncio.wait_for(future, timeout=timeout)


def _raise_or_log_guard_failure(exc: BaseException) -> None:
    logger.error("llm_guard_scan_failed", error_type=type(exc).__name__)
    if settings.llm_guard_fail_closed:
        raise AppException(
            code=ErrorCode.INTERNAL_ERROR,
            message="输入安全检查暂时不可用，请稍后重试",
            status_code=503,
        ) from exc
    logger.warning("llm_guard_scan_fail_open")


async def ensure_safe_query(value: str) -> None:
    category = classify_prohibited_input(value)
    if category is not None:
        logger.warning("rag_input_blocked", category=category, scanner="keyword")
        raise ValidationException(message=f"输入内容涉及{category}，无法进行检索或问答")

    if not settings.llm_guard_enabled or settings.testing:
        return

    try:
        rejection = await _run_in_guard_pool(
            partial(_scan_with_models, value),
            timeout=settings.llm_guard_scan_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_or_log_guard_failure(exc)
        return

    if rejection is None:
        return

    logger.warning(
        "rag_input_blocked",
        scanner=rejection.scanner,
        score=round(rejection.score, 4),
    )
    if rejection.scanner == "prompt_injection":
        message = "输入内容疑似提示词注入，无法进行检索或问答"
    else:
        message = "输入内容涉及禁止主题，无法进行检索或问答"
    raise ValidationException(message=message)


async def preload_guard_models() -> None:
    """在后台线程预热模型；失败后由首次请求按故障策略处理。"""
    if not settings.llm_guard_enabled or not settings.llm_guard_preload or settings.testing:
        return
    try:
        await _run_in_guard_pool(_get_scanners, timeout=None)
    except Exception as exc:  # noqa: BLE001
        logger.error("llm_guard_preload_failed", error_type=type(exc).__name__)


def guard_readiness_status() -> str:
    if (
        not settings.llm_guard_enabled
        or not settings.llm_guard_preload
        or settings.testing
    ):
        return "ok"
    return "ok" if _scanner_bindings is not None else "warming"


def shutdown_guard() -> None:
    """关闭专用线程池；模型随 FastAPI 进程释放。"""
    global _executor, _scanner_bindings

    with _executor_lock:
        executor = _executor
        _executor = None
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)
    with _scanner_init_lock:
        _scanner_bindings = None


def reset_guard_state_for_tests() -> None:
    shutdown_guard()
