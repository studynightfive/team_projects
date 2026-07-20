"""Prometheus HTTP 指标。

只暴露当前确实由应用更新的指标。数据库、Redis、磁盘和 Worker 指标需要
对应 exporter 或采集逻辑，不能用永远为零的占位 Gauge 冒充监控覆盖。
"""

import time

from fastapi import Request, Response
from prometheus_client import REGISTRY, Counter, Histogram, generate_latest
from starlette.middleware.base import RequestResponseEndpoint

api_requests_total = Counter(
    "api_requests_total",
    "API 请求总量",
    ["method", "endpoint", "status_code"],
)

api_request_duration_seconds = Histogram(
    "api_request_duration_seconds",
    "API 请求延迟分布（秒）",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


async def metrics_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """按路由模板记录请求量和耗时，避免资源 ID 造成标签基数失控。"""
    started_at = time.perf_counter()
    status_code = "500"
    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    finally:
        route_path = getattr(request.scope.get("route"), "path", None)
        endpoint = route_path if isinstance(route_path, str) else "unmatched"
        api_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()
        api_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(time.perf_counter() - started_at)


async def metrics_endpoint() -> Response:
    """返回 Prometheus 文本格式指标。外网入口由 Nginx 明确拒绝。"""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; charset=utf-8",
    )
