# 我的下载真实 API 与数据源页面移除修正记录

更新时间：2026-07-19

## 背景

交付演示范围已收敛到企业知识库闭环：登录、企业知识库、文档上传处理、RAG 检索问答、历史、收藏和下载。原用户端“数据源”页面属于前期演示样例，且“我的下载”页面仍读取固定 Mock 任务，容易在联调时误导为真实业务能力。

## 修正内容

1. 移除用户端数据源页面入口：
   - 删除 `/data-sources` 路由。
   - 从用户侧栏、移动抽屉、顶部状态栏和首页快捷入口中移除“数据源”。
   - 删除未挂载的 `DataSourcesView.vue` 页面文件。
   - 搜索页可见文案从“数据源”调整为“知识来源/来源”，避免和已移除页面混淆。

2. 将“我的下载”接入真实导出 API：
   - 新增 `frontend/web/src/services/downloads.ts`。
   - 真实 API 模式下，`/downloads` 调用 `GET /api/v1/exports` 读取任务。
   - 已完成任务通过后端返回的签名 `download_url` 走鉴权接口下载文件。
   - 删除任务调用 `DELETE /api/v1/exports/{export_id}`。
   - 失败或过期任务保留“重新创建”，复用原任务文档 ID 和格式调用 `POST /api/v1/exports`。
   - Mock/测试模式继续使用本地样例，保证历史设计回归不请求业务接口。

3. 修正导出权限兼容：
   - 后端导出路由改为兼容旧权限码 `export.view/export.create` 和新权限码 `export:read/export:write/export:download/export:delete`。
   - 种子权限补充标准 `export:*` 权限，供新环境初始化使用。

## 大修说明

本次没有对组员核心业务代码做大规模重构。后端只调整导出路由权限依赖；前端下载页保留原布局和筛选交互，仅替换真实模式的数据来源与操作函数。

## 验证记录

- `pnpm.cmd run typecheck:web`：通过。
- `pnpm.cmd run lint:web`：通过。
- `pnpm.cmd run test:web`：10 个测试文件、87 条测试通过。
- `pnpm.cmd run build:web`：通过。
- `python -m compileall backend\app\exports\all.py backend\app\common\seed.py`：通过。
- `ruff check backend\app\exports\all.py backend\app\common\seed.py`：通过。

## 剩余限制

- 导出模块现有 `_fetch_document_content` 仍是员工 5 原占位实现，创建导出文件的正文还没有读取员工 4 文档 Markdown 服务；本次只保证“我的下载”页面不再展示固定样例，并能对接真实任务列表、鉴权下载和删除接口。
- 帮助、偏好设置等辅助页面仍含界面级样例，不属于本次企业知识库交付闭环；通知中心已在后续修正中接入真实 API。
