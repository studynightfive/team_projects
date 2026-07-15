# 智能知识库平台

面向团队知识资产的统一检索、问答、引用溯源、文档处理和导出平台。首期采用前后端分离的 Git Monorepo，由五人团队协作交付，并将普通用户功能和管理员管理中心合并为一个 Vue 应用。

## 当前状态

项目已进入统一前端 M01 `web-foundation` 实施阶段。当前 M01 只提供静态用户/管理壳层、通用状态、API Client 安全边界和 design-only Mock，不包含真实登录、权限或业务接口。

## 总体架构

```text
          统一 Web 应用
  普通用户工作区 + /admin 管理中心
                 |
               Nginx
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
└─ web/             普通用户与管理中心的统一 Vue 3 应用
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

所有直接依赖精确锁定，禁止 `^`、`~` 和 `latest`。完整依赖基线见《知识库平台_5人团队分工协作方案.md》。

## 开发工作流

1. 阅读 [AGENTS.md](AGENTS.md) 和 [MEMORY.md](MEMORY.md)。
2. 从 GitHub Issue 确认目标、范围、依赖、验收和失败场景。
3. 从最新 `main` 创建 `feature/<issue>-<name>` 或 `fix/<issue>-<name>`。
4. 实现并运行相关类型检查、Lint、测试和构建。
5. 推送分支并创建关联 Issue 的 Pull Request。
6. 至少一名非作者评审和 Pull Request `quality` CI 通过后合并。

员工 1 的统一前端 P0 使用经批准的整体交付流程：一个总 Issue、一个长期功能分支、15 个里程碑和一个持续更新的 Draft PR；每个里程碑先本地通过再推送，全部门禁通过后才转 Ready。详见 [员工 1 统一前端完整实施计划](员工1_统一前端完整实施计划.md)。

治理细节见 [docs/project-governance.md](docs/project-governance.md)。

## 统一前端命令

前端工程进入仓库后，在根目录使用：

```powershell
npm.cmd ci
npm.cmd run dev:web
npm.cmd run dev:web:api
npm.cmd run typecheck:web
npm.cmd run lint:web
npm.cmd run test:web
npm.cmd run test:web:watch
npm.cmd run build:web
npm.cmd run verify:web:browser
```

- `dev:web` 使用 design-only 固定数据，Mock Adapter 默认拒绝所有未注册请求，不访问真实业务网络。
- `dev:web:api` 通过 Vite 代理访问 `http://127.0.0.1:8000/api`。
- 普通用户入口为 `http://127.0.0.1:5173`，管理中心为 `http://127.0.0.1:5173/admin`。

## 安全

- 不提交 `.env`、凭据、Token、API Key、密码或私钥。
- OpenAPI 是接口单一事实来源，权限由后端最终校验。
- Markdown 使用服务端清洗和前端 DOMPurify 二次过滤。
- 原始文件和导出文件只通过鉴权接口或短期地址访问。

发现安全问题时不要创建公开 Issue，请直接联系仓库所有者处理。
