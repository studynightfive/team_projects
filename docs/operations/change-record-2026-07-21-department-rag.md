# 部门化 RAG 平台修正记录

## 交付范围

本次修正围绕部门数据隔离、RAG 输入治理、答案导出、命中率测试和多模型管理展开。前端继续使用 Vue 3，后端继续使用 FastAPI 模块化单体，没有拆分微服务。

## 修正明细

| 编号 | 用户需求 | 修正结果 | 主要接口或模块 |
|---|---|---|---|
| 1 | 部门、部门管理员和部门知识库 | 新增部门管理；用户和知识库增加部门归属；超级管理员管理全部部门，部门管理员只管理本部门；普通用户只读取本部门知识库 | `/api/v1/departments`、`knowledge`、`documents`、`rag/_shared/permissions` |
| 2 | 禁止涉黄赌毒输入 | 在检索和流式问答进入业务处理前统一执行输入守卫；命中时返回 422，不创建会话、不调用检索或外部模型 | `rag/guard.py` |
| 3 | 删除历史会话和搜索历史 | 删除两个前端页面、路由和导航入口；新的 AI 搜索回答不再写入会话历史 | `router/index.ts`、`foundation.ts`、`rag/search/service.py` |
| 4 | 搜索页直接导出答案 | 搜索结果页直接下载 Markdown、TXT 或 DOCX；文件只包含问题、答案和可选引用元数据，不打包参考文档正文 | `POST /api/v1/exports/answer` |
| 5 | 单问题命中率测试 | 在原测试集模式之外增加单问题模式，返回命中结果、命中率、阈值、候选片段和耗时 | `POST /api/v1/retrieval-tests/single` |
| 6 | 多家模型供应商 | 模型管理增加 Kimi/Moonshot、智谱、MiniMax、豆包、千帆、OpenAI、DeepSeek 和 DashScope；聊天、Embedding、Rerank 仍由真实模型表驱动 | `models`、`ModelsView.vue` |
| 7 | 云上 FastAPI 部署 | 保留 FastAPI + Uvicorn API、独立 Worker、PostgreSQL/pgvector、Redis 和 Nginx 编排，并补充云部署说明 | `docs/operations/cloud-fastapi-deployment.md` |
| 8 | 用户角色单选与超级管理员保护 | 用户管理只允许单选普通用户或知识库编辑者，后端拒绝分配超级管理员；知识库编辑者权限以普通用户权限全集为基础扩展 | `users`、`common/seed.py`、`UsersView.vue` |
| 9 | 精简管理首页与 AI 搜索 | 删除管理首页快捷入口；AI 搜索删除附件和模式切换，统一使用混合智能检索并默认请求重排 | `AdminHomeView.vue`、`AiSearchBox.vue`、`ai-search-real.ts` |
| 10 | 真实命中率评测 | 删除固定医疗问题填充；每次测试都重新调用真实检索，不再复用相同配置历史结果，检索失败时整次测试明确失败 | `rag/tests/all.py`、`RetrievalTestsView.vue` |
| 11 | 文档查看与拖拽上传 | 管理文档列表可进入真实预览；有权限用户在知识库详情页可点击或拖拽批量上传 | `DocumentsView.vue`、`KnowledgeDetailView.vue` |
| 12 | 默认重排 | 请求启用重排但未指定模型时自动选择已启用且已配置密钥的重排模型；关键词、向量和混合候选均可在答案生成前重排 | `rag/search/service.py` |

## 数据库迁移

迁移 `0016_departments` 完成以下操作：

1. 新建 `departments` 表。
2. 给 `users` 和 `knowledge_bases` 增加 `department_id`。
3. 将升级前数据归入“默认部门”，并在存在超级管理员时自动指定其为默认部门管理员。
4. 将知识库名称唯一约束从全局唯一调整为“部门内忽略首尾空格和大小写唯一”。
5. 保留用户部门可空，以支持注册后由管理员分配；知识库部门不可空。

迁移 `0017_single_builtin_user_role` 清理历史账号中“普通用户 + 知识库编辑者”的重复角色关系。知识库编辑者已继承普通用户权限，因此不需要同时挂两个角色。

## 大修说明

部门化属于跨模块权限模型调整，无法仅靠新增一个页面完成，因此修改了认证用户结构、用户管理、知识库、文档、任务和 RAG 可访问范围。业务处理流程、文档解析器、Markdown 切分器、pgvector 存储结构和现有前端设计体系未重写。

多模型部分复用现有 OpenAI 兼容 Provider 适配器，没有引入新的 SDK。新增供应商均通过模型管理写入 Base URL、模型标识和密钥；密钥只写入加密字段，不在页面回显。

## 验证记录

