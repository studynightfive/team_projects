# 智能知识库平台项目规则

## 1. 项目目标与边界

本仓库交付前后端分离的智能知识库平台。首期使用 Git Monorepo、单个 Vue 3 前端、FastAPI 模块化单体、PostgreSQL + pgvector、Redis 异步任务，不拆分微服务。

主要目录：

```text
frontend/web/           普通用户工作区与管理员管理中心
backend/                FastAPI、Worker、迁移和测试
deploy/                 Docker、Nginx 和环境模板
docs/                   API、设计和运维文档
```

模块负责人只修改自己的主责范围。跨模块契约先更新 OpenAPI 或对应事实来源，再更新生成类型、Mock 和测试。

## 2. 沟通与代码风格

- README、技术文档、UI 文案、代码注释、计划、Review 和总结使用中文；代码、变量名和文件名使用英文。
- 结论先行，说明技术选择为什么重要及其用户影响。
- 精准修改，不重构无关代码，不添加需求外功能、抽象、配置或依赖。
- 优先函数式和声明式实现；除非现有模式或领域明确受益，否则避免 class。
- TypeScript 开启 strict，禁止 `any`。`unknown` 只用于外部输入边界，并必须安全收窄。
- 注释解释“为什么”，不重复代码已经表达的“做了什么”。

## 3. 项目启动协议

- 项目工作开始前先读取根目录 `AGENTS.md` 和 `MEMORY.md`。
- 复杂任务按 Specify -> Plan -> Task -> Execute -> Verify 执行；编码前创建或更新 PRD、Tech-Spec、API Contract 或等价文档。
- 开始前定义验收标准、风险、约束和验证步骤；结束前运行与改动相称的检查。
- 学到长期有效的架构决策、兼容性决定、反复踩坑或用户纠正时更新 `MEMORY.md`；不记录临时进度、secret 或代码中显而易见的事实。

## 4. Git 与协作

- `main` 始终保持可部署，禁止直接推送。
- 一个 Issue 对应一个分支和一个 Pull Request。
- 员工 1 的统一前端 P0 作为一个整体交付单元：只创建一个总 Issue、一个 `feature/<issue>-unified-web-p0` 长期功能分支、15 个里程碑和一个持续更新的 Draft PR。每个里程碑必须先通过本地门禁再推送同一分支；全量本地 E2E、最终 CI 和测试环境验收通过后才能转 Ready；合并后才关闭总 Issue。
- 功能分支：`feature/<issue>-<name>`；修复分支：`fix/<issue>-<name>`；发布分支：`release/<version>`。
- 每个新分支从最新 `main` 创建；依赖上一个分支时，等待上一个 PR 合并后再创建。
- 不提前创建全部分支，不在不同分支重复维护同一份代码。
- 分支合并后删除远端和本地功能分支。
- 提交格式：`feat(scope): message`、`fix(scope): message`、`test(scope): message`、`docs(scope): message`。
- 工作区存在无关改动时只暂存本任务文件，不回滚他人改动。
- PR 必须关联 Issue，包含范围、用户影响、验证结果、截图或视觉证据（适用时）及剩余风险。
- 至少一名非作者评审通过且必需 CI 通过后才能合并。

标准起点：

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/<issue>-<name>
```

## 5. 固定版本

- Node.js `22.23.1`，npm `10.9.8`。
- Python `3.10.20`，uv `0.8.22`。
- Vue `3.5.39`、Vue Router `4.6.3`、Pinia `3.0.4`、Element Plus `2.14.3`。
- Axios `1.13.2`、Markdown-It `14.1.0`、DOMPurify `3.3.0`、FileSaver `2.0.5`。
- Vite `7.2.2`、TypeScript `5.9.3`、Vue TSC `3.3.7`、ESLint `9.39.1`、Prettier `3.6.2`、Vitest `4.1.10`。
- FastAPI、数据库、文档处理工具及完整依赖版本以协作方案和锁文件为准。
- 所有直接依赖使用精确版本，禁止 `^`、`~` 和 `latest`；提交 `package-lock.json` 与 `uv.lock`。

## 6. 前端规则

- 前端统一位于 `frontend/web/`；普通用户工作区和管理员 `/admin` 管理中心共用登录、路由、组件、类型、构建和部署产物。
- 管理入口和管理路由按后端权限码展示；普通用户不得预加载管理数据，前端隐藏不能代替后端权限校验。
- Pinia 只保存跨页面、共享或必须持久化的状态；表单、弹窗、页码和单页筛选留在局部。
- OpenAPI 是 API 单一事实来源；TypeScript 类型由 OpenAPI 生成，Mock 实现同一类型。未确认接口只做静态 UI，不标记为联调完成。
- 普通请求复用统一 API Client。流式问答使用原生 Fetch、ReadableStream、TextDecoder 和 AbortController，不新增 SSE 依赖。
- Markdown 必须经服务端清洗和前端 DOMPurify 二次过滤，禁止脚本、事件属性和危险 URL。
- 前端不把 Token 写入 localStorage、URL 或日志；优先 HttpOnly Cookie。隐藏按钮不能代替后端权限校验。
- 下载统一走鉴权接口，不拼接可猜测的静态文件地址。

规定的统一前端命令：

```powershell
npm.cmd run dev:web
npm.cmd run dev:web:api
npm.cmd run typecheck:web
npm.cmd run lint:web
npm.cmd run test:web
npm.cmd run test:web:watch
npm.cmd run build:web
```

## 7. 后端与安全规则

- 后端按业务包隔离，通过服务层调用；禁止跨模块直接修改数据。
- 在认证、上传、用户输入、网络请求、支付、AI 工具和外部集成边界验证并清理输入。
- 永远不读取、打印、复制或提交 `.env`、凭据、Token、API Key、密码或私钥的值；只记录配置位置。
- 不使用 `eval()` 等不安全执行方式；日志和错误不得泄露 secret、内部堆栈或存储路径。
- 文件上传交叉校验文件名、扩展名、MIME 和文件头，并阻止路径穿越和上传目录执行。

## 8. 验证与完成定义

- 相关类型检查、Lint、单元/组件/接口测试和生产构建通过。
- 修复 Bug 时可行情况下先复现或添加失败测试，再验证回归。
- UI 分支同时检查 1440px、1280px 和 375px，覆盖加载、空、401、403、404、网络失败、长文本、重复点击和页面离开清理。
- 不把第一稿交给用户 spot-check；检查失败后修复并重新运行。
- 功能只有在代码、测试、契约、文档、PR 评审、CI 和测试环境验收均满足后才完成。
- 最终汇报必须说明做了什么、验证了什么、剩余限制，以及 `MEMORY.md` 是否更新。
