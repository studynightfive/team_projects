# 备份与恢复指南

## 一致性备份

统一入口会短暂停止 Web、API 和 Worker 的业务写入，为 PostgreSQL 和共享文件卷生成同一批次 ID，并输出 SHA256 清单；结束或异常退出时会重新启动服务。

```bash
bash scripts/backup.sh
bash scripts/backup.sh /mnt/backups
```

输出结构：

```text
backups/
├─ postgres/knowledge_base_<backup_id>.sql.gz
├─ files/files_<backup_id>.tar.gz
└─ backup_<backup_id>.sha256
```

单独的 `backup-postgres.sh` 和 `backup-files.sh` 只适合诊断或已有外部一致性窗口的场景；日常任务和定时任务应调用 `backup.sh`。

示例 crontab（UTC/主机时区由运维统一确认）：

```cron
0 2 * * * cd /path/to/project && bash scripts/backup.sh /mnt/backups
```

脚本保留最近 7 天文件。长期周/月备份和异地复制必须由外部备份系统负责；仓库不会自动宣称已实现。

## 恢复

恢复会删除并重建业务数据库、清空共享文件卷，是破坏性操作。只在维护窗口、确认目标 Compose 项目和备份批次后执行：

```bash
bash scripts/restore.sh \
  ./backups/postgres/knowledge_base_20260720_120000.sql.gz \
  ./backups/files/files_20260720_120000.tar.gz
```

脚本会：

1. 校验 gzip/tar 完整性和两个文件的批次 ID。
2. 停止业务写入服务。
3. 在 `backups/pre-restore/` 保存当前数据库和文件卷。
4. 重建数据库并恢复文件卷。
5. 运行迁移、启动全部服务并输出关键表计数。

恢复后必须执行：

```bash
bash scripts/health-check.sh
```

随后用代表性账号验证登录、权限、检索、问答、引用和导出。仓库尚未进行大规模恢复演练，因此恢复时间和 RPO/RTO 不能凭空承诺。
