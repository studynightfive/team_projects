# 监控指南

## 当前真实能力

- `/api/v1/health/live`：只表示 API 进程存活。
- `/api/v1/health/ready`：并发检查 PostgreSQL `SELECT 1`、Redis `PING` 和存储目录可写性；任一失败返回 503。
- `/api/v1/metrics`：提供 `api_requests_total` 与 `api_request_duration_seconds`，端点标签使用路由模板避免高基数。

当前应用没有采集数据库、Redis、磁盘、Worker 心跳、队列长度、检索或模型调用指标。部署相应 exporter/采集逻辑前，不应为这些信号配置告警。

## 访问边界

Nginx 对公网 `/api/v1/metrics` 固定返回 404。可选 Prometheus 必须加入 Docker 网络 `kb-network`，并直接抓取：

```text
http://api-server:8000/api/v1/metrics
```

仓库提供 [Prometheus 配置](../../deploy/prometheus/prometheus.yml) 和 [告警规则](../../deploy/prometheus/alert.rules.yml)，但默认 Compose 不部署 Prometheus、Alertmanager 或 Grafana。

## 日志

应用输出结构化 JSON 日志并携带规范化 `request_id`。日志不得包含 Authorization、Cookie、密码、API Key、连接字符串或完整敏感请求体。

排查示例：

```bash
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml logs --tail=100 api-server worker
```
