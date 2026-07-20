# 告警基线

当前规则文件只定义能够由真实指标驱动的三项告警：

| 告警 | 条件 | 持续时间 |
|---|---|---:|
| `APIServiceDown` | Prometheus 无法抓取 API | 1 分钟 |
| `APIErrorRateHigh` | 5xx 比例超过 10% | 5 分钟 |
| `APILatencyHigh` | HTTP P95 延迟超过 5 秒 | 5 分钟 |

默认 Compose 不部署 Prometheus 或 Alertmanager。启用规则前必须自行部署监控栈、将 Prometheus 加入 `kb-network`，并验证内部指标抓取和通知渠道。

数据库、Redis、磁盘、Worker、队列和模型服务告警尚未实现，因为仓库没有对应 exporter 或可靠采集逻辑。正确顺序是先采集并验证指标，再添加规则和通知；不得用永远为零的占位指标制造“已覆盖”假象。
