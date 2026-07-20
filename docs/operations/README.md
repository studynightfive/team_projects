# 运维文档索引

本文档集描述当前仓库可以实际执行的本地/单机 Compose 流程。默认编排不是完整生产平台：TLS、Prometheus、Alertmanager、Grafana、对象存储和外部备份介质需要由部署环境另行提供。

| 文档 | 说明 |
|---|---|
| [deployment.md](deployment.md) | 环境配置、启动、迁移和故障排查 |
| [testing.md](testing.md) | 前后端门禁与隔离 Docker 测试 |
| [monitoring.md](monitoring.md) | 真实可用的健康检查和 HTTP 指标 |
| [alerting.md](alerting.md) | 当前可用告警与待补 exporter 边界 |
| [backup-restore.md](backup-restore.md) | 数据库与文件卷的一致性备份、恢复 |
| [rollback.md](rollback.md) | 镜像回滚和有损数据恢复决策 |
| [release-checklist.md](release-checklist.md) | 发布前强制检查项 |

常用命令：

```bash
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml up -d --build
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml exec api-server /app/backend/.venv/bin/python scripts/bootstrap_admin.py  # 仅新环境首次交互执行
bash scripts/health-check.sh
bash scripts/backup.sh
docker compose -f deploy/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
```

`make clean` 只移除容器并保留数据卷。只有显式执行 `make purge-data CONFIRM=delete-data` 才删除本地数据库和文件卷。
