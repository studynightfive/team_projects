# 部署指南

## 适用边界

`deploy/docker-compose.yml` 用于本地开发和单机联调，包含五个长期服务以及一次性迁移任务。生产环境可复用镜像，但必须另行提供 TLS、Secret 管理、监控栈、异地备份和高可用能力。

## 前置条件

- Docker Engine 27.5.1 或更高版本
- Docker Compose 2.32.4 或更高版本
- 至少 20 GB 可用磁盘空间

## 配置

```bash
cp deploy/env/.env.example deploy/env/.env
```

只在本地编辑 `deploy/env/.env`，不得提交或打印其内容。至少配置 `POSTGRES_PASSWORD` 和不少于 32 位的 `SECRET_KEY`。演示播种默认关闭；如仅在隔离环境启用，还必须提供不少于 12 位的 `DEMO_SEED_PASSWORD`。生产环境还必须满足：

```text
APP_ENVIRONMENT=production
AUTO_SEED_DEMO_DATA=false
COOKIE_SECURE=true
DEBUG=false
```

生产流量必须通过 HTTPS，否则 Secure Cookie 无法正常发送。

## 启动与验证

```bash
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml config --quiet
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml up -d --build
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml ps
bash scripts/health-check.sh
```

启动顺序为 PostgreSQL/Redis 健康 → `migrate` 执行 `alembic upgrade heads` → API/Worker → Web。`migrate` 正常退出码为 0，不是长期运行服务。

### 创建首管理员

应用启动会自动补齐内建权限和角色，不会自动创建生产账号。新环境启动完成后，使用交互式终端执行：

```bash
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml exec api-server /app/backend/.venv/bin/python scripts/bootstrap_admin.py
```

口令输入不回显，长度必须为 12–128 位。数据库已有“超级管理员”角色账号时，脚本会拒绝创建第二个首管理员。不要在非交互式 CI 中传递口令，也不要使用演示播种脚本代替该流程。

| 入口 | 预期 |
|---|---|
| `http://127.0.0.1/` | Web SPA 200 |
| `/api/v1/health/live` | 进程存活 200 |
| `/api/v1/health/ready` | 数据库、Redis、存储均可用时 200，否则 503 |
| `/api/v1/docs` | API 文档 200 |
| `/api/v1/metrics` | 经公网 Nginx 返回 404 |

## 常用操作

```bash
COMPOSE="docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml"
$COMPOSE ps
$COMPOSE logs --tail=100 api-server worker
$COMPOSE up -d --build
$COMPOSE down                 # 保留数据卷
```

Shell 变量示例适用于 Bash；PowerShell 请直接写完整 Compose 命令。

## 故障排查

1. `migrate` 失败：查看 `docker compose ... logs migrate`，不要绕过迁移强行启动 API。
2. `/ready` 返回 503：根据响应中的 `database`、`redis`、`storage` 检查对应依赖和卷权限。
3. 端口 80 被占用：先确认宿主机占用者，再决定停止该进程或显式调整 Web 端口映射。
4. 构建失败：先重试普通构建；仅在确认缓存损坏时清理特定 BuildKit 缓存，不执行全局 `docker system prune -a`。
5. 存储权限异常：检查命名卷和容器内 `/app/storage` 所有者；不要通过删除 `kb-storage-data` 作为常规修复。
6. 首管理员脚本拒绝执行：先确认是否已有管理员；不要通过删除账号或角色规避保护。

删除数据是破坏性操作，只能在确认目标为本地测试环境且已备份后执行：

```bash
make purge-data CONFIRM=delete-data
```
