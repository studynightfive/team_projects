# 运维文档索引

> 文档版本：1.0
> 维护人：员工6（测试与平台工程）

---

## 文档列表

| 文档 | 说明 | 适用场景 |
|---|---|---|
| [deployment.md](deployment.md) | 部署指南 | 首次部署、环境搭建 |
| [release-checklist.md](release-checklist.md) | 发布检查清单 | 每次发布前逐项确认 |
| [rollback.md](rollback.md) | 回滚方案 | 发布失败时恢复 |
| [monitoring.md](monitoring.md) | 监控指南 | 查看指标、日志、健康检查 |
| [alerting.md](alerting.md) | 告警基线 | 配置告警规则 |
| [backup-restore.md](backup-restore.md) | 备份与恢复指南 | 数据备份和灾难恢复 |
| [testing.md](testing.md) | 测试指南 | 运行测试、查看覆盖率 |

---

## 发布记录

| 版本 | 日期 | 发布人 | 说明 |
|---|---|---|---|
| [v1.0.0](release-notes/v1.0.0.md) | 待定 | 员工6 | 首次正式发布 |

---

## 快速导航

### 我要部署项目

1. [deployment.md](deployment.md) - 快速启动
2. 配置 `deploy/env/.env`

### 我要发布新版本

1. [release-checklist.md](release-checklist.md) - 逐项检查
2. `bash scripts/build-release.sh v1.0.0`
3. 部署后验证

### 我遇到了问题

1. [deployment.md](deployment.md) - 故障排查章节
2. [rollback.md](rollback.md) - 回滚步骤

### 我要查看系统状态

1. [monitoring.md](monitoring.md) - 指标和日志
2. `bash scripts/health-check.sh`
3. `curl /api/v1/metrics`

### 我要备份数据

1. [backup-restore.md](backup-restore.md) - 备份策略
2. `bash scripts/backup-postgres.sh`
3. `bash scripts/backup-files.sh`