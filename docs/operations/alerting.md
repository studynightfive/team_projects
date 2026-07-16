# 告警基线

> 方案第17.4节：监控必须覆盖告警
> 文档版本：1.0

---

## 一、告警架构

```
API Server -> Prometheus 指标 -> Alertmanager -> 通知渠道
```

- Prometheus 以 15 秒间隔抓取 `/api/v1/metrics` 端点
- 告警规则定义在 `deploy/prometheus/alert.rules.yml`
- Alertmanager 负责告警路由和通知

---

## 二、严重告警（P0，需立即响应）

| 告警名称 | 触发条件 | 持续时间 | 说明 |
|---|---|---|---|
| APIServiceDown | `up{job="api-server"} == 0` | 1 分钟 | API Server 停止响应 |
| DatabaseDown | `up{job="postgres"} == 0` | 1 分钟 | PostgreSQL 不可用 |
| WorkerHeartbeatTimeout | Worker 心跳超过 60 秒 | 2 分钟 | 文档处理和导出任务停滞 |
| DiskUsageHigh | 文件存储使用超过 90% | 5 分钟 | 上传和导出可能失败 |
| APIErrorRateHigh | 5xx 错误占比超过 10% | 5 分钟 | 后端服务异常 |

**通知方式**：即时通知（邮件、企业微信、钉钉等）

---

## 三、警告告警（P1，需在 1 小时内关注）

| 告警名称 | 触发条件 | 持续时间 | 说明 |
|---|---|---|---|
| APILatencyHigh | P95 延迟超过 5 秒 | 5 分钟 | 性能下降 |
| TaskQueueBacklog | 任务队列积压超过 20 个 | 5 分钟 | 处理能力不足 |
| RetrievalNoHitRateHigh | 无命中率超过 50% | 5 分钟 | 索引可能异常 |
| ModelRequestFailureRateHigh | 模型请求失败率超过 5% | 5 分钟 | 模型服务异常 |
| RedisMemoryHigh | Redis 内存超过 80% | 5 分钟 | 缓存或队列配置不足 |
| SlowQueriesHigh | 慢查询超过 10 个/分钟 | 1 分钟 | 缺少索引或查询低效 |

**通知方式**：聚合通知（每小时汇总一次）

---

## 四、通知渠道配置

### 邮件通知

```yaml
# Alertmanager 配置示例
receivers:
  - name: team-email
    email_configs:
      - to: team@example.com
        from: alertmanager@example.com
```

### 企业微信通知

```yaml
receivers:
  - name: team-wechat
    wechat_configs:
      - corp_id: your-corp-id
        to_user: "@all"
```

---

## 五、如何添加新告警规则

1. 编辑 `deploy/prometheus/alert.rules.yml`
2. 在对应 severity 组下添加新的 `alert` 规则
3. 重启 Prometheus 使规则生效

示例：

```yaml
- alert: NewAlertName
  expr: your_metric > threshold
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "告警摘要"
    description: "告警详细描述"
```

---

## 六、告警验证

新告警规则上线后，建议在测试环境运行至少 1 天，确认：

- 告警条件正确触发
- 不产生大量误报
- 通知渠道正常送达
- 告警恢复后自动关闭