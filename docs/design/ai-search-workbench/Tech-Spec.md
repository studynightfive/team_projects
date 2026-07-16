# AI 搜索工作台升级 Tech-Spec

## 1. 现有基线与约束

- 复用 Vue `3.5.39`、TypeScript strict、Vue Router `4.6.3`、Pinia `3.0.4`、Ant Design Vue `4.2.6`、Axios `1.18.1` 与 `@lucide/vue` `1.24.0`。
- 本升级仅取代 M01 的用户首页内容基线；继续使用 M01 `tokens-v2.css`、`WorkspaceShell`、`AppSidebar`、`MobileDrawer`、统一按钮和焦点样式，不建立第二套主题或壳层。
- 新增固定运行时依赖 `markdown-it` `14.1.0`、`dompurify` `3.3.0`，以及固定开发依赖 `@types/markdown-it` `14.1.2`；不再引入其他渲染或流式依赖。
- 固定 Mock 的结构化区域使用 Vue 模板输出；本地 Markdown 文本经禁用原始 HTML 的 Markdown-It 解析和 DOMPurify 二次过滤后渲染。真实服务端内容在服务端清洗契约落实前不得接入。
- 页面局部筛选、弹窗和表单继续使用 `ref`/`computed`；当前没有跨页持久化需求，不新增 Pinia 业务 Store。
- 本轮不推送 GitHub、不创建 Pull Request；只有用户完成观察、调整并明确同意后，才进入上传流程。

## 2. 目录职责

```text
frontend/web/src/
├── components/search/       搜索框、答案、引用、结果、上下文和文档预览
├── mocks/ai-search.ts       确定性中文视图数据
├── services/ai-search.ts    可替换的本地异步服务边界
├── types/ai-search.ts       页面领域模型
└── views/user/              结果、研究、空间、数据源、历史、收藏和设置
```

- 组件只接收显式 Props/Emits，不建立配置驱动的万能页面生成器。
- Mock Service 不调用 Axios 或 Fetch；支持 `AbortSignal`，便于后续替换真实检索且能在页面离开时清理。
- `api/client.ts` 保持不变；OpenAPI 确认后再增加真实 API service 和生成类型适配器。契约未确认的字段、权限、认证和连接状态仅使用明确标注的本地模拟数据。

## 3. 搜索数据流

1. `AiSearchBox` 在组件内维护输入高度和附件元数据，向页面发出完整 `SearchRequest`。
2. 首页校验查询后通过路由 query 进入 `/search`；模式、范围和模型使用稳定英文值，不把敏感信息写入 URL。
3. `SearchView` 调用本地 `runAiSearch()`，状态依次为 `searching` 与 `success`/`partial`/`error`。
4. 结果页的标签、筛选、预览、反馈和收藏仅更新当前页面内存状态。
5. 路由切换或重新检索时取消上一请求，避免过期结果覆盖新查询。

## 4. 安全与可信表达

- Markdown-It 配置 `html: false`，解析结果必须经 DOMPurify 过滤后才能传给 `v-html`；禁止脚本、事件属性、样式、表单、嵌入对象和危险 URL。引用、表格、列表和重点提示优先由受控字段渲染。
- 上传入口仅在前端校验扩展名、MIME、10 MB 上限和最多 5 个文件，不读取或上传内容。
- 外部链接仅在未来契约确认后开放；当前预览使用内部路由/按钮，不拼接可猜测下载地址。
- 状态同时使用中文文字和图标；权限受限、过期、待确认不能只用颜色表达。
- Mock 数据只使用虚构姓名、保留域名和非敏感内容，并统一显示“模拟数据”。

## 5. 响应式与可访问性

- `>= 1180px`：左侧导航、中央内容和可选右侧上下文并列。
- `768–1179px`：侧栏保留或折叠，右侧上下文改为覆盖抽屉，结果正文单列优先。
- `< 768px`：使用现有移动导航抽屉与底部导航；搜索工具栏换行；预览全屏；触控高度至少 44px。
- 搜索框、标签页、反馈和抽屉均提供可访问名称、`aria-live`、键盘提交、Escape 关闭和清晰焦点环。
- 动画只使用 150–200ms 状态过渡，并继承 reduced-motion 规则。

## 6. 测试策略

- 单元测试：Mock Service 空查询、取消、确定性结果；搜索框 Enter/Shift+Enter、快捷回填和附件限制。
- 组件/路由测试：首页提交、结果标签切换、筛选、引用预览、反馈、历史/收藏删除确认和旧路由回归。
- 浏览器验收：1440px、1280px、1024px、768px、375px；检查根级溢出、唯一 `h1`、中文、Emoji、导航、抽屉、控制台和业务请求。
- 安全与可访问性验收：验证恶意 Markdown 不进入最终 DOM；键盘提交、标签切换、Escape 关闭、焦点返回、可访问名称、`aria-live` 和焦点环可用。
- 网络验收：五个目标视口与核心交互全程不发起真实业务请求；所有数据来自本地 Mock Service。
- 完整命令：

```powershell
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```

## 7. 后端接入点

- 将 `services/ai-search.ts` 的本地实现替换为基于生成 OpenAPI 类型的 Adapter；页面和组件 Props 保持不变。
- 搜索结果改为真实分页/流式事件时，沿用原生 Fetch、ReadableStream、TextDecoder 与 AbortController。
- 真实 Markdown 先经服务端清洗，再使用固定版本 Markdown-It 解析和 DOMPurify 二次过滤。
- 上传、导出、收藏、历史和数据源写操作必须分别接入权限校验、错误结构与重试语义，不能沿用本地成功提示。
