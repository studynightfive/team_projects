# 前后端联通修正记录

> 状态：2026-07-18 的历史联调快照。文中“当前”“剩余限制”和测试数量仅描述当时状态；2026-07-20 之后的真实范围、接口、权限和验证结果以 `README.md`、`docs/api/openapi.yaml`、`docs/project-audit-2026-07-20.md` 与运行时代码为准。

## 目标

将统一前端的登录、知识库、文档上传处理和 AI 搜索主链路接入 FastAPI 后端，形成明天可演示、可验证的最小交付闭环：用户登录后进入用户工作区，可以创建或查看知识库，上传文档触发后端处理并写入文档分块，随后通过 RAG 关键词检索命中同一批文档分块。

## 验收标准

- `pnpm.cmd run dev:web:api` 模式下，前端请求通过 Vite `/api` 代理访问 `http://127.0.0.1:8000/api`。
- Docker/生产构建默认使用真实 API；只有 `dev:web`、Vitest 或显式 `VITE_USE_REAL_API=false` 才使用 Mock。
- 登录页调用 `POST /api/v1/auth/login`，Access Token 仅保存在运行时内存，不写入 `localStorage`、URL 或日志。
- 真实 API 模式下，`runAiSearch` 调用 `POST /api/v1/retrieval/search`，请求字段与后端 `SearchRequest` 对齐。
- 检索响应完整转换为前端 `AiSearchResponse`、`AiAnswer`、`SearchResultItem`、`CitationSource` 所需字段，页面无需大改即可展示。
- 真实 API 模式下，`/knowledge` 调用后端知识库列表和创建接口；`/knowledge/:kb_id` 调用后端文档列表和上传接口。
- 文档上传后复用后端现有处理流程，处理产物落入 `documents` 与 `document_chunks`，RAG 关键词检索读取同一张分块表。
- Mock 模式保持现有设计验证行为，不访问真实业务网络。
- 运行与改动相称的前端类型检查、测试、构建和后端关键测试。

## 风险与约束

- 后端检索依赖数据库中已有用户、权限、知识库、文档和文档分块；若本地数据库为空，需先登录后创建知识库并上传文档。
- 当前前端大部分管理页和资料页仍是本地交互基线，缺少完整 OpenAPI 生成类型和真实列表接口接入。本次不对这些页面做大修。
- 后端权限码存在跨模块命名差异风险，联通时优先做最小兼容，不改动业务权限模型。
- 向量检索和混合检索依赖真实 embedding/rerank 模型配置；明天交付先保证关键词 RAG 检索闭环可用。

## 修正记录

- 前端统一 API Client：新增运行时 Access Token 会话，自动注入 `Authorization: Bearer <token>`；当业务请求返回 401 时，使用 HttpOnly Cookie 调用 `POST /api/v1/auth/refresh` 刷新一次并重放原请求。
- 前端代理配置：`dev:web:api` 默认仍代理到 `http://127.0.0.1:8000`；如使用当前 Docker Compose 的 Nginx 入口，可设置 `VITE_API_PROXY_TARGET=http://127.0.0.1` 后启动前端开发服务器。
- 前端真实 API 开关：新增统一运行模式配置，`dev:web:api` 与生产构建默认走真实接口，`dev:web`、测试环境和显式 `VITE_USE_REAL_API=false` 保留 Mock，避免 Docker 演示包误回到本地模拟数据。
- 登录联通：登录页改为调用 `POST /api/v1/auth/login`，成功后只把 Access Token 写入内存态会话；删除 `localStorage` Token 写入，保留后端 Refresh Token Cookie 机制。
- 登录路由守卫：真实 API 模式下，用户区和管理区在进入前先检查内存 Access Token；若没有 Token，则尝试用 HttpOnly Refresh Token 恢复会话，恢复失败再跳转 `/login?redirect=...`。Mock 和测试模式不启用该守卫。
- AI 搜索联通：`dev:web:api` 模式下，`loadAiSearchHome` 使用真实接口模式标识，`runAiSearch` 调用 `POST /api/v1/retrieval/search`，并把后端 `SearchHit` 补齐转换为前端现有 `SearchResultItem` 与 `CitationSource`。
- 真实检索模式策略：由于后端 `hybrid`/`vector` 需要已配置 embedding 模型，本次交付先将前端 `smart`、`precise`、`document` 映射为后端 `keyword`，保证无模型配置时搜索链路可用；`research` 模式已随深度研究页面移出当前交付范围。
- 页面标识修正：首页与搜索结果页根据运行模式显示“真实接口”或“模拟数据”，导出文件名和提示同步区分来源。
- 后端接口兼容：检索路由权限从单一 `retrieval:read` 调整为兼容 `retrieval.search` 与 `retrieval:read`，避免默认种子管理员登录后仍被 403 阻断。
- 后端 SQL 修正：关键词检索中的 PostgreSQL `to_tsvector('simple', ...)` 与 `plainto_tsquery('simple', ...)` 恢复为可执行写法。
- 后端知识库接口：新增最小可交付的 `GET /api/v1/knowledge-bases`、`GET /api/v1/knowledge-bases/available`、`POST /api/v1/knowledge-bases` 与 `PATCH /api/v1/knowledge-bases/{kb_id}`，返回知识库基础信息、文档数、已索引文档数和分块数。
- 后端知识库授权：管理员可查看全部知识库；普通用户只能查看自己或角色被授权的知识库；创建知识库时自动给创建人写入用户级 `admin` 授权，避免刚创建后无法上传或检索。
- 后端上传权限兼容：文档上传接口兼容 `admin.document.upload`、`document.upload` 与 `document.view`，让已有普通用户角色在拥有知识库访问权时可以完成最小上传闭环。
- 后端检索数据源统一：关键词检索从员工 5 原 `chunks` 表切换到员工 4 文档处理产出的 `document_chunks`，并关联 `documents` 补齐文档标题、页码和知识库信息，保证“上传后可检索”。
- 后端种子增强：新增幂等默认知识库种子和 `document.upload` 权限码，默认知识库授权给超级管理员角色，便于空库环境快速演示。
- 前端知识库服务：新增真实 API 服务层，封装知识库列表、创建、文档列表和多文件上传，继续复用统一 API Client 的认证与 401 刷新机制。
- 前端知识库页面：`dev:web:api` 模式下，`/knowledge` 展示真实知识库并支持创建；`/knowledge/:kb_id` 展示真实文档列表并支持上传文档。非 API 模式保留原 Mock 页面，避免影响设计验收和既有测试。

