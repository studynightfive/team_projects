# 账号与支持页面 Tech-Spec

## 1. 技术基线

- 沿用 Vue `3.5.39`、Vue Router `4.6.3`、Pinia `3.0.4`、Ant Design Vue `4.2.6` 与 `@lucide/vue` `1.24.0`。
- 继续使用 M01 V2 tokens 和现有 `PageHeader`、`ResourcePanel`、`InlineState` 等页面模式。
- 不新增依赖，不复制设计 tokens，不调用 API Client。

## 2. 文件与职责

```text
frontend/web/src/
├── App.vue
├── components/NotificationPreview.vue
├── data/account-support.ts
├── stores/notifications.ts
├── stores/theme.ts
├── styles/global.css
└── views/user/
    ├── NotificationsView.vue
    ├── HelpCenterView.vue
    └── PreferencesView.vue
```

- `account-support.ts` 保存严格类型的本地通知样例、FAQ 和偏好默认值。
- `notifications.ts` 只管理确实跨顶栏与页面共享的通知内存状态，不做持久化。
- `theme.ts` 管理跨路由共享的主题模式、系统配色监听与单键持久化；只接受 `system`、`light`、`dark` 三个值。
- `App.vue` 根据已解析主题切换 Ant Design Vue 算法与 token；`global.css` 通过语义变量覆盖原生页面样式。
- `NotificationPreview.vue` 复用同一 Store，为用户端和管理端顶栏输出最近通知预览，不在两个布局中复制实现。
- `NotificationsView.vue` 通过 `audience: "user" | "admin"` 路由属性复用，不建立两份页面。
- 帮助搜索与业务偏好表单保持组件局部状态；只有需要跨页面生效的主题进入 Pinia。

## 3. 路由与入口

- 用户壳层增加 `/notifications`、`/help`、`/preferences`。
- 管理壳层增加 `/admin/notifications`，复用通知页面并传入 `audience="admin"`。
- 用户端和管理端顶栏复用 `NotificationPreview`；铃铛本身仍是进入对应通知中心的 `RouterLink`。
- 用户账号菜单的偏好设置改为正式链接；移动端个人资料弹窗补充偏好设置入口。
- 新路由不加入主侧栏；搜索设置保留账号菜单入口并从用户主导航移除，因此用户主导航为 10 项，管理导航仍为 7 项，底部仍保留四项高频导航。

## 4. 状态设计

- 通知 Store 按 `user`、`admin` 隔离列表，暴露读取列表、未读计数、单条已读和全部已读四个最小操作。
- Store 初始数据从固定样例复制，防止页面操作修改导入常量。
- 通知筛选使用页面局部 `ref` 与 `computed`；离开页面后筛选恢复，通知已读状态在当前应用会话内保留。
- 通知预览直接派生 Store 中排序靠前的 4 条数据；点击预览条目复用单条已读操作，“全部已读”复用 Store 的批量操作，不建立第二份状态。
- 偏好表单使用 `reactive`，保存快照使用局部 `ref`；通过结构比较得到未保存状态。
- 主题 Store 默认读取系统配色；用户选择浅色或深色时写入固定 `localStorage` 键，选择跟随系统时移除该键并监听 `prefers-color-scheme`。
- Store 把解析后的主题写入根节点 `data-theme` 和 `color-scheme`，路由页面只消费语义样式，不各自维护主题状态。
- 不注册计时器，不监听网络，不读取浏览器通知权限。

## 5. 样式与无障碍

- 页面根节点使用 `business-page`，页头继续由 `PageHeader` 输出唯一 `h1`。
- 通知列表和偏好分组使用语义化 `article`、`form`、`fieldset`、`label`。
- FAQ 使用原生 `details/summary`；筛选按钮提供 `aria-pressed`，通知红点配套完整中文 `aria-label`。
- 桌面端预览使用原生 CSS `:hover` 与 `:focus-within` 控制显隐，通过 `left: 50%` 与水平位移使卡片中心对齐铃铛中心，不注册计时器；键盘焦点进入预览链接后保持可见。
- 767px 以下以及不支持悬停的粗指针设备隐藏预览，保留铃铛的直接路由行为。
- 767px 以下操作区、列表行和表单改为单列，交互高度不小于 44px。
- 外观模式使用原生单选组和可点击卡片，当前选择具备可见状态与原生键盘语义。
- 深色模式只覆盖现有语义 tokens 和 Ant Design Vue 主题算法，不复制页面、不修改品牌侧栏结构。
- 不使用 emoji、远程资产、渐变或新的视觉体系。

## 6. 安全与联调边界

- 所有数据为非机密固定样例，不包含真实邮箱、Token、IP、请求标识或内部路径。
- 所有本地保存文案明确写出“当前页面”或“当前会话”，不伪装服务端成功。
- 主题持久化只保存非敏感枚举值，不读取或写入账号、Token、通知内容及业务偏好。
- OpenAPI 契约确认后，先更新契约和生成类型，再替换本地数据与 Store 行为。

## 7. 验证

```powershell
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```

- 单元/组件测试覆盖入口路由、通知预览内容与跳转、预览“全部已读”、通知计数同步、通知筛选、帮助搜索、偏好保存与重置，以及主题校验、全局应用、持久化和系统配色响应。
- 浏览器验收为 `/notifications`、`/help`、`/preferences` 和 `/admin/notifications` 生成 1440、1280、375 三档截图；另对偏好页三档深色状态进行截图，并验证主题跨用户端、管理端和刷新保持。所有用例继续检查边界、溢出、标题、触控尺寸、控制台和 `/api` 请求。
