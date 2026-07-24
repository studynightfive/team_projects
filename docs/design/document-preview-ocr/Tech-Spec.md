# 文档三视图与 OCR 展示技术规格

## 现有能力

- `DocumentStorage` 已按文档隔离保存 `original/`、`markdown/`、`assets/` 和
  `manifest.json`。
- `DocumentService` 已统一执行知识库访问校验。
- `MarkdownConverter` 已清洗 HTML，并保留页码、OCR 置信度注释和处理告警。
- `document_chunks` 已保存标题、页码、字符范围、Token 估算、向量和索引代次。

## API

### `GET /api/v1/documents/{document_id}`

在 `DocumentDetail` 中增加 `ocr`：

- `status`: `disabled | pending | not_required | completed | low_confidence | unavailable`
- `language`: OCR 语言配置
- `average_confidence`: 可为空的 0 到 1 数值
- `review_required`: 是否建议人工复核
- `message`: 面向用户的稳定说明

### `GET /api/v1/documents/{document_id}/original`

- Query `download=false` 时返回 `Content-Disposition: inline`。
- Query `download=true` 时返回 `Content-Disposition: attachment`。
- Content-Type 使用上传时交叉校验后的文档 MIME。
- 路径只由服务端根据文档 ID 和存储文件名解析，响应不包含物理路径。

### `GET /api/v1/documents/{document_id}/chunks`

返回 `APIResponse<PaginatedData<ChunkItem>>`：

- Query `page` 默认 1，最小 1。
- Query `page_size` 默认 20，范围 1 到 100。
- 仅返回当前活动索引代次。
- `ChunkItem` 增加 `token_estimate`、`index_generation` 和
  `embedding_status`。

## OCR 摘要

不新增数据库列。处理管线在写入 `manifest.json` 前，根据解析块的 `source=ocr`、
置信度和告警生成结构化 `ocr` 字段：

- 未启用 OCR：`disabled`
- 没有 OCR 块且无 OCR 告警：`not_required`
- 有 OCR 块且平均置信度不低于 0.70：`completed`
- 有 OCR 块但平均置信度低于 0.70：`low_confidence`
- OCR 未识别到内容或工具不可用：`unavailable`

历史文档没有 `ocr` 字段时，服务层根据文档配置和已有清单兼容推导，不要求重新迁移。

## 前端

- 使用标签页切换原文、Markdown、分块，默认原文。
- 原文由 Axios 以 Blob 获取，组件卸载或文档切换时撤销 Object URL。
- PDF 使用 `object`，图片使用 `img`，文本使用受控文本区；Office 显示下载操作。
- Markdown 继续使用 `SafeMarkdown`。
- 分块按需加载和分页，不在进入页面时一次读取全部分块。
- 所有加载请求使用同一个页面级 AbortController，并处理快速切换。

## 安全

- 所有资源读取先执行 `user_can_access_kb`。
- 下载文件名由 `FileResponse` 的受控参数生成，不接受客户端路径。
- 原文响应增加 `X-Content-Type-Options: nosniff` 和私有缓存策略。
- 页面不把 Token 写入 URL、Object URL 以外的持久化位置或日志。
