# 统一 Web 前端

`frontend/web` 是普通用户工作区与 `/admin` 管理中心共用的 Vue 3 应用。M01 `web-foundation` 只建立后续功能所需的稳定壳层，不把静态设计数据伪装成真实接口。

## 当前范围

- Vue 3、Vite、strict TypeScript、Vue Router、Pinia 与 Element Plus 配置基线。
- 普通用户工作区与管理中心两套响应式布局。
- `/login`、`/`、`/admin`、`/403` 和全局 404 路由。
- 加载、空、通用错误、403 和 404 状态组件。
- `/api` Axios Client、Cookie 请求配置与安全错误收窄。
- design-only Mock Adapter；未注册请求默认失败，不回退真实网络。

M01 不包含真实登录、会话、权限码、路由守卫、业务 API 或后端联调。`/admin` 可进入仅用于验证布局，不代表普通用户拥有管理权限。

## 设计事实来源

- 视觉变量直接导入 `docs/design/m01-web-foundation/tokens.css`，前端不维护第二份 tokens。
- 页面固定展示数据来自 `docs/design/m01-web-foundation/mock-data.json`，仅用于布局和边界验收。
- production 页面应与同目录的 artifact 和 1440px、1280px、375px 验收图保持一致。

## 开发命令

在仓库根目录执行：

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

- `dev:web` 使用 Vite `mock` mode；API Client 默认拒绝未注册请求。
- `dev:web:api` 使用 Vite `api` mode，并把 `/api` 代理到 `http://127.0.0.1:8000`。
- 开发地址为 `http://127.0.0.1:5173`；管理中心为 `http://127.0.0.1:5173/admin`。
- `verify:web:browser` 需在 `dev:web` 运行时执行；它通过 Chrome DevTools Protocol 固定 1440px、1280px、375px 视口，生成截图并检查溢出、控制台、业务网络请求和移动抽屉焦点。

## 目录

```text
src/
├─ api/          统一 API Client 与公开错误边界
├─ components/   已确认复用的工作区壳、移动抽屉和状态卡
├─ data/         design-only 数据与导航配置
├─ layouts/      用户和管理布局
├─ mocks/        默认拒绝网络的 Mock Adapter
├─ router/       M01 路由壳
├─ styles/       全局布局样式和 tokens 导入
├─ tests/        路由、布局、移动交互和 API 边界测试
└─ views/        M01 页面骨架
```

Pinia 在 M01 只完成注册，不创建用户、权限或业务 store。表单和页面临时状态继续留在组件局部，直到真实跨页面需求出现。
