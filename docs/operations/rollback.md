# 回滚方案

> 方案第17.2节：发布失败时优先回滚应用镜像
> 文档版本：1.0

---

## 一、回滚决策树

```
发布后发现异常
├── 应用层问题（API 错误、前端异常）
│   └── 回滚应用镜像（5分钟内）
├── 数据库迁移问题（数据错误、性能下降）
│   ├── 迁移向后兼容 -> 回滚应用镜像，数据库不回滚
│   └── 迁移不兼容 -> 回滚应用镜像 + 恢复数据库备份
└── 数据损坏或丢失
    └── 回滚应用镜像 + 恢复数据库和文件备份
```

---

## 二、应用镜像回滚（优先执行）

### 步骤

1. 将 `docker-compose.yml` 中的镜像标签改回上一个稳定版本
2. 滚动更新服务：
   ```bash
   docker compose -f deploy/docker-compose.yml up -d --no-deps api-server worker web
   ```
3. 等待健康检查通过：
   ```bash
   docker compose -f deploy/docker-compose.yml ps
   bash scripts/health-check.sh
   ```
4. 验证核心功能：
   - 登录、检索、问答、导出正常

### 预期时间

5 分钟内完成。

---

## 三、数据库回滚（仅在必要时执行）

### 前置判断

优先回滚应用镜像，数据库不回滚。如果新版本应用的数据库迁移是向后兼容的（只增列不删列、只加表不删表），则不需要回滚数据库。

### 回滚步骤

1. 从最近的备份恢复数据库：
   ```bash
   bash scripts/restore.sh \
     ./backups/postgres/knowledge_base_YYYYMMDD_HHMMSS.sql.gz \
     ./backups/files/files_YYYYMMDD_HHMMSS.tar.gz
   ```
2. 验证数据完整性：
   ```bash
   docker compose -f deploy/docker-compose.yml exec -T postgres \
     psql -U postgres -d knowledge_base -c "SELECT count(*) FROM users;"
   docker compose -f deploy/docker-compose.yml exec -T postgres \
     psql -U postgres -d knowledge_base -c "SELECT count(*) FROM documents;"
   ```
3. 启动应用服务：
   ```bash
   docker compose -f deploy/docker-compose.yml up -d api-server worker web
   ```

### 预期时间

取决于数据规模，10-30 分钟。

---

## 四、回滚演练

第8周在测试环境执行，记录回滚耗时。

1. 部署新版本镜像到测试环境
2. 模拟发布后发现问题
3. 执行回滚流程
4. 验证回滚后服务正常
5. 记录回滚耗时

---

## 五、回滚演练记录模板

```markdown
# 回滚演练记录

- 日期：2026-XX-XX
- 执行人：员工6
- 验证人：员工3

## 演练步骤

| 步骤 | 开始时间 | 结束时间 | 耗时 | 状态 |
|---|---|---|---|---|
| 部署新版本 | | | | |
| 发现问题 | | | | |
| 决定回滚 | | | | |
| 回滚应用镜像 | | | | |
| 健康检查 | | | | |
| 功能验证 | | | | |

## 总回滚时间
XX 分钟

## 回滚后验证

| 验证项 | 状态 |
|---|---|
| 登录 | |
| 检索 | |
| 问答 | |
| 导出 | |

## 问题和解决方案
```

---

## 六、应急联系人

| 角色 | 姓名 | 联系方式 |
|---|---|---|
| 发布执行人 | 员工6 | - |
| 后端备份 | 员工3 | - |
| 前端负责人 | 员工1 | - |