# M01 V2 可编辑视觉源

## 当前来源

V2 不再使用 V1 `artifact.html` 作为生产像素事实。当前可编辑视觉源由以下内容共同构成：

- [`V2-Redesign-Prompt.md`](V2-Redesign-Prompt.md)：原始需求输入。
- [`PRD.md`](PRD.md) 与 [`Tech-Spec.md`](Tech-Spec.md)：批准后的页面与实现规则。
- [`tokens-v2.css`](tokens-v2.css)：共享视觉变量。
- [`mock-data.json`](mock-data.json)：确定性 design-only 数据。
- `frontend/web/src/`：三页可运行 Vue 静态实现和共享组件。

PNG 是由同一工作树生成的正式验收证据，不能单独编辑后作为设计变更。

## 视图入口

```text
http://127.0.0.1:5173/login
http://127.0.0.1:5173/
http://127.0.0.1:5173/admin
http://127.0.0.1:5173/403
http://127.0.0.1:5173/does-not-exist
```

Mock 模式不需要后端，不发送业务 `/api` 请求。

## 正式导出视口

| 页面 | 视口 |
|---|---:|
| 登录、用户、管理 | 1920 × 1080 |
| 登录、用户、管理、403、404 | 1440 × 1000 |
| 登录、用户、管理、403、404 | 1280 × 900 |
| 登录、用户、管理、403、404 | 375 × 812 |
| 用户/管理折叠态 | 1440 × 1000 |

浏览器使用 DPR=1、独立临时 profile、隐藏滚动条，不加载扩展或用户会话。

## 变更顺序

1. 更新 PRD、Tech-Spec、实施规格或 tokens。
2. 同步 Mock、共享组件和三页实现。
3. 运行全部本地门禁。
4. 通过 `pnpm.cmd run verify:web:browser` 重新生成生产截图和机器报告。
5. 人工检查桌面/移动布局、文字、间距、交互和长内容。

## V1 归档

`artifact.html`、`tokens.css` 与 `acceptance/` 原图片保持 V1 历史状态，仅用于追踪改版差异；V2 正式证据统一保存在 `docs/verification/m01-web-foundation/`，不回写或覆盖 V1 资产。
