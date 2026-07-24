# 移动端关键流程适配 Tech-Spec

## 1. 设计原则

- 继续复用现有 Vue 3、Ant Design Vue 和语义 CSS，不引入设备判断依赖。
- 以 CSS 媒体查询处理布局，以现有组件状态处理交互。
- 页面级横向滚动始终禁止；宽表只允许在 `.data-table-scroll` 内部滚动。
- 浮层尺寸使用视口约束和安全区，不在每个页面重复计算设备宽度。

## 2. 共享样式

在 `frontend/web/src/styles/global.css` 的 `max-width: 767px` 区域增加：

- `.ant-drawer-content-wrapper` 最大宽度为视口宽度。
- Drawer 头部、正文和关闭按钮适配 16px 间距、44px 触控目标和底部安全区。
- Modal 最大宽度为 `100vw - 24px`，正文可滚动，页脚按钮在窄屏中等宽排列。
- `.data-table.mobile-sticky-actions` 的最后一列在滚动容器右侧固定。
- 表格滚动区域使用触控惯性滚动和可见滚动提示。

仅关键业务表格添加 `mobile-sticky-actions`，避免无操作列的审计与结果表被错误固定。

## 3. 页面适配

### 3.1 AI 搜索

- 结果动作保持两列，长文案自动换行。
- 答案导出 Modal 使用统一移动端浮层规则。
- 结果筛选面板和搜索上下文继续使用现有全屏覆盖逻辑。
- 流式回答区域保证长文本、代码块和引用不会撑破容器。

### 3.2 知识库与上传

- 上传区手机端缩小留白但保持清晰的点击入口。
- 切分策略、大小和重叠字符改为单列。
- 文档表格的操作列固定在右侧。

### 3.3 文档详情

- 原文、Markdown、分块按钮保持三等分和 44px 高度。
- PDF、图片、Markdown 表格和代码块只在自身容器滚动。
- 分块元数据在手机端采用两列，长值允许换行。

### 3.4 管理端

- 用户、知识库、文档等含操作列的关键表格启用右侧固定操作列。
- 用户新建/编辑 Drawer、角色授权 Drawer 和检索测试 Drawer 统一由全局规则限制宽度。
- 看板筛选器、指标卡和排行榜保持单列/内部滚动。

## 4. 自动化验证

扩展 `frontend/web/scripts/verify-browser.mjs`：

- 保留全部路由的 1440px、1280px、375px检查。
- 增加用户编辑 Drawer、答案导出 Modal、结果筛选面板和文档三视图状态。
- 记录浮层边界、关闭按钮高度、主要操作高度、表格操作列可见性和根节点溢出。
- 生成对应截图和 JSON 报告。

组件测试补充：

- 关键表格包含移动端固定操作列标识。
- Drawer 和 Modal 的语义状态、关闭操作与表单状态不回归。
- 文档三视图切换和上传入口保持可访问。

## 5. 验证命令

```powershell
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```

浏览器证据必须覆盖 375px、1280px 和 1440px；修改前后均检查控制台错误和业务 API 请求数量。
