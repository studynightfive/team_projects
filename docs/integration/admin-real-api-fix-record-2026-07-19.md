# 管理中心真实 API 联调修正记录（2026-07-19）

## 背景

本次修正面向交付演示前的管理中心联调。原管理中心多处页面直接读取固定演示样例，导致真实登录、注册、文档上传、RAG 检索闭环之外，管理员视角无法查看真实业务数据。

## 修正范围

- 管理首页读取 `/api/v1/admin/dashboard` 和 `/api/v1/audit-logs`。
- 用户管理读取 `/api/v1/users` 和 `/api/v1/roles`，新增、编辑、启停用、重置密码均写入真实后端。
- 角色管理新增 `/api/v1/permissions`，读取真实权限码并调用角色创建、更新、授权接口。
- 知识库管理读取 `/api/v1/knowledge-bases`，创建、编辑和归档使用真实知识库接口。
- 文档管理新增 `/api/v1/admin/documents`，读取真实文档列表，并复用真实重试和删除接口。
- 任务中心新增 `/api/v1/admin/tasks`，读取真实文档处理任务。
- 模型管理读取真实模型供应商和模型配置，支持通过真实 API 初始化 DeepSeek 供应商；密钥只写入不回显。
- 命中率测试读取真实测试集和运行记录，支持创建/编辑测试集、候选 chunk 检索、运行测试和查看逐题结果，不再生成固定本地命中结果。
- 审计日志读取真实审计日志，并在前端对 IP 和 Request ID 做掩码展示。
- 注册页新增登录/注册切换，注册前调用账号 ID 可用性检查；后端注册接口再次校验账号唯一性。

## 演示账号

API 启动会始终幂等补齐内建权限和三类基础角色，但仅当 `AUTO_SEED_DEMO_DATA=true` 且已配置合格口令时，才会创建或重置以下演示账号：

- 管理员：`admin`
- 普通用户：`liuhaiwang`
- 知识库编辑者：`qmxl`

说明：三个账号统一使用运行时 `DEMO_SEED_PASSWORD`，口令至少 12 位且不得写入仓库；生产环境禁止启用演示播种。

## 后端变更记录

- `backend/app/auth/router.py`：新增 `/api/v1/auth/check-username` 和 `/api/v1/auth/register`。
- `backend/app/users/schemas.py`、`backend/app/users/service.py`：密码最小长度改为 7 位；创建用户统一按去首尾空格后的账号 ID 做唯一性校验。
- `backend/app/common/seed.py`：将内建权限/角色初始化与演示账号播种分离；内建角色按当前白名单纠正遗留授权，`seed_demo_accounts` 自身校验演示开关和口令长度。
- `backend/app/main.py`：启动时始终幂等初始化内建授权；演示账号、默认知识库和演示模型仍只在显式启用演示播种时创建。
- `backend/app/users/role_router.py`：新增权限码列表接口。
- `backend/app/documents/router.py`、`backend/app/documents/service.py`、`backend/app/documents/schemas.py`：新增管理端文档和任务总览接口。
- `backend/app/users/dashboard_service.py`：系统概览补充真实知识库、文档、会话统计。

## 前端变更记录

- 新增 `frontend/web/src/services/admin.ts`，集中封装管理中心真实 API。
- 更新 `frontend/web/src/services/auth.ts`、`frontend/web/src/services/knowledge.ts`，补齐注册、账号查重、知识库更新、文档重试和删除服务。
- 重写管理中心页面：`AdminHomeView.vue`、`UsersView.vue`、`RolesView.vue`、`KnowledgeBasesView.vue`、`DocumentsView.vue`、`TasksView.vue`、`ModelsView.vue`、`RetrievalTestsView.vue`、`AuditLogsView.vue`。
- 更新测试环境 mock adapter：不再让管理页直接读页面固定样例，而是返回与真实后端一致的接口结构。

## 验证结果

