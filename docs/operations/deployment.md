# 智能知识库平台 - 部署指南

> 文档版本：1.0
> 对应方案：第17节 CI/CD、监控与发布
> 执行人要求：可由非作者（如员工3）独立执行

---

## 一、环境要求

| 软件 | 最低版本 | 说明 |
|---|---|---|
| Docker Engine | 27.5.1 | 容器运行时 |
| Docker Compose | 2.32.4 | 容器编排（Compose V2） |
| Git | 2.43.0 | 版本管理（如需 clone 仓库） |
| 操作系统 | Ubuntu Server 24.04.3 LTS x86_64 | 生产环境推荐 |
| 磁盘空间 | 至少 20GB 可用 | 镜像、数据库和文件存储 |

---

## 二、快速启动（开发环境）

### 1. 克隆仓库

```bash
git clone <repo-url>
cd knowledge-base-platform
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp deploy/env/.env.example deploy/env/.env

# 编辑 .env 文件，填入实际值
# 开发环境可以使用默认值，但生产环境必须修改
nano deploy/env/.env
```

必须修改的变量：
- `POSTGRES_PASSWORD`：数据库密码（不要使用默认值）
- `SECRET_KEY`：JWT 签名密钥（使用 `openssl rand -hex 32` 生成）

### 3. 启动全部服务

```bash
# 构建并启动全部 5 个服务
docker compose -f deploy/docker-compose.yml up -d

# 查看服务状态
docker compose -f deploy/docker-compose.yml ps
```

### 4. 验证健康检查

```bash
# 方式一：使用健康检查脚本
bash scripts/health-check.sh

# 方式二：手动检查
# Web 服务
curl http://localhost/

# API Server 存活检查
curl http://localhost/api/v1/health/live

# API Server 就绪检查
curl http://localhost/api/v1/health/ready
```

预期输出：
- `GET /` 返回前端 SPA 页面（HTML）
- `GET /api/v1/health/live` 返回 `{"status":"ok","timestamp":"..."}`
- `GET /api/v1/health/ready` 返回 `{"status":"ok","checks":{...},"timestamp":"..."}`

---

## 三、环境变量说明

| 变量名 | 用途 | 默认值 | 是否必需 | 安全级别 |
|---|---|---|---|---|
| `POSTGRES_PASSWORD` | PostgreSQL 数据库密码 | 无 | 是 | 敏感，不可提交 Git |
| `SECRET_KEY` | JWT 签名密钥 | 无 | 是 | 敏感，不可提交 Git |
| `DEBUG` | 调试模式开关 | `false` | 否 | 普通 |
| `MODEL_API_KEY` | LLM API 密钥 | 空 | 否（无 AI 功能时） | 敏感，不可提交 Git |

---

## 四、服务列表和端口说明

| 服务 | 容器名 | 端口 | 对外暴露 | 健康检查 |
|---|---|---|---|---|
| Web (Nginx) | `kb-web` | 80 | 是 | `curl http://localhost:80/` |
| API Server | `kb-api-server` | 8000 | 否（仅内部） | `curl http://localhost:80/api/v1/health/live` |
| Worker | `kb-worker` | 无 | 否 | 进程存活检查 |
| PostgreSQL | `kb-postgres` | 5432 | 否（仅内部） | `pg_isready` |
| Redis | `kb-redis` | 6379 | 否（仅内部） | `redis-cli ping` |

网络架构：
- 宿主机 -> Web (80) -> API Server (8000) -> PostgreSQL (5432) / Redis (6379)
- Worker 通过 Redis 队列接收任务，不对外暴露端口

---

## 五、健康检查端点说明

| 端点 | 用途 | 成功响应 | 失败响应 |
|---|---|---|---|
| `GET /api/v1/health/live` | 存活检查 | 200 | - |
| `GET /api/v1/health/ready` | 就绪检查 | 200（全部通过） | 503（部分失败） |

