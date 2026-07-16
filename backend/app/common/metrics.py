# Prometheus 指标模块
# 使用 prometheus_client 提供指标采集
# 方案第17.4节：监控必须覆盖全部指标

from collections.abc import Callable

from fastapi import Request, Response
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, generate_latest

# ============================================================
# API 请求指标
# ============================================================
# API 请求总量（按方法、端点、状态码分类）
api_requests_total = Counter(
    "api_requests_total",
    "API 请求总量",
    ["method", "endpoint", "status_code"],
)

# API 请求延迟分布（秒）
api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API 请求延迟分布（秒）",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ============================================================
# SSE 连接指标
# ============================================================
# 当前活跃 SSE 连接数
sse_connections_active = Gauge(
    "sse_connections_active",
    "当前活跃 SSE 连接数",
)

# SSE 连接总数（按状态分类：completed/failed/cancelled）
sse_connections_total = Counter(
    "sse_connections_total",
    "SSE 连接总数",
    ["status"],
)

# ============================================================
# 文档任务指标
# ============================================================
# 文档任务总数（按状态和阶段分类）
document_tasks_total = Counter(
    "document_tasks_total",
    "文档任务总数",
    ["status", "stage"],
)

# 文档任务队列当前长度
document_task_queue_length = Gauge(
    "document_task_queue_length",
    "文档任务队列当前长度",
)

# 文档任务等待时间分布（秒）
document_task_wait_seconds = Histogram(
    "document_task_wait_seconds",
    "文档任务等待时间分布（秒）",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
)

# 文档各阶段处理耗时（秒）
document_task_duration_seconds = Histogram(
    "document_task_duration_seconds",
    "文档各阶段处理耗时（秒）",
    ["stage"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0],
)

# ============================================================
# 检索指标
# ============================================================
# 检索请求总数（按模式：keyword/vector/hybrid 和状态分类）
retrieval_requests_total = Counter(
    "retrieval_requests_total",
    "检索请求总数",
    ["mode", "status"],
)

# 检索延迟分布（秒）
retrieval_latency_seconds = Histogram(
    "retrieval_latency_seconds",
    "检索延迟分布（秒）",
    ["mode"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# 无命中检索次数
retrieval_no_hits_total = Counter(
    "retrieval_no_hits_total",
    "无命中检索次数",
    ["mode"],
)

# ============================================================
# 模型请求指标
# ============================================================
# 模型请求总数（按模型ID和状态分类）
model_requests_total = Counter(
    "model_requests_total",
    "模型请求总数",
    ["model_id", "status"],
)

# 模型请求耗时分布（秒）
model_request_duration_seconds = Histogram(
    "model_request_duration_seconds",
    "模型请求耗时分布（秒）",
    ["model_id"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

# Token 使用量（按模型ID和类型：input/output 分类）
model_tokens_total = Counter(
    "model_tokens_total",
    "Token 使用量",
    ["model_id", "type"],
)

# ============================================================
# 导出任务指标
# ============================================================
# 导出任务总数（按格式和状态分类）
export_tasks_total = Counter(
    "export_tasks_total",
    "导出任务总数",
    ["format", "status"],
)

# 导出任务耗时分布（秒）
export_task_duration_seconds = Histogram(
    "export_task_duration_seconds",
    "导出任务耗时分布（秒）",
    ["format"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
)

# ============================================================
# 数据库指标
# ============================================================
# 活跃数据库连接数
db_connections_active = Gauge(
    "db_connections_active",
    "活跃数据库连接数",
)

# 慢查询耗时分布（秒）
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "慢查询耗时分布（秒）",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# ============================================================
# Redis 指标
# ============================================================
# Redis 连接数
redis_connected_clients = Gauge(
    "redis_connected_clients",
    "Redis 连接数",
)

# Redis 内存使用（字节）
redis_memory_used_bytes = Gauge(
    "redis_memory_used_bytes",
    "Redis 内存使用（字节）",
)

# ============================================================
# 文件存储指标
# ============================================================
# 文件存储使用量（字节）
file_storage_used_bytes = Gauge(
    "file_storage_used_bytes",
    "文件存储使用量（字节）",
)


# ============================================================
# 指标中间件：自动收集 API 请求指标
# ============================================================
async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """
    Prometheus 指标中间件
    自动收集每个 API 请求的指标：
    - api_requests_total：请求计数
    - api_request_duration_seconds：请求延迟
    """
    import time

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # 获取路由路径（去除参数，如 /users/123 -> /users/{user_id}）
    endpoint = request.url.path
    method = request.method
    status_code = str(response.status_code)

    # 记录请求计数
    api_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code,
    ).inc()

    # 记录请求延迟
    api_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)

    return response


# ============================================================
# 指标端点处理函数
# ============================================================
async def metrics_endpoint() -> Response:
    """
    Prometheus 指标端点
    返回 Prometheus 格式的指标数据
    """
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; charset=utf-8",
    )
