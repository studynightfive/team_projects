# M01 Web Foundation Tech-Spec

## 1. 目标与约束

本规格把 M01 设计基线映射为 Vue 3 实现边界。设计基线已通过 PR #10 合入；生产代码在统一 P0 长期分支中按本规格实现。

固定技术基线：Vue 3、Vue Router、Pinia、Element Plus、Vite 与 TypeScript strict。直接依赖版本以根 `AGENTS.md` 和锁文件为准；安全补丁升级必须同步事实来源并重新执行全部门禁。

## 2. 目标布局树

```text
App
└── ElConfigProvider
    └── RouterView
        ├── LoginView
        ├── UserWorkspaceLayout
        │   └── WorkspaceShell → RouterView → UserHomeView
        ├── AdminWorkspaceLayout
        │   └── WorkspaceShell → RouterView → AdminHomeView
        ├── ForbiddenView
        └── NotFoundView
```

M01 只建立布局和占位路由。M02 才实现登录态、守卫、`usePermission()`、401 刷新和权限撤销清理。

## 3. M01 路由壳

| 路径 | M01 行为 | 非范围 |
|---|---|---|
| `/login` | 登录视觉骨架 | 真实提交和会话 |
| `/` | 普通工作区壳层 | 业务数据加载 |
| `/admin` | 管理中心壳层 | 权限判断和管理 API |
| `/403` | 静态无权限页 | 后端鉴权替代 |
| `/:pathMatch(.*)*` | 静态 404 页 | 业务重定向策略 |

`/admin` 在 M01 的 Mock 入口只证明布局可进入，不代表普通用户允许访问。M02 必须实现“普通用户 403 且不请求管理数据”。

## 4. 目录映射

M01 按以下最小范围落地：

```text
frontend/web/src/
├── api/
├── layouts/
├── mocks/
├── router/
├── styles/
├── tests/
└── views/
```

不为 M02–M15 预建空 feature 目录或一次性抽象。只有真实跨模块复用后才把组件提升到共享目录。

## 5. Tokens

[`tokens.css`](tokens.css) 是 M01 语义视觉变量的单一事实来源：

- 色彩使用稳定的语义或布局用途命名，不按单页或临时实现值命名。
- 间距以 4px 为基础，避免页面自行发明数值。
- 侧栏、顶栏、内容 gutter 和移动导航尺寸直接映射布局。
- 生产 Vue 实现直接导入同一文件，并按 Element Plus CSS variables 做最小映射。

不得复制为第二份 JSON tokens 或在组件中重写一套等价值。需要改视觉值时先改 `tokens.css` 并重新生成截图。

## 6. 状态归属

- Pinia 在 M01 只完成注册，不保存表单、弹窗、页码、筛选或状态页加载标志。
- M01 登录输入只保留浏览器原生局部值且不提交；M02 才增加真实提交状态。
- 当前用户、权限和当前知识库只有在真实跨页面需求出现后进入 store。
- 设计 artifact 不模拟 store，不持久化任何数据。

## 7. API Client 与 Mock 边界

M01 API Client 的最小职责：

- `baseURL` 使用 `/api`。
- Cookie 会话请求设置 `withCredentials`。
- 把外部错误收窄为不泄露内部信息的统一前端错误边界。

M01 不实现刷新 Token、真实认证 DTO、权限码或业务接口。

[`mock-data.json`](mock-data.json) 标记为 `design-only`。它只固定卡片数量、文字长度和状态组合，不得生成 OpenAPI 类型，也不得被测试称为后端契约。M01 直接复用其展示内容，Mock Adapter 不注册虚构业务端点并默认拒绝网络；后续接口形状必须以已提交 OpenAPI 为准。

## 8. 静态 artifact

[`artifact.html`](artifact.html) 与 [`tokens.css`](tokens.css) 是可编辑视觉源：

- 不加载 CDN、远程字体、图片或脚本。
- `view=user|admin|states` 固定截图入口。
- 直接从本地文件打开可查看；截图过程不依赖登录态或后端。
- JavaScript 只负责选择静态视图和移动端导航展示，不执行动态代码或网络请求。

PNG 是由 artifact 派生的证据，不能单独编辑后作为事实来源。

## 9. 响应式实现规则

### 9.1 桌面（≥ 768px）

- CSS Grid：`240px minmax(0, 1fr)`。
- 顶栏高度 64px，内容 gutter 32px。
- 摘要区按验收 artifact 使用桌面四列、1180px 以下两列、767px 以下单列，普通用户三张卡在桌面保留第四列空位。
- 表格容器允许内部滚动，但页面根节点不产生横向滚动。

### 9.2 移动（≤ 767px）

- 侧栏 `display: none`，不保留空白列。
- 顶栏左右内容必须允许 `min-width: 0`，长标题省略。
- 菜单按钮通过本地 drawer 展示当前区域的完整模块导航和跨工作区入口，维护 `aria-expanded` / `aria-controls`，支持关闭按钮、Escape 退出和 Tab 首尾焦点循环。
- 内容 gutter 16px，卡片单列。
- 普通工作区底部导航高度 68px，内容区预留安全间距。
- 表格转为带标签的列表卡，不把宽表缩到不可读。

## 10. 可访问性实现规则

- 使用 `header`、`nav`、`main`、`section` 和正确标题层级。
- 图标按钮必须有可访问名称，装饰图形标记为隐藏。
- 表单控件使用显式 `label`，错误文字与控件关联。
- 可点击元素最小高度 44px；键盘顺序与视觉顺序一致。
- 使用 `:focus-visible` 和 `--shadow-focus`，不全局移除 outline。
- 加载状态保留可读文字，并通过 `aria-live="polite"` 提供动态反馈语义。

## 11. 安全边界

- 不把 Token、Cookie、密码、密钥、内部堆栈或真实请求体写入日志、Mock 或截图。
- 登录输入在 artifact 中为空，不提供示例凭据。
- 403 状态不渲染管理数据占位，避免形成“先加载后隐藏”的错误模式。
- `VITE_*` 会进入浏览器产物，后续不得用于 secret。

## 12. 验证

设计 PR：

- JSON 可解析，CSS/HTML 结构可读。
- Markdown 相对链接存在。
- artifact 三个视图可离线打开。
- 七张截图尺寸与清单一致。
- 1440px、1280px、375px 无根级横向溢出、文字重叠或关键操作遮挡。
- `git diff --check` 通过。

M01 生产实现必须运行：

```powershell
npm.cmd ci
npm.cmd run typecheck:web
npm.cmd run lint:web
npm.cmd run test:web
npm.cmd run build:web
npm.cmd run verify:web:browser
```

视觉实现须把生产截图与本目录验收图逐项对照；真实 API、认证与权限不在 M01 完成声明中。
