# M01 统一前端设计基线

> 对应 Issue：[#9](https://github.com/studynightfive/team_projects/issues/9)
> 状态：已由非作者批准并通过 PR #10 合入 `main`，现为 M01 实施基线
> 适用里程碑：M01 `web-foundation`

本目录是 M01 的项目级设计事实来源，不包含 `frontend/web/`、依赖、真实 API、认证或权限实现。它先于员工 1 的唯一 P0 总 Issue 合入 `main`，并在实现阶段继续用于生产截图对照，避免一边实现一边发明验收口径。

## 文件职责

| 文件 | 职责 |
|---|---|
| [`PRD.md`](PRD.md) | 用户价值、信息架构、页面状态和可观察验收 |
| [`Tech-Spec.md`](Tech-Spec.md) | Vue 实现映射、响应式、可访问性和边界 |
| [`tokens.css`](tokens.css) | M01 实际使用的语义视觉变量 |
| [`mock-data.json`](mock-data.json) | design-only 固定展示数据，不是 API Contract |
| [`assets/manifest.md`](assets/manifest.md) | 真实资产来源与无自定义资产决定 |
| [`source.md`](source.md) | 可编辑视觉源与截图生成规则 |
| [`artifact.html`](artifact.html) | 可离线查看的静态 UI 事实来源 |
| [`acceptance/manifest.md`](acceptance/manifest.md) | 七张验收图及逐图检查点 |

## 已固定决定

- 产品名称只使用“智能知识库平台”，不创造品牌简称。
- M01 不使用自定义 Logo、插画、Web Font 或远程图片。
- 页面采用系统字体和文字产品名；M01 不为装饰图标新增依赖。
- 视觉方向为克制、清晰、高密度但不拥挤的企业知识工具。
- 桌面端使用 240px 侧栏与 64px 顶栏；375px 隐藏侧栏并保留可达的移动导航。
- Mock 只证明布局和状态，不包含 `/me`、权限码、Token、Cookie、后端错误结构或未确认 DTO。

这些视觉值和资产取舍已由项目负责人以非作者身份批准，任何后续变更都应同步更新可编辑 artifact 与验收截图。

## 本地查看

直接打开 [`artifact.html`](artifact.html)，或使用查询参数固定视图：

```text
artifact.html?view=user
artifact.html?view=admin
artifact.html?view=states
```

静态 artifact 不访问网络，不需要安装依赖。截图尺寸与文件名见 [`acceptance/manifest.md`](acceptance/manifest.md)。

## M01 实现边界

实现阶段可以复用 tokens、文案、布局尺寸和状态结构，但不得把 design-only Mock 当成 OpenAPI。M01 只建立工程和壳层；登录逻辑、路由守卫、权限码、401 刷新和业务页面仍属于后续里程碑。
