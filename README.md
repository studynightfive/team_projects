# 智能知识库平台

面向团队知识资产的统一检索、问答、引用溯源、文档处理和导出平台。首期采用前后端分离的 Git Monorepo，通过清晰模块边界支持六人并行开发，同时保持部署和维护简单。

## 当前状态

项目处于治理与工程基线阶段。业务代码尚未进入 `main`；功能分支必须在对应 Issue、接口契约和验收标准明确后创建。

## 总体架构

```text
用户端 Web                 管理端 Web
    |                          |
    +----------- Nginx --------+
                 |
          FastAPI API Server
                 |
   +-------------+-------------+
   |             |             |
认证权限模块   知识文档模块   RAG 与导出模块
                 |
          PostgreSQL + pgvector
                 |
          Redis + Worker
```

## 计划目录

```text
frontend/
├─ user-web/        用户端 Vue 3 应用
├─ admin-web/       管理端 Vue 3 应用
└─ shared-ui/       经双方确认的共享组件
backend/
├─ app/             FastAPI 业务模块
├─ migrations/      Alembic 迁移
└─ tests/           后端测试
deploy/             Docker、Nginx 和环境模板
docs/
├─ api/             OpenAPI 与接口协作
├─ design/          产品和视觉事实来源
└─ operations/      部署、监控、备份和回滚
scripts/            可重复执行的工程脚本
```

## 固定环境

| 工具 | 版本 |
|---|---:|
| Node.js | 22.23.1 |
| npm | 10.9.8 |
| Python | 3.10.20 |
| uv | 0.8.22 |
| Docker Engine | 27.5.1 |
| Docker Compose | 2.32.4 |
| PostgreSQL | 17.10 |
| Redis | 7.4.9 |

所有直接依赖精确锁定，禁止 `^`、`~` 和 `latest`。完整依赖基线见《知识库平台_6人团队分工协作方案.md》。

## 开发工作流

1. 阅读 [AGENTS.md](AGENTS.md) 和 [MEMORY.md](MEMORY.md)。
2. 从 GitHub Issue 确认目标、范围、依赖、验收和失败场景。
3. 从最新 `main` 创建 `feature/<issue>-<name>` 或 `fix/<issue>-<name>`。
4. 实现并运行相关类型检查、Lint、测试和构建。
5. 推送分支并创建关联 Issue 的 Pull Request。
6. 至少一名非作者评审和必需 CI 通过后合并。

治理细节见 [docs/project-governance.md](docs/project-governance.md)。

## 用户端命令

用户端工程进入仓库后，在根目录使用：

```powershell
npm.cmd ci
npm.cmd run dev:user
npm.cmd run dev:user:api
npm.cmd run typecheck:user
npm.cmd run lint:user
npm.cmd run test:user
npm.cmd run build:user
```

- `dev:user` 使用类型安全 Mock。
- `dev:user:api` 通过 Vite 代理访问 `http://127.0.0.1:8000/api`。
- 默认用户端地址为 `http://localhost:5173`。

## 安全

- 不提交 `.env`、凭据、Token、API Key、密码或私钥。
- OpenAPI 是接口单一事实来源，权限由后端最终校验。
- Markdown 使用服务端清洗和前端 DOMPurify 二次过滤。
- 原始文件和导出文件只通过鉴权接口或短期地址访问。

发现安全问题时不要创建公开 Issue，请直接联系仓库所有者处理。