- `pnpm.cmd run typecheck:web`：通过。
- `pnpm.cmd run lint:web`：通过。
- `pnpm.cmd run test:web`：通过，85 个测试全部通过。
- `pnpm.cmd run build:web`：通过。
- `python -m compileall backend/app backend/scripts`：通过。
- `cd backend; uv run ruff check app scripts`：通过。

## 剩余限制

- 命中率测试页面已补齐真实测试集维护能力，可在页面创建问题、标注相关 chunk 并运行测试。
- 当前本机 Node.js 为 `v24.16.0`，项目期望版本为 `22.23.1`，命令均已通过但仍会输出版本警告。

## 追加修正：角色授权体验与 RAG 模型可选

2026-07-19 复查管理中心时，角色授权抽屉过于简洁，模型管理页也没有清晰体现 RAG 使用的 DeepSeek 聊天模型和 Qwen embedding 模型。

已修正：

- 角色管理的编辑授权抽屉改为角色摘要、权限统计、模块化权限卡片和模块全选/清空操作，仍调用真实角色详情、权限列表和授权保存接口。
- 后端启动种子新增默认 DeepSeek 聊天模型记录：供应商 `deepseek`，模型名来自 `DEEPSEEK_CHAT_MODEL`，密钥来自运行时环境变量，仅加密写入数据库，不回显。
- 模型管理页新增 RAG 模型概览，分别展示回答生成模型、向量检索模型和启用配置数量。
- 模型管理新增 DeepSeek 聊天模型和向量模型的快捷创建入口，embedding 配置支持维度和距离算法字段。
- AI 搜索真实模式下，模型下拉改为从 `/api/v1/models?kind=chat` 读取启用聊天模型，提交 RAG 问答时传递 `chat_model_id`，不再使用固定模型选项。

管理端真实 API 复查结论：

- 平台总览、用户管理、角色管理、知识库管理、文档管理、任务中心、审计日志、模型管理和命中率测试均通过 `services/admin.ts` 或真实知识库服务访问后端接口。
- 当前未发现管理端页面直接读取 `localPageData`、`foundationData` 或固定 mock 样例。
- 命中率测试页已接入后端已有测试集创建/编辑能力；页面可以维护测试集、检索候选 chunk、选择 keyword/vector/hybrid 模式并查看指标明细。

## 追加修正：命中率测试页交付演示

2026-07-19 晚间补齐命中率测试前端页面，目标是今晚可演示、明天可联调。

已修正：

- `frontend/web/src/services/admin.ts`：补齐测试集创建、编辑、运行详情读取、检索候选 chunk、检索模式和指标类型。
- `frontend/web/src/views/admin/RetrievalTestsView.vue`：重做为真实 API 测试工作台，支持选择知识库、选择测试集、配置 keyword/vector/hybrid、TopK、阈值、rerank，运行后展示 Hit Rate、MRR、Recall@K、Precision@K、NDCG@K、MAP@K 和逐题命中明细。
- 测试集编辑抽屉支持新建/编辑测试集、添加问题、填充医疗演示问题、调用真实检索接口拉取候选片段并勾选为标准相关 chunk。
- `backend/app/rag/tests/all.py`：在测试集创建和编辑接口提交后刷新 ORM 对象，避免异步 SQLAlchemy 在返回 `updated_at` 时触发懒加载 500。
- 已通过真实 API 创建演示测试集 `医疗信息化演示测试集`，绑定当前演示知识库中的 10 个医疗信息化问题和真实 chunk id。

验证结果：

- `pnpm.cmd run typecheck:web`：通过。
- `pnpm.cmd run build:web`：通过；当前 Node.js 仍会提示版本为 `v24.16.0`，项目期望 `22.23.1`。
- Docker 已重新构建并替换 `kb-api-server` 与 `kb-web` 容器，确认 API 容器内包含 `db.refresh` 修复。
- 使用真实 API 运行 `医疗信息化演示测试集`，参数为 `hybrid / TopK 8 / threshold 0 / rerank false`，结果为 10 题命中 9 题，Hit Rate `0.9`，MRR `0.3417`，Recall@K `0.5567`，Precision@K `0.3875`。
