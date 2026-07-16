# 监控指南

> 方案第17.4节：监控必须覆盖健康检查
> 文档版本：1.0

---

## 一、监控架构

```
FastAPI App -> /api/v1/metrics -> Prometheus -> Grafana 仪表板
                                      |
                                 Alertmanager -> 通知渠道
```

## 二、指标列表

### API 请求指标

| 指标名称 | 类型 | 说明 |
|---|---|---|
| `api_requests_total` | Counter | API 请求总量（按方法、端点、状态码） |
| `api_request_duration_seconds` | Histogram | API 请求延迟分布 |

### SSE 连接指标

| 指标名称 | 类型 | 说明 |
|---|---|---|
| `sse_connections_active` | Gauge | 当前活跃 SSE 连接数 |
| `sse_connections_total` | Counter | SSE 连接总数（按状态） |

### 文档任务指标

| 指标名称 | 类型 | 说明 |
|---|---|---|
| `document_tasks_total` | Counter | 文档任务总数（按状态、阶段） |
| `document_task_queue_length` | Gauge | 任务队列当前长度 |
| `document_task_wait_seconds` | Histogram | 任务等待时间分布 |
| `document_task_duration_seconds` | Histogram | 各阶段处理耗时 |

### 检索指标

| 指标名称 | 类型 | 说明 |
|---|---|---|
| `retrieval_requests_total` | Counter | 检索请求总数（按模式、状态） |
| `retrieval_latency_seconds` | Histogram | 检索延迟分布 |
| `retrieval_no_hits_total` | Counter | 无命中检索次数 |

### 模型请求指标

| 指标名称 | 类型 | 说明 |
|---|---|---|
| `model_requests_total` | Counter | 模型请求总数（按模型ID、状态） |
| `model_request_duration_seconds` | Histogram | 模型请求耗时分布 |
| `model_tokens_total` | Counter | Token 使用量（按 input/output） |

### 导出任务指标

| 指标名称 | 类型 | 说明 |
|---|---|---|
| `export_tasks_total` | Counter | 导出任务总数（按格式、状态） |
| `export_task_duration_seconds` | Histogram | 导出任务耗时分布 |

### 基础设施指标

| 指标名称 | 类型 | 说明 |
|---|---|---|
| `db_connections_active` | Gauge | 活跃数据库连接数 |
| `db_query_duration_seconds` | Histogram | 慢查询耗时分布 |
| `redis_connected_clients` | Gauge | Redis 连接数 |
| `redis_memory_used_bytes` | Gauge | Redis 内存使用 |
| `file_storage_used_bytes` | Gauge | 文件存储使用量 |

---

## 三、健康检查端点

| 端点 | 用途 | 成功 | 失败 |
|---|---|---|---|
| `GET /api/v1/health/live` | 存活检查 | 200 | - |
| `GET /api/v1/health/ready` | 就绪检查 | 200 | 503 |
| `GET /api/v1/metrics` | Prometheus 指标 | 200 | - |

### 就绪检查项

- `database`：PostgreSQL 连接（SELECT 1）
- `redis`：Redis 连接（PING）
- `storage`：文件存储目录可读写

---

## 四、如何查看指标

### 本地开发

```bash
# 直接访问指标端点
curl http://localhost:8000/api/v1/metrics

# 或通过 Nginx 代理
curl http://localhost/api/v1/metrics
```

### 生产环境

指标端点通过 Nginx 保护，仅内部网络可访问：

```nginx
location /api/v1/metrics {
    allow 10.0.0.0/8;
    deny all;
    proxy_pass http://api_server;
}
```

---

## 五、如何添加新指标

1. 在 `backend/app/common/metrics.py` 中定义新指标
2. 在对应的业务模块中更新指标值
3. 如需告警，在 `deploy/prometheus/alert.rules.yml` 中添加规则

```python
# 示例：添加新指标
from app.common.metrics import api_requests_total

# 在业务代码中更新
api_requests_total.labels(
    method="POST",
    endpoint="/api/v1/documents",
    status_code="201",
).inc()
```

---

## 六、日志格式

所有日志使用 JSON 格式输出，包含以下字段：

- `timestamp`：ISO 8601 格式时间戳
- `level`：日志级别
- `request_id`：请求唯一标识
- `user_id`：当前用户（如有）
- `action`：操作类型
- `resource_type`：资源类型
- `resource_id`：资源 ID
- `result`：操作结果
- `duration_ms`：请求耗时

日志绝不包含：Authorization 头、密码、密钥、连接字符串、完整请求体。