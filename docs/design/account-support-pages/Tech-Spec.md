# 账号与支持页面 Tech-Spec

## 1. 技术基线

- 沿用 Vue `3.5.39`、Vue Router `4.6.3`、Pinia `3.0.4`、Ant Design Vue `4.2.6` 与 `@lucide/vue` `1.24.0`。
- 继续使用 M01 V2 tokens 和现有 `PageHeader`、`ResourcePanel`、`InlineState` 等页面模式。
- 不新增依赖，不复制设计 tokens，不调用 API Client。

## 2. 文件与职责

```text
frontend/web/src/
├── components/NotificationPreview.vue
├── data/account-support.ts
├── stores/notifications.ts
└── views/user/
    ├── NotificationsView.vue
    ├── HelpCenterView.vue
    └── PreferencesView.vue
```

- `account-support.ts` 保存严格类型的本地通知样例、FAQ 和偏好默认值。
- `notifications.ts` 只管理确实跨顶栏与页面共享的通知内存状态，不做持久化。
- `NotificationPreview.vue` 复用同一 Store，为用户端和管理端顶栏输出最近通知预览，不在两个布局中复制实现。
- `NotificationsView.vue` 通过 `audience: "user" | "admin"` 路由属性复用，不建立两份页面。
- 帮助搜索与偏好表单保持组件局部状态，不进入 Pinia。

## 3. 路由与入口

- 用户壳层增加 `/notifications`、`/help`、`/preferences`。
- 管理壳层增加 `/admin/notifications`，复用通知页面并传入 `audience="admin"`。
- 用户端和管理端顶栏复用 `NotificationPreview`；铃铛本身仍是进入对应通知中心的 `RouterLink`。
- 用户账号菜单的偏好设置改为正式链接；移动端个人资料弹窗补充偏好设置入口。
- 新路由不加入主侧栏，不改变现有 11 项用户导航、7 项管理导航和底部四项高频导航。

## 4. 状态设计

- 通知 Store 按 `user`、`admin` 隔离列表，暴露读取列表、未读计数、单条已读和全部已读四个最小操作。
- Store 初始数据从固定样例复制，防止页面操作修改导入常量。
- 通知筛选使用页面局部 `ref` 与 `computed`；离开页面后筛选恢复，通知已读状态在当前应用会话内保留。
- 通知预览直接派生 Store 中排序靠前的 4 条数据；点击预览条目复用单条已读操作，不建立第二份状态。
- 偏好表单使用 `reactive`，保存快照使用局部 `ref`；通过结构比较得到未保存状态。
- 不注册计时器，不监听网络，不读取浏览器通知权限。

## 5. 样式与无障碍

- 页面根节点使用 `business-page`，页头继续由 `PageHeader` 输出唯一 `h1`。
- 通知列表和偏好分组使用语义化 `article`、`form`、`fieldset`、`label`。
- FAQ 使用原生 `details/summary`；筛选按钮提供 `aria-pressed`，通知红点配套完整中文 `aria-label`。
- 桌面端预览使用原生 CSS `:hover` 与 `:focus-within` 控制显隐，不注册计时器；键盘焦点进入预览链接后保持可见。
- 767px 以下以及不支持悬停的粗指针设备隐藏预览，保留铃铛的直接路由行为。
- 767px 以下操作区、列表行和表单改为单列，交互高度不小于 44px。
- 不使用 emoji、远程资产、渐变或新的视觉体系。

## 6. 安全与联调边界

- 所有数据为非机密固定样例，不包含真实邮箱、Token、IP、请求标识或内部路径。
- 所有本地保存文案明确写出“当前页面”或“当前会话”，不伪装服务端成功。
- OpenAPI 契约确认后，先更新契约和生成类型，再替换本地数据与 Store 行为。

## 7. 验证

```powershell
pnpm.cmd run typecheck:web
pnpm.cmd run lint:web
pnpm.cmd run test:web
pnpm.cmd run build:web
pnpm.cmd run verify:web:browser
```

- 单元/组件测试覆盖入口路由、通知预览内容与跳转、通知计数同步、通知筛选、帮助搜索、偏好保存与重置，以及零 API/零存储写入。
- 浏览器验收为 `/notifications`、`/help`、`/preferences` 和 `/admin/notifications` 生成 1440、1280、375 三档截图；通知路由的桌面截图保持悬停预览打开，并检查预览可见性、边界、溢出、标题、触控尺寸、控制台和 `/api` 请求。
