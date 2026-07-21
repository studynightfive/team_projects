# 本地跑通整站并测 RAG（推荐路径）

> 现状提醒：前端 AI 搜索/问答页面仍以 **Mock** 为主，真实 RAG 效果请用后端 Swagger 或下方 curl。  
> 你这台机器刚才 **Docker Desktop 未启动**，需先打开 Docker。

## 0. 一次性准备

1. 打开 **Docker Desktop**，等到托盘图标就绪。
2. 准备一个 LLM Key（测「问答」效果必需；只测「检索」可用 local stub 不要 Key）：
   - DeepSeek：`https://platform.deepseek.com`
   - 或 OpenAI
   - 或本机 Ollama（需自行安装并 `ollama pull qwen2.5:7b`）

仓库已生成：`deploy/env/.env`（本地默认密码，勿提交）。

## 1. 起数据库（最快，推荐测 RAG）

在仓库根目录 PowerShell：

```powershell
docker compose -f deploy/docker-compose.dev.yml --env-file deploy/env/.env up -d
docker compose -f deploy/docker-compose.dev.yml ps
```

会拉取并启动：

- `pgvector/pgvector:pg17` → `localhost:5432`
- `redis:7.4.9-alpine` → `localhost:6379`

## 2. 起后端 API

```powershell
cd backend
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_base"
$env:REDIS_URL="redis://localhost:6379/0"
$env:SECRET_KEY="local-dev-secret-key-change-me-32chars"
$env:WORKER_INLINE="true"
$env:INDEXING_EMBEDDING_MODEL_ID="local"
uv sync --frozen --all-groups
uv run python -m scripts.seed_rag_demo --provider deepseek --api-key "你的KEY"
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

种子脚本会打印：

- 账号：`admin / admin123`
- `kb_id`
- `chat_model_id`（若配了 Provider）
- `embedding_model_id`（DeepSeek 无 embedding 时继续用 `local`）

打开文档：http://127.0.0.1:8000/api/v1/docs

## 3. 测 RAG（Swagger 或 curl）

把下面的 `TOKEN`、`KB_ID`、`CHAT_MODEL_ID` 换成实际值。

```powershell
# 登录
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'
# Cookie 或 token 以实际响应为准；若返回 access_token：
$token = $login.data.access_token
$headers = @{ Authorization = "Bearer $token" }

# 上传 Markdown
$kb = "<KB_ID>"
curl.exe -X POST "http://127.0.0.1:8000/api/v1/knowledge-bases/$kb/documents" `
  -H "Authorization: Bearer $token" `
  -F "files=@samples/readme.md;type=text/markdown" `
  -F "ocr_enabled=false"

# 关键词 / 混合检索
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/retrieval/search `
  -Headers $headers -ContentType "application/json" `
  -Body (@{
    query = "知识库"
    mode = "hybrid"
    kb_id = $kb
    top_k = 5
    rerank = $false
    embedding_model_id = "local"
    enable_query_rewrite = $true
  } | ConvertTo-Json)

# 流式问答（需 chat_model_id）
curl.exe -N -X POST http://127.0.0.1:8000/api/v1/chat/stream `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d "{\"kb_id\":\"$kb\",\"question\":\"文档里讲了什么？\",\"chat_model_id\":\"<CHAT_MODEL_ID>\",\"embedding_model_id\":\"local\",\"top_k\":5}"
```

若没有现成 md，可先：

```powershell
"# RAG 测试`n`n本文件用于 UNIQUE_TOKEN_WIDGET_ALPHA 检索验证。" | Out-File -Encoding utf8 samples\rag-demo.md
```

## 4.（可选）整容器全栈

构建较慢（含 LibreOffice/OCR）：

```powershell
docker compose -f deploy/docker-compose.yml --env-file deploy/env/.env up -d --build
# 浏览器 http://localhost/
```

前端页面目前大量 Mock，**不代表真实 RAG**；真实效果仍看 `/api/v1/docs`。

## 5. 常见卡点

| 现象 | 处理 |
|------|------|
| docker API pipe 错误 | 先启动 Docker Desktop |
| 5432 被占用 | 改 `docker-compose.dev.yml` 端口，例如 `5433:5432` |
| 登录/权限失败 | 重跑 `seed_rag_demo` |
| 检索为空 | 确认文档 status=ready，且用同一 `kb_id`；旧文档需 reprocess |
| 问答报 model not found | 种子时加 `--provider` + `--api-key` |
| 只要检索不要 LLM | embedding 用 `local`，不要调 `/chat/stream` |

## 你需要提供的

若要我在这台机器上继续代跑到「上传→检索有命中」，请确认：

1. Docker Desktop 已绿灯；
2. 是否有 DeepSeek/OpenAI Key（或已装 Ollama）。
