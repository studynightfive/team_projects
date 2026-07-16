# 备份与恢复指南

> 方案第17.5节：备份和恢复
> 文档版本：1.0

---

## 一、备份策略

### 备份范围

| 备份内容 | 方式 | 频率 | 保留期 |
|---|---|---|---|
| PostgreSQL 数据库 | `pg_dump` + gzip | 每天 | 7天每日 + 4周每周 + 3月每月 |
| 文件存储 | `tar.gz` 归档 | 每天 | 同 PostgreSQL |
| 向量索引 | 不备份，可通过文档重建 | - | - |

### 备份内容详解

- PostgreSQL：全部业务数据（用户、角色、权限、知识库、文档、会话、消息、审计日志）
- 文件存储：`storage/` 目录下的原始文件、Markdown、assets、manifest
- 不备份：向量索引（可通过文档重建）、Secret（通过环境变量管理）

---

## 二、备份脚本

### PostgreSQL 备份

```bash
# 执行备份
bash scripts/backup-postgres.sh

# 指定备份目录
bash scripts/backup-postgres.sh /mnt/backups/postgres
```

备份文件命名：`knowledge_base_YYYYMMDD_HHMMSS.sql.gz`

### 文件存储备份

```bash
# 执行备份
bash scripts/backup-files.sh

# 指定备份目录
bash scripts/backup-files.sh /mnt/backups/files
```

备份文件命名：`files_YYYYMMDD_HHMMSS.tar.gz`

### 统一备份

```bash
# 创建统一备份目录
BACKUP_DIR="./backups/$(date -u +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"

# 同时执行两个备份
bash scripts/backup-postgres.sh "${BACKUP_DIR}/postgres"
bash scripts/backup-files.sh "${BACKUP_DIR}/files"

echo "统一备份完成: ${BACKUP_DIR}"
```

### 定时备份（crontab）

```bash
# 每天凌晨 2 点执行备份
0 2 * * * cd /path/to/project && bash scripts/backup-postgres.sh && bash scripts/backup-files.sh
```

---

## 三、恢复流程

### 前置条件

- Docker 环境正常运行
- 备份文件（`.sql.gz` 和 `.tar.gz`）可用
- 备份文件完整性已验证

### 恢复步骤

```bash
# 1. 停止 API 和 Worker 服务（避免数据写入冲突）
docker compose -f deploy/docker-compose.yml stop api-server worker

# 2. 执行恢复
bash scripts/restore.sh \
  ./backups/postgres/knowledge_base_20260715_120000.sql.gz \
  ./backups/files/files_20260715_120000.tar.gz

# 3. 启动服务
docker compose -f deploy/docker-compose.yml start api-server worker

# 4. 等待健康检查通过
docker compose -f deploy/docker-compose.yml ps

# 5. 验证恢复
bash scripts/health-check.sh
```

### 恢复后验证

| 验证项 | 方法 | 预期 |
|---|---|---|
| 用户表行数 | `SELECT count(*) FROM users` | 与备份时一致 |
| 文档表行数 | `SELECT count(*) FROM documents` | 与备份时一致 |
| 登录功能 | 访问登录页面 | 正常 |
| 检索功能 | 执行检索查询 | 返回结果 |
| 问答功能 | 发起问答 | 正常返回 |
| 导出功能 | 执行导出 | 文件生成正常 |

### 预期恢复时间

| 数据规模 | 预估恢复时间 |
|---|---|
| 小型（< 1GB） | 5-10 分钟 |
| 中型（1-10GB） | 10-30 分钟 |
| 大型（> 10GB） | 30 分钟 - 2 小时 |

---

## 四、常见问题

### 备份失败

**问题**：`pg_dump` 连接被拒绝

**解决**：确认 PostgreSQL 容器正在运行
```bash
docker compose -f deploy/docker-compose.yml ps postgres
```

### 恢复失败

**问题**：恢复后数据不一致

**解决**：
1. 检查备份文件时间戳，确保 PostgreSQL 和文件存储备份是同一时间点
2. 如果文件存储备份较新，可以从备份恢复后重建向量索引

### 磁盘空间不足

**问题**：备份文件占用过多磁盘

**解决**：
1. 备份脚本自动清理 7 天前的备份
2. 手动清理：`find ./backups -name "*.gz" -mtime +7 -delete`
3. 考虑将备份存储到外部存储

---

## 五、恢复演练记录模板

每次恢复演练后填写：

```markdown
# 恢复演练记录

- 日期：2026-XX-XX
- 执行人：员工6
- 验证人：员工3

## 演练环境
- 环境：测试环境
- PostgreSQL 备份：knowledge_base_2026XXXX_XXXXXX.sql.gz
- 文件备份：files_2026XXXX_XXXXXX.tar.gz

## 恢复步骤

| 步骤 | 开始时间 | 结束时间 | 耗时 | 状态 |
|---|---|---|---|---|
| 停止服务 | | | | |
| 恢复数据库 | | | | |
| 恢复文件 | | | | |
| 启动服务 | | | | |
| 验证恢复 | | | | |

## 验证结果

| 验证项 | 状态 |
|---|---|
| 用户表行数 | |
| 文档表行数 | |
| 登录功能 | |
| 检索功能 | |
| 问答功能 | |

## 总恢复时间
XX 分钟

## 问题和解决方案
1. 问题：...
   解决方案：...
```