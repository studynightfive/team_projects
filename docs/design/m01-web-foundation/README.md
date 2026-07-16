# M01 V2 统一前端页面基线

> 状态：正式基线。项目负责人于 2026-07-16 确认先完成 M01，并要求 M02–M14 的本地页面继承本基线；确认对应的生产实现提交为 `4903e9d`。

## 当前事实来源

| 文件 | 职责 |
|---|---|
| [`V2-Redesign-Prompt.md`](V2-Redesign-Prompt.md) | 项目负责人提供的原始视觉与内容输入 |
| [`PRD.md`](PRD.md) | 批准后的用户价值、页面结构、范围和验收 |
| [`Tech-Spec.md`](Tech-Spec.md) | Vue 实现、交互、响应式、安全和验证映射 |
| [`V2-Implementation-Spec.md`](V2-Implementation-Spec.md) | 原始提示词与仓库版本/架构冲突的处理决定 |
| [`tokens-v2.css`](tokens-v2.css) | V2 生产实现唯一共享视觉变量 |
| [`mock-data.json`](mock-data.json) | design-only 固定展示数据，不是 API Contract |
| [`assets/manifest.md`](assets/manifest.md) | 图标、字体和品牌资产来源与限制 |
| [`source.md`](source.md) | 可编辑实现与正式截图生成规则 |
| [`acceptance/manifest.md`](acceptance/manifest.md) | V2 正式截图和逐项检查点 |

事实优先级为：用户最新明确决定 > PRD/Tech-Spec/实施规格 > tokens/Mock/生产实现 > 正式截图 > 原始提示词。原始提示词不能覆盖安全边界或不存在的依赖版本。

## 当前三页

- `/login`：55:45 企业分屏登录；375px 为紧凑品牌头和单列表单。
- `/`：普通用户工作台，包含搜索、动态问候、四指标、知识库和团队动态。
- `/admin`：管理中心，包含四条 Sparkline、服务健康、治理事项和审计日志。

真实登录、权限、业务子页面和业务 API 不属于本轮；未建设操作必须提供明确的后续开放反馈。

## 技术决定

- Ant Design Vue `4.2.6` 与 pnpm `11.13.0` 已获项目负责人明确批准。
- `@lucide/vue@1.24.0` 是已废弃 `lucide-vue-next` 的官方替代包。
- 保留 Vue 3.5、Pinia 3、Vite 7 和 TypeScript strict。
- Sparkline 使用原生 SVG；不为四条静态曲线引入 ECharts。
- 继续验收 375px，不采用提示词“只支持最小 1280px”的建议。

## 历史证据

`artifact.html`、`tokens.css` 和 `acceptance/` 内原有 PNG 为 V1 历史设计证据。它们不再是 V2 的像素参考，也不得覆盖当前生产实现。V2 正式生产截图与机器报告位于 [`../../verification/m01-web-foundation`](../../verification/m01-web-foundation)。

## 本地查看

```powershell
pnpm.cmd install --frozen-lockfile
pnpm.cmd run dev:web
```

- 用户端：http://127.0.0.1:5173/
- 登录页：http://127.0.0.1:5173/login
- 管理端：http://127.0.0.1:5173/admin

## 正式基线变更规则

1. 项目负责人提出登录、用户或管理基线调整。
2. 先同步 PRD、Tech-Spec、tokens 或 Mock 中受影响的事实。
3. 修改共享组件和当前页面，并确保后续对应子页面继承最新基线。
4. 重跑类型、Lint、测试、构建、依赖和浏览器验收。
5. 生成受影响视口截图并由项目负责人确认。
