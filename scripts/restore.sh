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
ENV_FILE="deploy/env/.env"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE")

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
if [ ! -f "$ENV_FILE" ]; then
    echo "错误: 缺少本地配置文件 $ENV_FILE"
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

POSTGRES_ID=$(basename "$POSTGRES_BACKUP" | sed -E 's/^knowledge_base_(.*)\.sql\.gz$/\1/')
FILES_ID=$(basename "$FILES_BACKUP" | sed -E 's/^files_(.*)\.tar\.gz$/\1/')
if [ "$POSTGRES_ID" != "$FILES_ID" ]; then
    echo "错误: 数据库与文件备份不是同一个备份批次"
    exit 1
fi
echo "备份文件验证通过"

# 停止会写数据库或文件卷的服务；PostgreSQL 和 Redis 保持运行。
"${COMPOSE[@]}" stop web api-server worker

# 恢复前保存数据库和文件卷，便于失败时人工回退。
PRE_RESTORE_DIR="./backups/pre-restore"
PRE_RESTORE_ID="$(date -u +%Y%m%d_%H%M%S)"
bash scripts/backup-postgres.sh "$PRE_RESTORE_DIR/postgres" "$PRE_RESTORE_ID"
bash scripts/backup-files.sh "$PRE_RESTORE_DIR/files" "$PRE_RESTORE_ID"
echo "恢复前备份批次: $PRE_RESTORE_ID"

# 1. 恢复 PostgreSQL
echo ""
echo "=== 步骤1: 恢复 PostgreSQL ==="
echo "开始时间: $(date)"

"${COMPOSE[@]}" exec -T postgres dropdb --if-exists --force -U postgres knowledge_base
"${COMPOSE[@]}" exec -T postgres createdb -U postgres knowledge_base
gunzip -c "${POSTGRES_BACKUP}" | \
  "${COMPOSE[@]}" exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U postgres knowledge_base

echo "PostgreSQL 恢复完成: $(date)"

# 2. 恢复文件存储
echo ""
echo "=== 步骤2: 恢复文件存储 ==="
echo "开始时间: $(date)"

"${COMPOSE[@]}" run --rm --no-deps -T api-server sh -c \
  'find /app/storage -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && tar -xzf - -C /app/storage' \
  < "$FILES_BACKUP"

echo "文件存储恢复完成: $(date)"

# 3. 启动应用；一次性 migrate 服务会先校验/补齐 schema。
echo ""
echo "=== 步骤3: 启动应用 ==="
"${COMPOSE[@]}" up -d

# 4. 验证恢复
echo ""
echo "=== 步骤4: 验证恢复 ==="
echo "检查关键表行数..."

echo -n "users 表: "
"${COMPOSE[@]}" exec -T postgres \
  psql -U postgres -d knowledge_base -t -c "SELECT count(*) FROM users;" 2>/dev/null || echo "无法查询"

echo -n "documents 表: "
"${COMPOSE[@]}" exec -T postgres \
  psql -U postgres -d knowledge_base -t -c "SELECT count(*) FROM documents;" 2>/dev/null || echo "无法查询"

echo ""
echo "============================================================"
echo "  恢复完成: $(date)"
echo "============================================================"
echo ""
echo "后续步骤:"
echo "  1. 运行 bash scripts/health-check.sh"
echo "  2. 验证登录、检索、问答和导出功能"
