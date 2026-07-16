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
from app.common.config import settings
from app.common.metrics import metrics_endpoint, metrics_middleware

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
    # 启动阶段：输出启动日志
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
    )
    yield
    # 关闭阶段：输出关闭日志
    logger.info("application_shutting_down")


# ============================================================
# 创建 FastAPI 应用实例
# ============================================================
app = FastAPI(
    # 应用标题（方案第14.1节：API 前缀 /api/v1）
    title=settings.app_name,
    # 应用版本
    version=settings.app_version,
    # API 文档路径（OpenAPI）
    openapi_url="/api/v1/openapi.json",
    # Swagger UI 文档路径
    docs_url="/api/v1/docs",
    # 生命周期管理
    lifespan=lifespan,
)

# ============================================================
# CORS 中间件：允许前端跨域访问
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # 允许的域名列表
    allow_credentials=True,               # 允许携带 Cookie
    allow_methods=["*"],                   # 允许所有 HTTP 方法
    allow_headers=["*"],                   # 允许所有请求头
)


# ============================================================
# Request ID 中间件：为每个请求注入唯一标识
# ============================================================
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    请求 ID 中间件
    1. 从请求头获取或生成 request_id
    2. 记录请求开始和结束时间
    3. 在响应头中返回 request_id
    """
    # 生成或获取 request_id
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

    # 将 request_id 绑定到结构化日志上下文
    structlog.contextvars.bind_contextvars(request_id=request_id)

    # 记录请求开始时间
    start_time = time.time()

    # 处理请求
    response = await call_next(request)

    # 计算请求耗时（毫秒）
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # 在响应头中返回 request_id
    response.headers["X-Request-ID"] = request_id

    # 记录请求完成日志
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )

    # 清理日志上下文
    structlog.contextvars.clear_contextvars()

    return response


# ============================================================
# 全局异常处理器：统一错误响应格式
# ============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    将所有未捕获异常转换为统一响应格式（方案第14.2节）
    不暴露内部堆栈信息给客户端
    """
    request_id = str(uuid.uuid4())
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        error_type=type(exc).__name__,
        # 不记录完整堆栈到日志（安全原因），仅记录错误类型和消息
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": 10000,  # 通用错误码
            "message": "服务器内部错误",  # 安全错误信息，不暴露内部细节
            "data": None,
            "request_id": request_id,
        },
    )


# ============================================================
# 注册路由
# ============================================================
# 健康检查路由（/api/v1/health/live、/api/v1/health/ready）
app.include_router(health_router, prefix="/api/v1")

# Prometheus 指标路由（/api/v1/metrics）
app.add_api_route("/api/v1/metrics", metrics_endpoint, methods=["GET"], tags=["metrics"])

# 注册指标中间件（自动收集 API 请求指标）
app.middleware("http")(metrics_middleware)


# ============================================================
# 根路径重定向
# ============================================================
@app.get("/")
async def root():
    """
    根路径：返回 API 基本信息
    """
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/v1/docs",
    }
