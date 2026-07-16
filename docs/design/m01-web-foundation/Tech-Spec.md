# M01 V2 统一前端 Tech-Spec

## 1. 技术基线

- Node.js `22.23.1`、pnpm `11.13.0`。
- Vue `3.5.39`、Vue Router `4.6.3`、Pinia `3.0.4`。
- Ant Design Vue `4.2.6`、`@lucide/vue` `1.24.0`。
- Vite `7.3.6`、TypeScript `5.9.3` strict。
- Axios `1.18.1` 只保留统一 API Client；V2 页面不发送业务请求。

提示词写的 Ant Design Vue 5.x 当前无法从 registry 安装，`lucide-vue-next` 已被官方废弃，因此采用上述可验证版本。保留仓库当前 Vue/Pinia/Vite 版本，不按提示词降级。

## 2. 包管理与命令

- 根目录使用 `pnpm-workspace.yaml` 管理 `frontend/*`。
- 直接依赖精确锁定，提交 `pnpm-lock.yaml`，不再维护 `package-lock.json`。
- `allowBuilds` 只允许 esbuild 构建脚本，明确拒绝非必要的 core-js 安装脚本。

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run dev:web
pnpm.cmd run dev:web:api
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```

## 3. 组件树

```text
App
└── Ant ConfigProvider + App
    └── RouterView
        ├── LoginView
        ├── UserWorkspaceLayout
        │   └── WorkspaceShell
        │       ├── AppSidebar
        │       ├── User Topbar
        │       ├── MobileDrawer
        │       └── UserHomeView → StatCard
        ├── AdminWorkspaceLayout
        │   └── WorkspaceShell
        │       ├── AppSidebar
        │       ├── Admin Topbar
        │       ├── MobileDrawer
        │       └── AdminHomeView → StatCard → Sparkline
        ├── ForbiddenView
        └── NotFoundView
