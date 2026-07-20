#!/bin/bash
# ============================================================
# 智能知识库平台 - 文件存储备份脚本
# 用途：备份原始文件、Markdown、assets 和 manifest
# 用法：bash scripts/backup-files.sh [backup_dir] [backup_id]
# 退出码：0 = 成功, 1 = 失败
# ============================================================

set -euo pipefail

# 备份目录（默认 ./backups/files）
BACKUP_DIR="${1:-./backups/files}"
# 时间戳（UTC，与 PostgreSQL 备份对齐）
TIMESTAMP="${2:-$(date -u +%Y%m%d_%H%M%S)}"
# 备份归档文件
BACKUP_FILE="${BACKUP_DIR}/files_${TIMESTAMP}.tar.gz"
TEMP_FILE="${BACKUP_FILE}.tmp"
COMPOSE_FILE="deploy/docker-compose.yml"
ENV_FILE="deploy/env/.env"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

echo "============================================================"
echo "  文件存储备份"
echo "  $(date)"
echo "============================================================"
echo ""

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

if [ ! -f "$ENV_FILE" ]; then
    echo "错误: 缺少本地配置文件 $ENV_FILE"
    exit 1
fi

# 从 Compose 挂载的真实命名卷创建归档，避免误备份宿主空目录。
echo "创建归档..."
trap 'rm -f "$TEMP_FILE"' EXIT
"${COMPOSE[@]}" run --rm --no-deps -T api-server \
  tar -czf - -C /app/storage . > "$TEMP_FILE"
mv "$TEMP_FILE" "$BACKUP_FILE"
trap - EXIT

# 验证归档完整性
echo "验证归档..."
if tar -tzf "${BACKUP_FILE}" > /dev/null 2>&1; then
    BACKUP_SIZE=$(ls -lh "${BACKUP_FILE}" | awk '{print $5}')
    echo "备份成功: ${BACKUP_FILE} (${BACKUP_SIZE})"
else
    echo "备份失败: 归档文件损坏"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# 清理过期备份（7天以上）
echo "清理过期备份..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "files_*.tar.gz" -mtime +7 -delete -print | wc -l)
if [ "${DELETED_COUNT}" -gt 0 ]; then
    echo "已清理 ${DELETED_COUNT} 个过期备份"
fi

echo ""
echo "备份完成: $(date)"
echo "============================================================"
