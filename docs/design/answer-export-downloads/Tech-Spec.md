# RAG 问答导出与下载记录 Tech-Spec

## 后端设计

- `POST /api/v1/exports/answer` 继续直接返回文件，保持前端下载调用兼容。
- `AnswerExportRequest.format` 增加 `pdf`，保留 `docx`、`markdown`、`txt`。
- 接口先创建当前用户的 `ExportTask`，`document_ids` 为空，状态由 `running` 转为
  `done` 或 `failed`。
- 生成文件写入 `EXPORT_STORAGE_ROOT/<task_id>/`，不再使用响应后删除的临时目录。
- 成功响应增加 `X-Export-Id`，文件通过现有签名下载接口再次下载。
- `ExportTaskResponse` 增加只读派生字段 `source_type` 和 `filename`，无需迁移：
  空 `document_ids` 映射为 `answer`，否则为 `document`。
- 问答任务下载时不执行文档权限循环；所有者、签名、过期时间及路径约束仍必须通过。

## 前端设计

- AI 搜索页使用导出弹窗选择 PDF、Word（DOCX）或 Markdown。
- 在请求后端前调用 `showSaveFilePicker`，确保保留浏览器用户激活；取消选择即终止。
- 不支持该 API 时使用带 `download` 属性的临时链接回退。
- 下载服务解析 `Content-Disposition`，以服务端文件名为最终兜底。
- “我的下载”优先展示接口返回的 `filename`；问答任务不提供“重新创建”，但保留下载和删除。

## 验证

- 后端：任务持久化、三种主格式、失败记录、再次下载权限和路径检查。
- 前端：弹窗格式切换、取消不请求、成功保存、列表问答名称与再次下载。
- 契约：重新生成 OpenAPI YAML 与 TypeScript 类型并执行一致性检查。
- 门禁：Ruff、mypy、后端相关测试、Vue 类型检查、ESLint、Vitest 和生产构建。
