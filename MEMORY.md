# 项目长期记忆

## 架构与范围

- 智能知识库平台采用 Git Monorepo、一个统一 Vue 3 前端、一个 FastAPI 模块化单体、独立 Worker、PostgreSQL + pgvector 和 Redis。
- 首期部署单元为 `web`、`api-server`、`worker`、`postgres`、`redis`；不拆分认证、文档或 RAG 微服务。
- 原始文件和标准化 Markdown 都必须保留；文档处理、OCR、索引和大型导出使用异步任务。

## 协作边界

- 2026-07-15 员工 2 离职，其管理端前端职责由员工 1 接管；当前团队保留员工编号 1、3、4、5、6。
- 员工 1 主责统一的 `frontend/web`，其中普通用户工作区与 `/admin` 管理中心共用登录、组件、API 类型、构建和部署产物。
- 管理员可同时使用普通用户功能和管理中心；管理入口、路由和按钮由权限码控制，后端对所有管理请求最终鉴权。
- 员工 3 提供认证、个人信息、权限码和统一错误结构；员工 4 提供知识库文档、Markdown、资源和引用定位；员工 5 提供检索、问答、会话、反馈、导出和收藏接口；员工 6 维护治理、CI 和部署基线。
- OpenAPI 是前后端接口单一事实来源；生成的 TypeScript 类型和 Mock 使用同一契约，未确认字段不能被标记为联调完成。

## 长期安全与实现决定

- 前端认证优先使用 HttpOnly Cookie，不在 localStorage、URL 或日志中保存 Token。
- 流式问答使用原生 Fetch + ReadableStream + TextDecoder + AbortController，不新增专用 SSE 依赖。
- Markdown 采用服务端清洗加前端 DOMPurify 二次过滤；下载统一走鉴权接口。
- 每个新功能分支从最新 `main` 创建；依赖分支必须等待父 PR 合并，避免堆叠未合并代码造成冲突。
- 2026-07-15 确认员工 1 的统一前端 P0 采用整体交付：一个总 Issue、一个 `feature/<issue>-unified-web-p0` 长期功能分支、15 个里程碑和一个持续更新的 Draft PR。每个里程碑先本地通过再推送；全量本地 E2E、最终 CI 和测试环境验收通过后才转 Ready；合并后统一关闭总 Issue 并删除长期分支。

## 非机密仓库备注

- GitHub 仓库：`studynightfive/team_projects`，默认分支 `main`。
- 2026-07-15 接管项目治理时，远端 `main` 基线为 `c57255a162ffbd8ba59e353f9f46588c2e80e192`，仓库尚无工程代码、治理文件、Issue 模板或 CI。
- 当前协作账号对仓库是 Write 权限而不是 Admin；`main` 已启用部分经典分支保护，但必需状态检查列表尚未包含 `quality`，其余目标规则也无法由当前权限完整确认。仓库管理员需运行 `scripts/configure-main-protection.ps1` 应用并复核完整保护规则。
- 项目直接依赖必须精确锁定；Node.js `22.23.1`、npm `10.9.8`、Python `3.10.20`、uv `0.8.22`。
