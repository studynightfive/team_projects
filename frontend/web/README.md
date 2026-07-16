# 统一 Web 前端

`frontend/web` 是普通用户工作区与 `/admin` 管理中心共用的 Vue 3 应用。M01 `web-foundation` V2 已由项目负责人批准并冻结为正式视觉和交互基线；M02–M14 与 AI 搜索工作台升级已在同一壳层中形成业务路由的本地可交互页面，但尚未接入真实认证、权限或业务接口。静态设计数据不会伪装成真实接口结果。

当前全部页面的用途、主要操作和联调边界见 [`docs/frontend-feature-guide.md`](../../docs/frontend-feature-guide.md)。

## 当前范围

- Vue 3、Vite、strict TypeScript、Vue Router、Pinia、Ant Design Vue `4.2.6` 与 `@lucide/vue` `1.24.0` 配置基线。
- 普通用户工作区与管理中心两套响应式布局。
- 15 个用户工作区路由、9 个管理中心路由，以及 `/login`、`/403` 和全局 404 特殊入口。
- 加载、空、通用错误、403 和 404 状态组件。
- `/api` Axios Client、Cookie 请求配置与安全错误收窄。
- design-only Mock Adapter；未注册请求默认失败，不回退真实网络。
- M02–M14 与 AI 搜索工作台的筛选、弹窗、抽屉、确认、状态切换和组合导航只更新组件局部状态，刷新后恢复固定样例。

当前版本不包含真实登录、会话、权限码、路由守卫、业务 API 或后端联调。M02–M14 与 AI 搜索工作台只能标记为“本地页面已开发”，不能标记为业务里程碑联调完成。`/admin` 可进入仅用于验证布局，不代表普通用户拥有管理权限。真实数据、上传、下载、轮询和流式问答必须等待 OpenAPI 契约后接入。

## 设计事实来源

- V2 视觉变量直接导入 `docs/design/m01-web-foundation/tokens-v2.css`，前端不维护第二份 tokens。
- 页面固定展示数据分别来自 M01 设计数据、`src/data/local-pages.ts` 和 `src/mocks/ai-search.ts`，仅用于布局、交互和边界验收。
- production 页面应与 `docs/design/m01-web-foundation/` 下已冻结的 V2 规格及 `docs/verification/m01-web-foundation/` 正式基线截图保持一致；`artifact.html` 与 `tokens.css` 仅保留为 V1 历史证据。

## 开发命令

在仓库根目录使用 pnpm `11.13.0` 执行：

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run dev:web
pnpm.cmd run dev:web:api
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run test:web:watch
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```

- `dev:web` 使用 Vite `mock` mode；API Client 默认拒绝未注册请求。
- `dev:web:api` 使用 Vite `api` mode，并把 `/api` 代理到 `http://127.0.0.1:8000`。
- 开发地址为 `http://127.0.0.1:5173`；管理中心为 `http://127.0.0.1:5173/admin`。
- `verify:web:browser` 需在 `dev:web` 运行时执行；它通过 Chrome DevTools Protocol 覆盖 M01 的 20 个基线场景，以及 M02–M14 的 50 个 1440px、1280px、375px 和侧栏折叠场景，并检查溢出、可见顶栏标题、控制台、业务网络请求和移动抽屉焦点。

## 目录

```text
src/
├─ api/          统一 API Client 与公开错误边界
├─ components/   已确认复用的工作区壳、移动抽屉和状态卡
├─ data/         design-only 数据、完整导航与安全固定样例
├─ layouts/      用户和管理布局
├─ mocks/        默认拒绝网络的 Mock Adapter
├─ router/       M01–M14 正式前端路由
├─ styles/       全局布局样式和 tokens 导入
├─ tests/        路由、布局、移动交互和 API 边界测试
└─ views/        用户工作区与管理中心页面
```

Pinia 当前只完成注册，不创建用户、权限或业务 store。表单和页面临时状态继续留在组件局部，直到真实跨页面需求和 API 契约出现。
