# M01 V2 前端改版实施规格

## 1. 状态与事实来源

- 生效日期：2026-07-15。
- 用户批准的视觉与内容来源：[`V2-Redesign-Prompt.md`](V2-Redesign-Prompt.md)。
- 本规格覆盖原 M01 PRD、Tech-Spec 中与三页视觉、页面结构、UI 库和包管理器冲突的部分；认证、权限、API 和安全边界继续沿用原规格。
- 登录页、普通用户工作台、管理中心分别作为后续对应子页面的最新界面基线。

## 2. 已确认技术决定

- UI 库从 Element Plus 切换为 `ant-design-vue@4.2.6`。用户允许采用 Ant Design；registry 当前不存在提示词写的 Ant Design Vue 5.x，因此使用可验证的最新稳定版 4.2.6。
- 包管理器从 npm 切换为 `pnpm@11.13.0`，新增 `pnpm-workspace.yaml` 并提交 `pnpm-lock.yaml`，删除 npm 锁文件。
- 线性图标使用 `@lucide/vue@1.24.0`，禁止 emoji 和字符拟态图标。提示词指定的 `lucide-vue-next` 已被官方废弃，registry 明确要求迁移到该替代包。
- 保留 Vue 3.5、TypeScript strict、Vue Router 4、Pinia 3 和 Vite 7 的仓库固定版本。
- 样式继续使用共享 CSS Variables；当前页面规模不足以证明引入 Sass、stylelint 或 ECharts 的必要性。Sparkline 使用可访问的内联 SVG，避免增加图表依赖。
- V2 生产实现直接导入 [`tokens-v2.css`](tokens-v2.css)；原 `tokens.css` 与 V1 artifact 保持历史一致，不再作为生产视觉事实来源。
- 提示词写明桌面最小 1280px，但仓库强制验收 375px；实现必须同时覆盖 1440px、1280px 和 375px。

## 3. 本轮范围

### 3.1 登录页

- 桌面采用 55:45 深色品牌区与白色表单区的分屏布局，页面高度固定为 100vh。
- 包含品牌、主标语、三项价值点、版权与版本信息、账号密码表单、密码可见切换、记住我、SSO、三种第三方入口和法律声明。
- 375px 采用单栏表单，保留精简品牌信息，不出现横向滚动。
- 只实现本地校验和交互反馈，不发送账号、密码或任何认证请求。

### 3.2 普通用户工作台

- 240px 深色侧栏可折叠至 64px；顶栏包含面包屑、全局搜索、通知、帮助和头像。
- 主体包含动态问候、两个主操作、四张指标卡、最近访问知识库和团队动态。
- `Ctrl/Cmd + K` 聚焦搜索；侧栏折叠、用户菜单和移动抽屉为本地状态。

### 3.3 管理中心

- 与用户端共享布局结构，主色切换为 `#553C9A`。
- 顶栏包含环境选择、通知、管理员头像和返回用户工作区。
- 主体包含标题与筛选、四张带 Sparkline 指标卡、服务健康、待治理事项和审计日志表格。

## 4. 明确非范围

- 不实现真实登录、退出、找回密码、SSO 或第三方登录。
- 不实现业务子页面、权限守卫或后端 API；未建设的导航项必须明确提示后续开放，禁止继续使用无反馈的 `href="#"`。
- 不创建虚构 OpenAPI、权限码、下载地址或真实组织/个人数据。
- 不引入品牌图片；在正式 Logo 缺失时使用 Lucide 线性图标组成可替换的平台标记。

## 5. 数据和状态

- `mock-data.json` 仍是 design-only 数据，不是后端契约。
- 表单值、侧栏折叠、下拉菜单、筛选和更新时间保留为页面局部状态。
- 未确认业务接口不得进入 API Client；浏览器验收必须保持业务 `/api` 请求为 0。

## 6. 验收标准

- 三页符合 V2 提示词的色彩、字号、间距、圆角、阴影和中文文案要求。
- 页面无 emoji；所有图标来自 Lucide。
- 所有真实可交互元素具备 hover、active、focus-visible 和适当的 disabled 状态。
- 登录表单具备默认、hover、focus、error 和 disabled 样式；本地提交不持久化凭据。
- 用户端四张指标卡包含图标、指标和值/趋势；管理端四张指标卡均包含 Sparkline。
- 管理端表头为 `#F1F5F9`，紫色只作点缀，不形成大面积内容背景。
- 1440px、1280px、375px 无根级横向滚动、重叠、重要文字截断或主要操作不可达。
- TypeScript、Lint、单元/组件测试、生产构建、依赖审计和浏览器验收全部通过。

## 7. 验证命令

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```