## 验证记录

- `pnpm.cmd run typecheck:web`：通过。提示当前 Node.js 为 `v24.16.0`，与仓库要求 `22.23.1` 不一致。
- `pnpm.cmd run test:web`：通过，10 个测试文件、88 个用例通过。
- `pnpm.cmd run lint:web`：通过。
- `pnpm.cmd run build:web`：通过。
- `backend/.venv/Scripts/ruff.exe check app/knowledge app/documents/router.py app/documents/service.py app/rag/_shared/permissions.py app/rag/search/service.py app/main.py app/common/seed.py scripts/seed_db.py`：通过。
- `backend/.venv/Scripts/pytest.exe tests/unit/test_employee5_search.py tests/test_health.py`：通过，27 个用例通过。
- `backend/.venv/Scripts/pytest.exe`：通过，250 个用例通过、104 个按现有标记跳过；保留 3 条既有 AsyncMock RuntimeWarning。
- `docker compose -f deploy/docker-compose.yml up -d --build api-server web worker`：通过，`kb-api-server`、`kb-web`、`kb-worker` 均已按当前代码重建并启动为 healthy。
- `http://127.0.0.1/api/v1/health/live`：返回 200；`/api/v1/openapi.json` 已包含 `/api/v1/knowledge-bases`、`/api/v1/knowledge-bases/available` 和 `/api/v1/knowledge-bases/{kb_id}`；未登录访问 `/api/v1/knowledge-bases` 返回 401，鉴权生效。
- `docker compose -f deploy/docker-compose.yml build web` 与 `docker compose -f deploy/docker-compose.yml up -d --no-build --force-recreate web`：通过，`kb-web` 已切换到最新生产构建镜像。
- Headless Chrome 打开 `http://127.0.0.1/knowledge`：真实 API 模式下未登录访问会先进入登录页，避免演示时暴露未登录工作区外壳；登录成功后会按 `redirect` 返回原业务路径。
- 历史警示：当时曾在 API 容器内直接运行 `backend/scripts/seed_db.py`。该脚本会创建或重置演示账号，现已增加 `AUTO_SEED_DEMO_DATA=true` 和至少 12 位 `DEMO_SEED_PASSWORD` 的双重门禁；不得将该历史命令用于生产初始化，生产首管理员必须使用 `backend/scripts/bootstrap_admin.py` 交互创建。

## 剩余限制

- 当前完成明天交付所需的登录、知识库创建/查看、文档上传处理和 RAG 关键词检索主链路；管理端列表、收藏、历史、数据源、会话和导出等页面仍有大量本地 Mock，需后续按 OpenAPI 分模块接入。
- 本地真实检索效果依赖文档是否已处理出有效 `document_chunks`。若上传后仍在处理中，检索会暂时返回空结果，需要等待处理完成或查看后端任务日志。
- 向量和混合检索需要后端配置 embedding/rerank 模型后再开启；否则会因缺少 `embedding_model_id` 或模型配置失败。
- 已完成 Docker 级健康、路由和未登录页面冒烟；为避免在命令和日志中暴露演示账号密码，未自动提交登录表单。今晚演示前需使用实际演示账号手工走一遍“登录 -> 创建或进入知识库 -> 上传文档 -> 搜索命中”的业务路径。
