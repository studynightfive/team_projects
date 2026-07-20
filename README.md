# 智能知识库平台

面向团队知识资产的统一检索、问答、引用溯源、文档处理和导出平台。仓库采用 Git Monorepo：Vue 3 统一承载普通用户工作区和 `/admin` 管理中心，FastAPI 模块化单体提供业务 API，PostgreSQL + pgvector 保存业务与向量数据，Redis + ARQ Worker 执行异步任务。

## 当前实现边界

- 前端同时支持 `mock` 和真实 API 两种模式；真实模式包含登录、权限路由、知识库、文档、检索、会话、收藏、通知、导出和管理页面。
- Mock 模式只用于确定性 UI 回归，不会回退到真实业务网络；仍未接入的交互会在界面中明确标为本地预览。
- 后端 OpenAPI 运行时契约同步保存于 `docs/api/openapi.yaml`，由 `scripts/export_openapi.py` 生成并由契约测试校验。
- Docker Compose 提供 Web、API Server、Worker、PostgreSQL、Redis 五个长期服务，并在应用启动前运行一次性 Alembic 迁移。

## 目录

```text
frontend/web/       Vue 3 普通用户工作区与管理中心
backend/app/        FastAPI 业务模块与 ARQ Worker
backend/migrations/ Alembic 迁移
backend/tests/      后端自动化测试
deploy/             Docker、Nginx、环境模板和可选监控配置
docs/               API、设计、集成、验证和运维文档
samples/            文档解析测试样本及完整性清单
scripts/            契约导出、健康检查、备份、恢复和发布脚本
```

## 固定环境

| 工具 | 版本 |
|---|---:|
| Node.js | 22.23.1 |
| pnpm | 11.13.0 |
| Python | 3.10.20 |
| uv | 0.11.26 |
| PostgreSQL | 17（pgvector 镜像固定摘要） |
| Redis | 7.4.9 |

所有直接依赖使用精确版本；前后端锁文件必须随依赖变更一起提交。

## 本地启动

先复制环境模板并填写本地值。不要读取、打印或提交真实 `.env` 内容。

```powershell
Copy-Item deploy/env/.env.example deploy/env/.env
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml up -d --build
bash scripts/health-check.sh
```

入口：

- Web：`http://127.0.0.1/`
- API 文档：`http://127.0.0.1/api/v1/docs`
- 存活检查：`http://127.0.0.1/api/v1/health/live`
- 就绪检查：`http://127.0.0.1/api/v1/health/ready`

`/api/v1/metrics` 只允许容器内部监控网络访问，Nginx 外网入口固定返回 404。

应用启动会幂等补齐内建权限码与“超级管理员”“普通用户”“知识库编辑者”角色，但默认不创建任何账号。新环境首次启动后，在交互式终端创建首管理员：

```powershell
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml exec api-server /app/backend/.venv/bin/python scripts/bootstrap_admin.py
```

脚本使用不回显的口令输入，口令至少 12 位，并且只在数据库中尚无管理员时创建。演示账号播种只允许在隔离环境显式启用，不是生产初始化方式。

## 质量门禁

前端：

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
```

后端与样本验证使用隔离的测试数据库和测试卷，测试依赖在镜像构建期安装：

```powershell
docker compose -f deploy/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner
```

更详细的部署、监控、备份和回滚说明见 [运维文档](docs/operations/README.md)。协作和分支规则见 [AGENTS.md](AGENTS.md) 与 [项目治理](docs/project-governance.md)。

## 安全边界

- 不提交 `.env`、凭据、Token、API Key、密码或私钥。
- 权限由后端校验，前端隐藏按钮不是授权机制。
- Markdown 在服务端清洗并由前端 DOMPurify 二次过滤。
- 原始文件和导出文件只通过鉴权接口下载；存储卷不映射为公开静态目录。