Docker HEALTHCHECK 配置：
- Web：每 30 秒检查 `http://localhost:80/`
- API Server：每 30 秒检查 `http://localhost:8000/api/v1/health/live`
- Worker：每 30 秒检查 arq 进程是否存在
- PostgreSQL：每 10 秒执行 `pg_isready`
- Redis：每 10 秒执行 `redis-cli ping`

---

## 六、常用命令

```bash
# 启动全部服务
docker compose -f deploy/docker-compose.yml up -d

# 停止全部服务
docker compose -f deploy/docker-compose.yml down

# 重启全部服务
docker compose -f deploy/docker-compose.yml restart

# 查看日志（最近 100 行，持续输出）
docker compose -f deploy/docker-compose.yml logs --tail=100 -f

# 查看特定服务日志
docker compose -f deploy/docker-compose.yml logs api-server

# 进入容器
docker compose -f deploy/docker-compose.yml exec api-server bash

# 运行测试
docker compose -f deploy/docker-compose.test.yml up --build --abort-on-container-exit

# 使用 Makefile 快捷命令
make dev          # 仅启动 postgres 和 redis
make dev-full     # 启动全部服务
make build        # 构建镜像
make test         # 运行测试
make logs         # 查看日志
make status       # 查看状态
make health       # 健康检查
make clean        # 清理全部
```

---

## 七、常见故障排查

### 问题 1：端口 80 已被占用

**错误信息**：`bind: address already in use`

**解决方案**：
```bash
# 查找占用端口 80 的进程
sudo lsof -i :80

# 停止占用进程，或修改 docker-compose.yml 中的端口映射
# 例如将 "80:80" 改为 "8080:80"
```

### 问题 2：数据库连接失败

**错误信息**：`could not connect to server: Connection refused`

**解决方案**：
```bash
# 检查 postgres 容器是否正常运行
docker compose -f deploy/docker-compose.yml ps postgres

# 检查 postgres 日志
docker compose -f deploy/docker-compose.yml logs postgres

# 检查数据库密码是否正确
# 确保 .env 文件中的 POSTGRES_PASSWORD 已设置
```

### 问题 3：权限问题（非 root 用户运行）

**错误信息**：`Permission denied`

**解决方案**：
```bash
# 检查挂载卷的权限
docker compose -f deploy/docker-compose.yml exec api-server ls -la /app/storage

# 如果需要，修复卷权限
docker compose -f deploy/docker-compose.yml down
docker volume rm kb-storage-data
docker compose -f deploy/docker-compose.yml up -d
```

### 问题 4：镜像构建失败

**错误信息**：`failed to solve: ...`

**解决方案**：
```bash
# 清理 Docker 构建缓存后重试
docker builder prune -f
docker compose -f deploy/docker-compose.yml build --no-cache
```

### 问题 5：磁盘空间不足

**错误信息**：`no space left on device`

**解决方案**：
```bash
# 清理未使用的 Docker 资源
docker system prune -a -f

# 清理构建缓存
docker builder prune -a -f
```

---

## 八、生产环境部署注意事项

1. **必须修改所有默认密码**：`POSTGRES_PASSWORD`、`SECRET_KEY` 必须使用强随机值。
2. **必须启用 TLS**：使用外部 LB 或 Certbot 配置 HTTPS，Nginx 生产配置包含 TLS 模板。
3. **必须关闭 DEBUG**：`DEBUG=false`（默认值，不要修改）。
4. **必须配置防火墙**：仅开放 80/443 端口，5432 和 6379 禁止外部访问。
5. **必须配置备份**：参考 `docs/operations/backup-restore.md`。
6. **必须配置监控**：参考 `docs/operations/monitoring.md`。
7. **镜像不可变标签**：生产使用 `v1.0.0-abc1234` 格式的标签，不使用 `latest`。
8. **测试与生产镜像一致**：生产使用与测试环境完全相同的镜像（SHA256 一致）。