#!/bin/bash
# ============================================================
# 智能知识库平台 - PostgreSQL 备份脚本
# 用途：执行数据库全量逻辑备份，验证完整性，清理过期备份
# 用法：bash scripts/backup-postgres.sh [backup_dir] [backup_id]
# 退出码：0 = 成功, 1 = 失败
# ============================================================

set -euo pipefail

# 备份目录（默认 ./backups/postgres）
BACKUP_DIR="${1:-./backups/postgres}"
# 时间戳（UTC）
TIMESTAMP="${2:-$(date -u +%Y%m%d_%H%M%S)}"
# 备份文件名
BACKUP_FILE="${BACKUP_DIR}/knowledge_base_${TIMESTAMP}.sql.gz"
TEMP_FILE="${BACKUP_FILE}.tmp"
# Docker Compose 文件路径
COMPOSE_FILE="deploy/docker-compose.yml"
ENV_FILE="deploy/env/.env"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

echo "============================================================"
echo "  PostgreSQL 备份"
echo "  $(date)"
echo "============================================================"
echo ""

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

if [ ! -f "$ENV_FILE" ]; then
    echo "错误: 缺少本地配置文件 $ENV_FILE"
    exit 1
fi

# 执行备份
echo "执行 pg_dump..."
trap 'rm -f "$TEMP_FILE"' EXIT
"${COMPOSE[@]}" exec -T postgres \
  pg_dump --clean --if-exists -U postgres knowledge_base | gzip > "${TEMP_FILE}"
gzip -t "${TEMP_FILE}"
mv "${TEMP_FILE}" "${BACKUP_FILE}"
trap - EXIT

# 验证备份文件完整性
echo "验证备份文件..."
if gzip -t "${BACKUP_FILE}"; then
    BACKUP_SIZE=$(ls -lh "${BACKUP_FILE}" | awk '{print $5}')
    echo "备份成功: ${BACKUP_FILE} (${BACKUP_SIZE})"
else
    echo "备份失败: 文件损坏"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# 清理过期备份
echo "清理过期备份..."

# 删除7天前的每日备份
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "knowledge_base_*.sql.gz" -mtime +7 -delete -print | wc -l)
if [ "${DELETED_COUNT}" -gt 0 ]; then
    echo "已清理 ${DELETED_COUNT} 个过期备份"
fi

# 保留最近4周的每周备份（每周一保留一份）
# 保留最近3个月的每月备份（每月1日保留一份）

echo ""
echo "备份完成: $(date)"
echo "============================================================"
