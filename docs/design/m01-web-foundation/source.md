# M01 可编辑视觉源

## 唯一来源

M01 不使用外部 Figma 文件。仓库内以下文件共同构成可追溯、可编辑的视觉源：

- [`artifact.html`](artifact.html)：页面结构、状态组合和响应式行为。
- [`tokens.css`](tokens.css)：静态 artifact 与后续实现共同复用的视觉变量。
- [`mock-data.json`](mock-data.json)：只服务设计状态的确定性示例数据。
- [`assets/manifest.md`](assets/manifest.md)：资产来源、授权和“无自定义资产”决定。

验收图必须从上述文件所在的同一 Git 提交生成。单独修改 PNG 不会改变设计基线。

## 视图入口

静态 artifact 使用查询参数切换固定视图：

```text
artifact.html?view=user
artifact.html?view=admin
artifact.html?view=states
```

`states` 视图在同一状态板中覆盖登录、加载、空、通用错误、403 和 404。所有入口均不得依赖网络资源，直接打开本地 HTML 也必须可查看。

## 导出视口

| 文件族 | 视口 |
|---|---:|
| `*-1440.png` | 1440 × 1000 |
| `*-1280.png` | 1280 × 900 |
| `*-375.png` | 375 × 812 |
| `system-states-1440.png` | 1440 × 1000 |

Chrome 截图使用 1 倍设备缩放、隐藏滚动条，不加载扩展或用户浏览器配置。具体文件映射和验收点见 [`acceptance/manifest.md`](acceptance/manifest.md)。

## 变更规则

1. 先修改 PRD、Tech-Spec 或 tokens 等上游事实来源。
2. 同步静态 artifact 与 design-only Mock。
3. 重新生成所有受影响尺寸的图片。
4. 在 PR 中记录变更原因、用户影响和视觉差异。
