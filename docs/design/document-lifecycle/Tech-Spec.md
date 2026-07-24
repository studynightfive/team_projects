# 文档批量生命周期管理技术方案

## 1. 数据模型

在 `documents` 表增加：

- `deleted_at timestamptz null`：非空表示文档位于回收站。
- `deleted_by varchar(36) null`：执行删除的用户 ID，仅用于审计展示。
- `purge_after timestamptz null`：预计物理清理时间，默认删除时间加 30 天。

普通文档查询、知识库统计、检索版本指纹和贡献统计均排除 `deleted_at IS NOT NULL`。回收站查询只返回已删除文档。

## 2. API 契约

### 2.1 批量重新处理

`POST /api/v1/documents/batch/reprocess`

请求：

```json
{
  "document_ids": ["document-id"],
  "options": {
    "ocr_enabled": true,
    "chunk_strategy": "recursive",
    "chunk_size": 800,
    "chunk_overlap": 120
  }
}
```

响应逐项返回 `document_id`、`document_title`、`task`。每个 `task.task_id` 继续使用 `GET /api/v1/tasks/{task_id}` 查询真实进度。

### 2.2 批量软删除

`POST /api/v1/documents/batch/delete`

请求最多 100 个去重后的文档 ID。响应返回删除数量和逐项文档摘要。单文档 `DELETE /api/v1/documents/{document_id}` 保持兼容，但语义改为软删除。

### 2.3 回收站

- `GET /api/v1/admin/documents/recycle-bin?page=1&page_size=20`
- `POST /api/v1/documents/batch/restore`

恢复接口为每个文档清除删除标记并创建重新处理任务，响应结构与批量重新处理一致。

## 3. 后端流程

### 3.1 上传

上传接口继续接收多文件 multipart 请求，数据库事务和存储回滚逻辑保持不变。前端仅改变提交时机，不增加临时上传接口。

### 3.2 重新处理

1. 去重并验证 1 至 100 个文档 ID。
2. 逐项验证知识库范围、角色权限、删除状态和当前处理状态。
3. 在同一事务中创建 `DocumentTask` 并将文档标记为 `uploaded`。
4. 事务提交后批量加入 ARQ 队列。
5. 前端轮询现有任务接口聚合整体进度。

任务流水线完成新分块后先激活新世代，再替换 RAG 检索投影。Worker 在开始和激活索引前检查 `deleted_at`，删除中的文档不得重新发布。

### 3.3 删除

1. 验证管理权限和部门范围。
2. 设置删除时间、删除人和清理时间。
3. 取消尚未完成的文档任务。
4. 停用全部 `document_chunks`，设置 `is_active_index=false`。
5. 删除 PostgreSQL 检索投影，并按向量后端配置移除外部向量。
6. 保留原件、Markdown、分块和历史任务。

### 3.4 恢复

恢复仅允许原知识库仍可访问的管理员执行。接口清除删除标记并创建重新处理任务；恢复后的文档在任务完成前不进入 RAG。

### 3.5 到期清理

Worker 定时任务删除 `purge_after <= now()` 的文档及存储目录。数据库外键级联清理资源、分块和任务；清理前再次撤下检索投影。清理失败记录错误类型，不记录文件内容或宿主机路径。

## 4. 前端交互

### 4.1 上传队列

上传区域维护页面局部 `File[]` 队列：

- 使用“文件名 + 大小 + lastModified”去重。
- 队列项展示名称、大小和移除按钮。
- “确认上传”一次调用现有多文件接口。
- 上传完成后保留失败项，成功项从队列移除，并刷新文档列表。

### 4.2 批量操作

文档表格支持当前页全选和跨页保留选择。批量操作栏固定显示选择数量：

- `重新处理`：确认后调用批量接口并打开进度面板。
- `删除`：危险确认后调用批量软删除接口。
- 管理端提供 `回收站` 视图，可多选恢复。

进度面板每 1 秒轮询未终止任务，页面离开时停止计时器和请求。整体进度为任务进度平均值，失败和人工复核视为终态。

## 5. 权限

- 企业知识库重新处理、删除和恢复：`admin.document.upload` / `admin.document.delete`，并受部门范围限制。
- 个人知识库重新处理：`personal.document.upload` 且 `owner_user_id == user.id`。
- 回收站仅管理端可见，超级管理员跨部门，部门管理员仅本部门。
- 前端隐藏按钮仅改善体验，所有边界由服务端再次校验。

## 6. 验证

- 后端：模型、服务、权限、软删除、恢复、到期清理、检索投影和 OpenAPI 契约测试。
- 前端：上传 6 个文件进入队列但确认前不请求；批量选择、删除、恢复；任务进度轮询；我的空间真实布局。
- 门禁：Ruff、Mypy、Pytest、前端类型检查、ESLint、Vitest、生产构建。
- 浏览器：1440px、1280px、375px，检查上传抽屉、批量操作、回收站和“我的空间”。
