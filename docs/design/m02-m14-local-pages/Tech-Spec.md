# M02–M14 本地页面 Tech-Spec

## 1. 技术基线

- 沿用 M01：Vue `3.5.39`、Vue Router `4.6.3`、Pinia `3.0.4`、Ant Design Vue `4.2.6`、`@lucide/vue` `1.24.0`。
- 包管理器为 pnpm `11.13.0`，不增加依赖。
- 继续直接导入 `docs/design/m01-web-foundation/tokens-v2.css`，不复制第二套 tokens。
- 页面只使用确定性本地视图数据，不调用 API Client。

## 2. 目录与职责

```text
frontend/web/src/
├── components/
│   ├── PageHeader.vue
│   ├── ResourcePanel.vue
│   └── InlineState.vue
├── data/
│   ├── foundation.ts
│   └── local-pages.ts
├── layouts/
│   ├── UserWorkspaceLayout.vue
│   └── AdminWorkspaceLayout.vue
├── router/index.ts
└── views/
    ├── user/
    └── admin/
```

- `PageHeader` 统一一个 `h1`、说明、可选 eyebrow 和 actions slot。
- `ResourcePanel` 只封装卡片标题与 body/footer slots，不接收万能 schema。
- `InlineState` 处理工作区卡片内的 loading/empty/error，不输出第二个 `h1`。
- 业务视图保留语义模板，不建立配置驱动的万能页面生成器。

## 3. 路由与导航

- 所有页面继续作为 `UserWorkspaceLayout` 或 `AdminWorkspaceLayout` 的子路由。
- 路由 `meta.title` 驱动顶栏当前页标题；`meta.parentTitle` 驱动面包屑上级名称。
- `NavigationItem` 增加 `activePrefixes`，由共享 `isNavigationItemActive()` 判断动态详情和多路由分组激活态。
- 固定样例：`kb_id=product-handbook`、`document_id=release-guide`、`conversation_id=conv-release-review`。
- 不添加 `/profile`，不添加正式路由表之外的详情页。

## 4. 本地数据与交互

- `mock-data.json` 是页面内容事实来源；`local-pages.ts` 只做组件图标映射和安全的本地视图导出。
- 固定数据不复制 API 响应包络，不使用后端候选字段名，不声称代表 DTO。
- 筛选、搜索、标签、页码、选中行、抽屉和确认框使用组件局部 `ref`/`computed`。
- 只在跨多个页面且必须共享时才使用 Pinia；本轮不新增全局业务 Store。
- 写操作只显示“本地预览已更新”或说明性反馈，不显示“已保存到服务器”。
- 上传区不读取真实文件；下载按钮不构造 URL；模型密钥输入默认空且不写入 Store/Storage/日志。
- 问答页用本地逐段展示模拟视觉状态，不实现 Fetch/SSE，也不启动后台定时器。

## 5. 样式与响应式

- 页面主体最大宽度、240/64px 侧栏、56px 顶栏、375px gutter 和移动底栏完全沿用 M01。
- 新增统一类只服务本轮页面：`page-header`、`resource-panel`、`filter-bar`、`data-table`、`status-chip`、`split-view`、`local-preview-badge`。
- 桌面筛选栏可横向排列；1180px 以下双列内容改单列；767px 以下表单、卡片、操作栏改单列。
- 表格最小宽度只作用于内部滚动容器；`html`、`body` 和 `.workspace-shell` 不得溢出。
- 不使用 emoji、远程字体、渐变、霓虹或大面积管理紫色背景。

## 6. 安全边界

- 默认 Mock Adapter 继续拒绝未注册请求；浏览器验收业务 `/api` 请求必须为 0。
- 无 OpenAPI 时不创建 auth store、Cookie 策略、权限码映射、API 类型或接口路径。
- 只使用保留示例数据：邮箱使用 `example.com`，IP 使用 RFC 5737 网段，request ID 使用明显的 `demo-*`。
- 审计、模型和用户页面不展示 Token、密码、密钥、内部堆栈或真实个人数据。
- Markdown 页面本轮只渲染受控 Vue 模板；真实 Markdown 渲染和 DOMPurify 联调等待文档契约。

## 7. 测试与验证

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```

- 路由测试：每个正式路由解析到正确页面，未知路径仍为 404。
- 导航测试：动态详情与组合菜单激活正确，全部正式入口有 `to`。
- 交互测试：至少覆盖用户筛选/会话操作、管理筛选/详情，以及模型密钥不持久化。
- 浏览器测试：页面级 expectations，不能把 M01 的“四指标”断言套到列表/详情页。
- 视觉检查：1440、1280、375，另检查一个用户详情页和一个管理表格页的桌面折叠态。

## 8. 完成定义

本地页面完成需同时满足：代码、文档、固定数据、测试、生产构建和浏览器截图通过，且业务 `/api` 请求为 0。真实里程碑完成仍需对应 OpenAPI、生成类型、Mock 契约、权限、接口测试和测试环境验收。
