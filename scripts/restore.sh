#!/bin/bash
# ============================================================
# 智能知识库平台 - 恢复脚本
# 用途：恢复 PostgreSQL 数据库和文件存储
# 用法：bash scripts/restore.sh <postgres_backup_file> <files_backup_file>
# 退出码：0 = 成功, 1 = 失败
# ============================================================

set -euo pipefail

# 参数检查
if [ $# -lt 2 ]; then
    echo "用法: bash scripts/restore.sh <postgres_backup_file> <files_backup_file>"
    echo ""
    echo "示例:"
    echo "  bash scripts/restore.sh ./backups/postgres/knowledge_base_20260715_120000.sql.gz ./backups/files/files_20260715_120000.tar.gz"
    exit 1
fi

POSTGRES_BACKUP="${1}"
FILES_BACKUP="${2}"
COMPOSE_FILE="deploy/docker-compose.yml"

echo "============================================================"
echo "  数据恢复"
echo "  $(date)"
echo "============================================================"
echo ""

# 检查备份文件是否存在
if [ ! -f "${POSTGRES_BACKUP}" ]; then
    echo "错误: PostgreSQL 备份文件不存在: ${POSTGRES_BACKUP}"
    exit 1
fi

if [ ! -f "${FILES_BACKUP}" ]; then
    echo "错误: 文件备份不存在: ${FILES_BACKUP}"
    exit 1
fi

# 验证备份文件完整性
echo "验证备份文件..."
if ! gzip -t "${POSTGRES_BACKUP}"; then
    echo "错误: PostgreSQL 备份文件损坏"
    exit 1
fi
if ! tar -tzf "${FILES_BACKUP}" > /dev/null 2>&1; then
    echo "错误: 文件备份归档损坏"
    exit 1
fi
echo "备份文件验证通过"

# 1. 恢复 PostgreSQL
echo ""
echo "=== 步骤1: 恢复 PostgreSQL ==="
echo "开始时间: $(date)"

gunzip -c "${POSTGRES_BACKUP}" | \
  docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U postgres knowledge_base

echo "PostgreSQL 恢复完成: $(date)"

# 2. 恢复文件存储
echo ""
echo "=== 步骤2: 恢复文件存储 ==="
echo "开始时间: $(date)"

# 备份当前存储（以防恢复失败）
if [ -d "./storage" ] && [ "$(ls -A ./storage 2>/dev/null)" ]; then
    STORAGE_BACKUP="./storage_backup_$(date -u +%Y%m%d_%H%M%S)"
    echo "备份当前存储到: ${STORAGE_BACKUP}"
    mv ./storage "${STORAGE_BACKUP}"
fi

mkdir -p ./storage
tar -xzf "${FILES_BACKUP}" -C ./storage/

echo "文件存储恢复完成: $(date)"

# 3. 重建向量索引
echo ""
echo "=== 步骤3: 重建向量索引 ==="
echo "注意: 向量索引需要手动触发重建，预计耗时取决于文档数量"
echo "重建命令: docker compose exec api-server uv run python -m backend.scripts.reindex_vectors"

# 4. 验证恢复
echo ""
echo "=== 步骤4: 验证恢复 ==="
echo "检查关键表行数..."

echo -n "users 表: "
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U postgres -d knowledge_base -t -c "SELECT count(*) FROM users;" 2>/dev/null || echo "无法查询"

echo -n "documents 表: "
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  psql -U postgres -d knowledge_base -t -c "SELECT count(*) FROM documents;" 2>/dev/null || echo "无法查询"

echo ""
echo "============================================================"
echo "  恢复完成: $(date)"
echo "============================================================"
echo ""
echo "后续步骤:"
echo "  1. 重建向量索引（如需要）"
echo "  2. 验证登录功能"
echo "  3. 验证检索功能"
echo "  4. 验证问答功能"
echo "  5. 验证导出功能"