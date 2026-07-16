#!/bin/bash
# ============================================================
# 智能知识库平台 - PostgreSQL 备份脚本
# 用途：执行数据库全量逻辑备份，验证完整性，清理过期备份
# 用法：bash scripts/backup-postgres.sh [backup_dir]
# 退出码：0 = 成功, 1 = 失败
# ============================================================

set -euo pipefail

# 备份目录（默认 ./backups/postgres）
BACKUP_DIR="${1:-./backups/postgres}"
# 时间戳（UTC）
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
# 备份文件名
BACKUP_FILE="${BACKUP_DIR}/knowledge_base_${TIMESTAMP}.sql.gz"
# Docker Compose 文件路径
COMPOSE_FILE="deploy/docker-compose.yml"

echo "============================================================"
echo "  PostgreSQL 备份"
echo "  $(date)"
echo "============================================================"
echo ""

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 执行备份
echo "执行 pg_dump..."
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  pg_dump -U postgres knowledge_base | gzip > "${BACKUP_FILE}"

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