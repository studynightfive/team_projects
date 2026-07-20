#!/bin/bash
# ============================================================
# 智能知识库平台 - 数据库和文件备份入口
# 用法：bash scripts/backup.sh [backup_dir]
# ============================================================

set -euo pipefail

BACKUP_ROOT="${1:-./backups}"
BACKUP_ID="$(date -u +"%Y%m%d_%H%M%S")"
COMPOSE=(docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml)
POSTGRES_BACKUP="$BACKUP_ROOT/postgres/knowledge_base_${BACKUP_ID}.sql.gz"
FILES_BACKUP="$BACKUP_ROOT/files/files_${BACKUP_ID}.tar.gz"
MANIFEST="$BACKUP_ROOT/backup_${BACKUP_ID}.sha256"

if [ ! -f deploy/env/.env ]; then
    echo "错误: 缺少本地配置文件 deploy/env/.env"
    exit 1
fi

# 只暂停当前正在运行的写入服务，并在退出时恢复原状态。
RUNNING_SERVICES=()
for service in web api-server worker; do
    if "${COMPOSE[@]}" ps --services --status running | grep -Fxq "$service"; then
        RUNNING_SERVICES+=("$service")
    fi
done

restore_services() {
    if [ "${#RUNNING_SERVICES[@]}" -gt 0 ]; then
        "${COMPOSE[@]}" up -d --no-deps "${RUNNING_SERVICES[@]}"
    fi
}
trap restore_services EXIT

if [ "${#RUNNING_SERVICES[@]}" -gt 0 ]; then
    "${COMPOSE[@]}" stop "${RUNNING_SERVICES[@]}"
fi

bash scripts/backup-postgres.sh "$BACKUP_ROOT/postgres" "$BACKUP_ID"
bash scripts/backup-files.sh "$BACKUP_ROOT/files" "$BACKUP_ID"

(
    cd "$BACKUP_ROOT"
    sha256sum "postgres/$(basename "$POSTGRES_BACKUP")" \
        "files/$(basename "$FILES_BACKUP")" > "$(basename "$MANIFEST")"
)

restore_services
trap - EXIT

# 与 7 天归档保留期同步清理校验清单。
find "$BACKUP_ROOT" -maxdepth 1 -name "backup_*.sha256" -mtime +7 -delete

echo "一致性备份已完成: $BACKUP_ID"
echo "校验清单: $MANIFEST"
