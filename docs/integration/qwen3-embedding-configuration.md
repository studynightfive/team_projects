# DashScope Embedding 配置记录

日期：2026-07-19

## 修正目标

将项目从仅有本地 deterministic stub 向量，升级为可接入真实 embedding API 的链路。当前托管默认模型为 `text-embedding-v4`，项目按 1024 维向量和 cosine 距离写入 pgvector，并用于 RAG 混合检索。

参考资料：

- Qwen 官方模型卡：[Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)，支持最高 1024 维向量、32K 上下文和 100+ 语言。
- 阿里云 Model Studio Embedding 文档：[Embedding](https://www.alibabacloud.com/help/en/model-studio/embedding)，OpenAI 兼容 `/embeddings` 接口使用 `DASHSCOPE_API_KEY`，1024 维是常用推荐配置；托管模型 `text-embedding-v4` 标注为 Qwen3-Embedding 系列。

## 已完成代码修正

- 后端配置新增非密钥环境变量：
  - `DASHSCOPE_BASE_URL`
  - `QWEN_EMBEDDING_MODEL`
  - `QWEN_EMBEDDING_DIMENSIONS`
- 后端支持 `dashscope` provider，并复用现有 OpenAI-compatible `/embeddings` 适配器。
- API 启动时幂等创建默认 embedding provider 和模型记录：
  - provider：`dashscope`
  - model：`text-embedding-v4`
  - kind：`embedding`
  - dimensions：`1024`
  - distance：`cosine`
- 新增迁移 `0011_qwen_embedding_vector`：
  - `document_chunks.embedding_vector vector(1024)`
  - HNSW 索引 `ix_document_chunks_embedding_vector`
- 文档处理管线在切块后会调用已配置的 embedding 模型，将真实向量写入 `document_chunks.embedding_vector`。
- 原 `embedding_json` deterministic stub 保留，用作无外部 API Key 时的离线处理兜底。
- RAG 检索的向量检索已改为读取 `document_chunks.embedding_vector`，不再读取旧的空 `chunks.embedding`。
- 前端真实 API 模式下，AI 搜索的“智能搜索”优先请求后端 `hybrid`；当后端未配置 embedding key 或没有向量时，自动退回关键词检索，避免演示中断。

## 本地环境当前状态

当前 Docker 演示环境已执行到 Alembic `0011_qwen_embedding_vector`，模型表已有：

```text
provider_code: dashscope
model_name: text-embedding-v4
kind: embedding
dimensions: 1024
distance: cosine
enabled: true
api_key_set: false
```

说明：首次配置时本地未写入真实 DashScope 密钥，因此 `api_key_set=false`。2026-07-19 晚间联调时，`deploy/env/.env` 已补齐 DeepSeek 与 DashScope Key，后端容器已确认可以读取到密钥，模型接口显示 `api_key_set=true`。

## 演示前操作

在 `deploy/env/.env` 中添加或确认以下配置，不要提交该文件：

```env
DASHSCOPE_API_KEY=你的 DashScope 或兼容 embedding 服务密钥
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_EMBEDDING_MODEL=text-embedding-v4
QWEN_EMBEDDING_DIMENSIONS=1024
```

然后重启服务：

```powershell
docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml up -d --force-recreate api-server worker
```

已有文档是在 Qwen key 配置前处理的，初始 `embedding_vector` 为空。2026-07-19 已通过 `POST /api/v1/documents/{document_id}/reprocess` 重新处理演示文档，30 个 active chunk 均已写入 1024 维真实向量。

## 验证记录

- `python -m compileall backend/app/common/config.py backend/app/common/seed.py backend/app/documents/models.py backend/app/documents/service.py backend/app/rag/search/service.py backend/app/models/schemas.py backend/app/models/providers/openai.py backend/app/main.py backend/migrations/versions/0011_qwen_embedding_vector.py` 通过。
- `uv run ruff check app/common/config.py app/common/seed.py app/documents/models.py app/documents/service.py app/rag/search/service.py app/models/schemas.py app/models/providers/openai.py app/main.py` 通过。
- `pnpm.cmd run typecheck:web` 通过。
- `pnpm.cmd run build:web` 通过。
- Docker 镜像 `api-server`、`worker`、`web` 已重建并重启。
- `GET http://127.0.0.1/api/v1/health/live` 返回 200。
- `GET /api/v1/models?kind=embedding` 返回 Qwen embedding 模型配置。
- `POST /api/v1/retrieval/search` 使用 `mode=hybrid` 时，在未配置 DashScope Key 的状态下自动退回 `keyword` 并正常返回。
- 配置真实 Key 后，`document_chunks` 验证结果：`active_chunks=30`、`vector_chunks=30`、`vector_dims=1024`。
- `POST /api/v1/retrieval/answer` 使用 `mode=hybrid`、`model=deepseek-chat`，可基于医疗信息化演示文档生成带引用编号的 RAG 回答。

## 剩余限制

- 当前真实 Key 仅存在本地 `deploy/env/.env`，不得提交仓库。
- 后续新增文档会自动写入真实向量；若还有更早处理的旧文档，需要重新上传或调用 reprocess 才会补齐 `embedding_vector`。
- 当前未新增本地模型推理服务；如要完全离线运行 `Qwen/Qwen3-Embedding-0.6B`，需要单独引入 vLLM、Text Embeddings Inference、Ollama 或 ModelScope 服务，并把 `DASHSCOPE_BASE_URL` 指向其 OpenAI-compatible endpoint。
