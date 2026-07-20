# 通知真实 API 与 RAG 索引链路核查记录

日期：2026-07-19

## 通知中心修正

原状态：用户端和管理端通知中心、顶栏通知预览均读取 `notificationSeeds` 和本地 Pinia 状态，未请求真实业务接口。

已修正：

- 新增后端通知表 `notifications` 和迁移 `0010_notifications`。
- 新增真实接口：
  - `GET /api/v1/notifications?audience=user|admin`
  - `PATCH /api/v1/notifications/{notification_id}/read`
  - `POST /api/v1/notifications/mark-all-read?audience=user|admin`
- 用户通知按当前登录用户持久化；管理员通知为管理员视角全局通知，非管理员不能读取管理通知。
- 前端 `NotificationPreview` 与 `NotificationsView` 改为真实 API 模式下加载后端通知，已读状态写回后端。
- 默认通知使用确定性 ID 和 PostgreSQL `ON CONFLICT DO NOTHING`，避免顶栏和页面并发首次加载时重复生成。

## 文档上传处理核查

代码链路：

- 上传接口：`backend/app/documents/router.py`
- 处理服务：`backend/app/documents/service.py`
- Markdown 转换：`MarkdownConverter.convert(...)`
- Markdown 落盘：`DocumentStorage.write_markdown_package(...)` 写入 `storage/documents/<document_id>/markdown/content.md`
- 切块：`Chunker.split(...)` 优先按 Markdown 标题、段落、表格和代码块形成语义块；知识库 `chunk_size` 与 `chunk_overlap` 只用于超长段落的兜底拆分
- 入库：写入 `document_chunks`，字段包含 `content`、`chunk_no`、`token_estimate`、`embedding_json`、`index_generation`、`is_active`

数据库核查：

- 当前上传文档 `医疗信息化 IT 系统分析文档` 状态为 `ready`。
- `markdown_path` 已写入 `storage/documents/<document_id>/markdown/content.md`。
- `document_chunks` 当前有 30 个 active chunk。
- 30 个 chunk 均有 `embedding_json`。

结论：上传文档会被转换为 Markdown，并切块保存到 `document_chunks`。

追加修正：

- 2026-07-19 已将 `Chunker` 从“按固定大小聚合多个 Markdown 单元”调整为“标题/段落优先”的语义切分。
- 标题行会单独成为可检索块；标题下的每个段落、表格和代码块分别成为独立块，并携带当前标题作为上下文。
- 单个段落超过 `chunk_size` 时，才使用 `chunk_overlap` 做滑窗兜底，避免极长段落无法检索。

## Embedding 与向量数据库核查

原核查现状：

- PostgreSQL 使用 `pgvector/pgvector:pg17` 镜像。
- 数据库扩展 `vector` 已安装，实查版本为 `0.8.5`。
- 旧 `chunks` 表存在 `embedding vector(1536)` 字段和 HNSW 索引 `ix_chunks_embedding`。
- 但当前真实上传处理链路写入的是 `document_chunks.embedding_json`，不是 `chunks.embedding`。
- `backend/app/documents/indexing.py` 当前使用本地 deterministic pseudo-embedding stub，维度为配置项 `embedding_dimensions`，用于离线/演示索引稳定性，不是真实语义向量模型。

后续修正：

- 已新增 `0011_qwen_embedding_vector`，在 `document_chunks` 增加 `embedding_vector vector(1024)` 与 HNSW 索引。
- 已幂等配置 `dashscope / text-embedding-v4 / embedding / 1024 / cosine`。
- 文档处理管线会在 `DASHSCOPE_API_KEY` 存在时调用 OpenAI 兼容 `/embeddings` 接口写入真实向量；无 key 时继续保留 stub 兜底。
- RAG 向量检索已改为读取 `document_chunks.embedding_vector`。

结论：

- 有向量数据库能力：pgvector 扩展、向量字段和 HNSW 索引均已具备。
- 已有真实 embedding 模型配置，但当前本地 `api_key_set=false`，既有 chunk 还未回填真实向量。
- 当前交付可用检索在无 DashScope Key 时仍主要依赖关键词检索和 DeepSeek 生成回答；配置 key 并重新上传或回填文档后，可启用 Qwen 向量参与 hybrid 检索。

## 验证

- `pnpm.cmd run typecheck:web` 通过。
- `pnpm.cmd run lint:web` 通过。
- `pnpm.cmd run test:web` 通过，10 个测试文件、81 个测试用例通过。
- `pnpm.cmd run build:web` 通过。
- `python -m compileall backend/app/notifications backend/app/main.py` 通过。
- `uv run ruff check app/notifications app/main.py` 通过。
- Docker API 与 Web 镜像已重建，`kb-api-server`、`kb-web` 健康。
- Alembic 已执行到 `0011_qwen_embedding_vector`。
- 通知接口冒烟：
  - 普通用户通知 3 条，未读 3 条。
  - 管理员通知 4 条，未读 4 条。
  - 并发首次加载后普通用户通知仍为 3 条，没有重复。
