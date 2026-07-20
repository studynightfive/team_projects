# 智能知识库平台 - FastAPI 应用入口
# 负责创建 FastAPI 实例、注册中间件、加载路由、配置生命周期事件

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.health import router as health_router
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.common.config import settings
from app.common.database import async_session_factory, engine
from app.common.exceptions import AppException
from app.common.logging import setup_logging
from app.common.metrics import metrics_endpoint, metrics_middleware
from app.common.openapi import install_openapi_schema
from app.common.schemas import APIResponse, ErrorCode, get_error_message
from app.common.seed import (
    seed_builtin_authorization,
    seed_default_chat_model,
    seed_default_embedding_model,
    seed_default_knowledge_base,
    seed_demo_accounts,
)
from app.documents.router import router as documents_router

# 员工5 路由（提示词 01~06）
from app.exports.all import router as exports_router
from app.favorites.router import router as favorites_router
from app.knowledge.router import router as knowledge_router
from app.models.api import router as models_router
from app.notifications.router import router as notifications_router
from app.rag.chat.all import router as chat_router
from app.rag.conversations.all import router as conversations_router
from app.rag.search.api import router as retrieval_router
from app.rag.tests.all import router as retrieval_tests_router
from app.rag.sensitive_filter.router import router as sensitive_filter_router
from app.users.dashboard_router import router as dashboard_router
from app.users.role_router import router as role_router
from app.users.router import router as users_router

# 在创建任何 logger 前启用统一 JSON 输出和敏感字段过滤。
setup_logging(level="DEBUG" if settings.debug else "INFO")
logger = structlog.get_logger()


# ============================================================
# 应用生命周期管理
# ============================================================
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """
    应用生命周期管理器
    启动时：初始化数据库连接池、Redis 连接
    关闭时：释放数据库连接池、Redis 连接
    """
    # 启动阶段
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
    )
    async with async_session_factory() as db:
        await seed_builtin_authorization(db)
        if settings.auto_seed_demo_data:
            await seed_demo_accounts(db)
            await seed_default_knowledge_base(db)
            await seed_default_chat_model(db)
            await seed_default_embedding_model(db)
    try:
        yield
    finally:
        await engine.dispose()
        logger.info("application_shutting_down")


# ============================================================
# 创建 FastAPI 应用实例
# ============================================================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    lifespan=lifespan,
)

# ============================================================
# CORS 中间件
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request ID 中间件
# ============================================================
@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """为每个请求注入唯一标识"""
    supplied_request_id = request.headers.get("X-Request-ID")
    try:
        request_id = (
            str(uuid.UUID(supplied_request_id))
            if supplied_request_id
            else str(uuid.uuid4())
        )
    except ValueError:
        request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)

    try:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
    finally:
        structlog.contextvars.clear_contextvars()


# ============================================================
# 全局异常处理器：统一错误响应格式（方案第14.2节）
# ============================================================
def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) and request_id else str(uuid.uuid4())


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理业务异常，返回统一响应格式"""
    request_id = _request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            code=exc.code,
            message=exc.message,
            data=None,
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, _exc: RequestValidationError
) -> JSONResponse:
    """校验失败不回显原始输入，保持所有 API 错误使用统一响应契约。"""
    request_id = _request_id(request)
    return JSONResponse(
        status_code=422,
        content=APIResponse(
            code=ErrorCode.VALIDATION_ERROR,
            message=get_error_message(ErrorCode.VALIDATION_ERROR),
            data=None,
            request_id=request_id,
        ).model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """把框架生成的 404/405 等错误收敛到公开 API 契约。"""
    code_by_status = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
    }
    code = code_by_status.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            code=code,
            message=get_error_message(code),
            data=None,
            request_id=_request_id(request),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获异常，不暴露内部堆栈"""
    request_id = _request_id(request)
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message=get_error_message(ErrorCode.INTERNAL_ERROR),
            data=None,
            request_id=request_id,
        ).model_dump(),
    )


# ============================================================
# 注册路由
# ============================================================
# 健康检查
app.include_router(health_router, prefix="/api/v1")

# 认证（登录、退出、刷新、/me）
app.include_router(auth_router)

# 用户管理
app.include_router(users_router)

# 角色管理
app.include_router(role_router)

# 审计日志
app.include_router(audit_router)

# 系统概览
app.include_router(dashboard_router)

# 文档处理（员工 4）
app.include_router(knowledge_router)
app.include_router(documents_router)

# Prometheus 指标
app.add_api_route("/api/v1/metrics", metrics_endpoint, methods=["GET"], tags=["metrics"])
app.middleware("http")(metrics_middleware)


# ============================================================
# 根路径
# ============================================================
@app.get("/")
async def root() -> dict[str, str]:
    """根路径：返回 API 基本信息"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/v1/docs",
    }


app.include_router(models_router)
app.include_router(retrieval_router)
app.include_router(conversations_router)
app.include_router(chat_router)
app.include_router(exports_router)
app.include_router(favorites_router)
app.include_router(retrieval_tests_router)
app.include_router(sensitive_filter_router)
app.include_router(notifications_router)

install_openapi_schema(app)