- 前端 TypeScript 类型检查通过。
- 前端 ESLint 零警告通过。
- 前端 Vitest：11 个测试文件、88 项测试通过。
- 前端 Node 22 生产构建和 Web 镜像构建通过。
- 后端 Ruff 通过。
- 后端 Mypy：118 个源文件通过。
- 后端 Pytest：349 项通过、2 项按项目配置跳过，覆盖率 59.81%。
- PostgreSQL 空库从首个迁移升级到 `0016_departments` 成功，`alembic check` 无待生成操作。
- 真实 HTTP 冒烟：登录 200、违规检索 422、答案导出 200，导出文件包含当前问题和答案。
- FastAPI、Worker、PostgreSQL、Redis、Nginx 容器均通过健康检查；`/api/v1/health/live` 和 `/api/v1/health/ready` 返回 200。
- 1440、1280、375 像素宽度检查无页面横向溢出。

## 限制与运维提示

- 当前输入守卫是可审计的确定性规则，能处理常见分隔符规避，但不是独立语义审核模型。云上高风险场景可在同一守卫接口后增加企业内容安全服务。
- Kimi、智谱、MiniMax、豆包、千帆等按 OpenAI 兼容接口接入；使用厂商非兼容专有端点时需新增对应适配器。
- 更换 Embedding 模型后，旧向量与新模型不在同一向量空间，必须重新处理相关知识库文档。
- 云上 `SECRET_KEY` 必须不少于 32 位，且 `DEBUG=false`、`COOKIE_SECURE=true`；密钥必须由云 Secret 服务注入，不得写入镜像或仓库。
- 为兼容本地已有模型密文，开发环境允许不少于 16 位的历史 `SECRET_KEY`；生产环境仍强制不少于 32 位并要求独立配置 `MODEL_KEY_FERNET_KEY`，避免会话密钥轮换导致模型 Key 无法解密。
- 命中率测试中的“查找相关片段”只负责辅助人工标注标准答案；Hit Rate、MRR、NDCG、Recall、Precision 和 MAP 都以勾选的片段 ID 为相关集合。未正确标注时，运行再真实也不能代表业务准确率。
- 默认重排依赖模型管理中至少一个启用、已配置密钥的 rerank 模型；未配置时检索会保留融合排序，并在响应中标记 `reranked=false`。

## 本轮附加验证（管理与检索体验）

- 前端 TypeScript、ESLint、生产构建通过；Vitest 11 个文件、88 项测试通过。
- 后端 Ruff 通过；本轮 20 个相关源文件 Mypy 通过；角色、配置、重排和评测相关 23 项单元测试通过。
- 全量后端测试在宿主机运行结果为 349 项通过、2 项跳过；4 项依赖 PostgreSQL 的测试因宿主机未映射数据库端口失败。随后在 Compose 网络内复测相关用例，除既有 pytest 事件循环复用问题外均通过，该用例单独运行通过。
- Alembic 当前版本为 `0017_single_builtin_user_role (head)`，`alembic check` 无待生成操作。
- FastAPI、Worker、PostgreSQL、Redis、Nginx 五个容器健康；存活和就绪检查均返回 200。
- 浏览器实测用户角色单选、超级管理员保护、管理首页、测试集标注、管理文档预览、拖拽上传和统一 AI 搜索；1440、1280、375 宽度无页面级横向溢出，控制台无应用错误。
- 本机真实模型链路已验证通过：DeepSeek 与 DashScope Key 均从 `deploy/env/.env` 加载，数据库中的聊天、Embedding 和 Rerank 凭据均可解密。医疗知识库实测返回 `mode=hybrid`、`reranked=true`，5 个结果均包含向量分数与重排分数，DeepSeek 成功基于引用片段生成答案。

## Rerank 配置与向量重建

- 新增 `DASHSCOPE_RERANK_BASE_URL`，默认值为 `https://dashscope.aliyuncs.com/compatible-api/v1`。
- 新增 `QWEN_RERANK_MODEL`，默认值为 `qwen3-rerank`；Rerank 与 Embedding 复用 `DASHSCOPE_API_KEY`，不需要第二个阿里云 Key。
- DashScope Embedding 继续调用 `/compatible-mode/v1/embeddings`，文本 Rerank 单独调用 `/compatible-api/v1/reranks`。
- 默认 Embedding 选择优先匹配 `QWEN_EMBEDDING_MODEL`，避免误选声明维度与实际返回维度不一致的模型。
- 已重新处理医疗知识库 13 份文档，13 个任务全部成功，`document_chunks.embedding_vector` 写入 540 条 1536 维真实向量。
- 实测混合检索候选 16 条，返回 5 条；5 条均有 `vector_score` 和 `rerank_score`。Embedding 耗时约 1.6 秒，Rerank 耗时约 1.9 秒，DeepSeek 完整问答约 7.8 秒。

本地演示仍使用由 `SECRET_KEY` 派生的模型密钥加密能力。云端生产部署必须配置独立且稳定的 `MODEL_KEY_FERNET_KEY`，否则轮换 `SECRET_KEY` 会导致历史模型凭据无法解密。