```

- `WorkspaceShell` 只协调共享网格、侧栏、顶栏槽位、移动抽屉和底部导航。
- 用户/管理顶栏保留在各自 Layout，避免创建难维护的万能顶栏配置对象。
- `StatCard` 复用指标结构；`Sparkline` 使用原生 SVG 平滑曲线和七个数据点，不为四条静态趋势引入 ECharts。
- `components/icons/index.ts` 只按需导出已使用 Lucide 图标，禁止 `export *`。

## 4. 路由边界

| 路径 | V2 行为 | 非范围 |
|---|---|---|
| `/login` | 分屏登录与本地交互验证 | 真实认证和会话 |
| `/` | 普通用户工作台 | 知识库/检索/问答子页面 |
| `/admin` | 管理总览 | 管理业务 API 和权限守卫 |
| `/403` | 静态无权限页 | 后端鉴权替代 |
| `/:pathMatch(.*)*` | 静态 404 | 业务重定向策略 |

当前只创建三张核心页面，不虚构子路由。尚未建设的菜单和按钮通过 Ant Design 消息明确提示所属后续里程碑，禁止 `href="#"` 或静默无效点击。

## 5. 视觉事实来源

- 原始需求输入：`V2-Redesign-Prompt.md`。
- 执行事实：`PRD.md`、本 Tech-Spec、`V2-Implementation-Spec.md`。
- 视觉变量：`tokens-v2.css`，生产 `global.css` 直接导入。
- 固定展示数据：`mock-data.json`，只供 design-only 页面和测试使用。
- V1 `artifact.html`、`tokens.css` 和旧 PNG 保留为历史证据，不参与 V2 完成判断。

## 6. Tokens 与 Ant Design

- `tokens-v2.css` 提供蓝/紫六档色阶、Slate 中性色、语义色、九档字号、四档字重、三档行高、4px 间距、四档圆角和三档阴影。
- `App.vue` 的 Ant `ConfigProvider` 只映射主色、语义色、边框、背景、圆角和系统字体。
- 业务页面不复制第二套 SCSS 变量；当前规模不引入 Sass、stylelint 或 Tailwind。
- 浅色背景上的 12/13px 辅助文字至少使用 Slate 500；Slate 400 只用于深色侧栏等仍满足对比度的场景。
- 用户焦点环为蓝色 12% 透明，管理区域为紫色 12% 透明。

## 7. 状态归属

- 账号、密码、错误、记住我、密码显隐都属于 LoginView 局部状态。
- 侧栏折叠、移动抽屉、筛选、环境选择和更新时间属于各页面/Layout 局部状态。
- `Ctrl/Cmd + K` 监听器挂载时注册、卸载时清理。
- Pinia 继续注册但不保存 design-only 状态；真实用户和权限数据等 OpenAPI 明确后再进入 store。

## 8. Mock 与隐私

- `mock-data.json` 不包含真实个人数据、凭据、权限码、Cookie、下载地址或未确认 DTO。
- 审计 IP 使用 RFC 5737 文档保留网段 `192.0.2.0/24`、`198.51.100.0/24`、`203.0.113.0/24`。
- 动态问候只根据浏览器当前小时计算，测试只断言用户名和规则结果，不把日期写入持久化状态。
- Mock/生产页面不得访问 `/api`；Mock Adapter 默认拒绝所有未注册请求。

## 9. 关键交互

### 9.1 登录

- 空提交同步生成两个中文错误，并聚焦第一个错误字段。
- 密码显隐按钮维护动态 `aria-label`、`aria-pressed`。
- 记住我只改变内存中的复选状态，不写存储。
- 填写后提交只显示“认证接口将在 M02 接入”，不记录字段值。

### 9.2 侧栏和顶栏

- 桌面侧栏 240px，可在 200ms 内折叠到 64px；折叠按钮维护 `aria-expanded`。
- 用户菜单通过点击打开，支持 Escape，不依赖 hover 作为唯一入口。
- 用户顶栏搜索宽度最大 480px；`Ctrl/Cmd + K` 聚焦输入框。
- 通知红点同时提供包含数量的中文可访问名称。

### 9.3 移动抽屉

- 375px 隐藏桌面侧栏，菜单按钮维护 `aria-expanded`/`aria-controls`。
- 支持关闭按钮、遮罩、Escape、Tab/Shift+Tab 焦点循环、关闭后焦点返回和卸载滚动锁清理。
- 所有主要触控区域不小于 44px。

## 10. 响应式实现

- 桌面：`240px minmax(0, 1fr)`；折叠：`64px minmax(0, 1fr)`。
- 顶栏 56px；内容有效宽度最大 1280px，桌面 gutter 32px。
- 登录桌面 `55% 45%`，表单 360px；900px 以下改为单栏。
- 1280px 仍保持四张指标卡；1180px 以下管理运营区改单列。
- 767px 以下所有指标和内容区改单列，gutter 16px，底部导航 68px。
- 审计表最小内容宽度 920px，只在 `.audit-table-scroll` 内横向滚动。

## 11. 可访问性

- 一个页面一个 `h1`；标题、导航、区域和表格使用语义元素。
- 文字按钮和图标按钮均可键盘聚焦；focus-visible 不被裁切。
- 状态徽章同时显示文字；颜色不是唯一信号。
- Sparkline 使用 `role="img"` 和中文趋势标签；28 个点由测试与浏览器脚本锁定。
- 动画遵守 `prefers-reduced-motion`。

## 12. 验证

自动化门禁：

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd audit
pnpm.cmd run verify:web:browser
git diff --check
```

浏览器脚本覆盖 20 个用例：用户、管理、登录的 1920/1440/1280/375，用户/管理折叠 1440，以及 403/404 的 1440/1280/375。检查顶栏、侧栏、四指标、Sparkline、审计表头、登录错误/显隐、移动抽屉、触控尺寸、根级溢出、控制台错误和业务 API 请求。
