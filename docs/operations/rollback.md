# 回滚方案

## 决策原则

1. 应用缺陷优先回滚 Web/API/Worker 镜像，不先改数据。
2. 只有在确认迁移不向后兼容或数据已损坏时，才恢复数据库和文件卷。
3. 数据恢复会丢失备份之后的写入，必须由负责人确认维护窗口和影响范围。

## 应用镜像回滚

`scripts/build-release.sh` 要求干净工作区，并为镜像写入版本、提交 SHA 和构建时间标签。将 `.env` 中 `APP_IMAGE_TAG` 改为已验证的旧版本后执行：

```bash
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml up -d --no-build
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml ps
bash scripts/health-check.sh
```

Compose 会先运行迁移任务；因此旧应用能否连接当前 schema 必须在发布前验证，不能仅凭“镜像已启动”判断可回滚。

## 数据恢复

使用同一批次 ID 的数据库和文件备份：

```bash
bash scripts/restore.sh \
  ./backups/postgres/knowledge_base_<backup_id>.sql.gz \
  ./backups/files/files_<backup_id>.tar.gz
```

恢复后执行健康检查和代表性业务验证，并记录丢失的写入时间范围。详细安全边界见 [备份与恢复](backup-restore.md)。
