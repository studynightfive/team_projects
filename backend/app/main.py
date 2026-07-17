# 智能知识库平台 - FastAPI 应用入口
# 负责创建 FastAPI 实例、注册中间件、加载路由、配置生命周期事件

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.common.config import settings
from app.common.exceptions import AppException
from app.common.metrics import metrics_endpoint, metrics_middleware
from app.common.schemas import APIResponse, ErrorCode, get_error_message
from app.documents.router import router as documents_router

# 员工5 路由（提示词 01~06）
from app.exports.all import router as exports_router
from app.models.api import router as models_router
from app.rag.chat.all import router as chat_router
from app.rag.conversations.all import router as conversations_router
from app.rag.search.api import router as retrieval_router
from app.rag.tests.all import router as retrieval_tests_router
from app.users.dashboard_router import router as dashboard_router
from app.users.role_router import router as role_router
from app.users.router import router as users_router

# 初始化结构化日志记录器
logger = structlog.get_logger()


# ============================================================
# 应用生命周期管理
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
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
    yield
    # 关闭阶段
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
async def request_id_middleware(request: Request, call_next):
    """为每个请求注入唯一标识"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.bind_contextvars(request_id=request_id)

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

    structlog.contextvars.clear_contextvars()
    return response


# ============================================================
# 全局异常处理器：统一错误响应格式（方案第14.2节）
# ============================================================
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理业务异常，返回统一响应格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            code=exc.code,
            message=exc.message,
            data=None,
            request_id=exc.request_id,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理未捕获异常，不暴露内部堆栈"""
    request_id = str(uuid.uuid4())
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
app.include_router(documents_router)

# Prometheus 指标
app.add_api_route("/api/v1/metrics", metrics_endpoint, methods=["GET"], tags=["metrics"])
app.middleware("http")(metrics_middleware)


# ============================================================
# 根路径
# ============================================================
@app.get("/")
async def root():
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
app.include_router(retrieval_tests_router)
