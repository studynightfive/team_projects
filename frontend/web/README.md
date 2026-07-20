# 统一 Web 前端

`frontend/web` 是普通用户工作区与 `/admin` 管理中心共用的 Vue 3 应用，使用 strict TypeScript、Vue Router、Pinia、Ant Design Vue 和 Lucide 图标。

## 运行模式

- `pnpm.cmd run dev:web`：确定性 Mock 模式。未注册请求直接失败，不访问真实业务网络，适合视觉和交互回归。
- `pnpm.cmd run dev:web:api`：真实 API 模式。`/api` 默认代理到 `http://127.0.0.1:8000`，启用登录、会话刷新、权限守卫和业务数据读取。
- 生产构建默认使用真实 API，并通过同源 Nginx 访问后端。

Mock 数据只用于预览；真实模式中尚无后端契约的能力会隐藏、禁用或明确提示，不会伪造成功结果。访问 `/admin` 需要真实会话具备对应权限码。

## 命令

在仓库根目录执行：

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

`verify:web:browser` 需要先运行 `dev:web`，用于固定数据下的桌面端和移动端页面回归。真实 API 的授权、失败状态和并发刷新由组件/服务测试及 Docker 联调验证。

## 主要目录

```text
src/api/          Axios Client、Cookie 会话和单飞刷新
src/components/   共享布局与业务组件
src/config/       运行模式判断
src/data/         设计基线固定数据
src/mocks/        拒绝未知请求的 Mock Adapter
src/router/       用户、管理和错误页路由守卫
src/services/     按业务域封装的真实 API 调用
src/stores/       跨页面会话和通知状态
src/tests/        组件、路由、权限和 API 边界测试
src/views/        用户工作区与管理中心页面
```

视觉事实来源仍位于 `docs/design/`；OpenAPI 事实来源位于 `docs/api/openapi.yaml`。
