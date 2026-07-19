# 项目长期记忆

## 架构与范围

- 智能知识库平台采用 Git Monorepo、一个统一 Vue 3 前端、一个 FastAPI 模块化单体、独立 Worker、PostgreSQL + pgvector 和 Redis。
- 首期部署单元为 `web`、`api-server`、`worker`、`postgres`、`redis`；不拆分认证、文档或 RAG 微服务。
- 原始文件和标准化 Markdown 都必须保留；文档处理、OCR、索引和大型导出使用异步任务。

## 协作边界

- 2026-07-15 员工 2 离职，其管理端前端职责由员工 1 接管；当前团队保留员工编号 1、3、4、5、6。
- 员工 1 主责统一的 `frontend/web`，其中普通用户工作区与 `/admin` 管理中心共用登录、组件、API 类型、构建和部署产物。
- 2026-07-15 项目负责人将登录页、普通用户工作区和管理中心分别作为三类界面基线；其后对任一基线的样式、内容或交互调整，都必须同步到该区域的共享布局、组件、响应式状态以及后续对应子功能和子页面，禁止只修当前页面或沿用过期基线。
- 管理员可同时使用普通用户功能和管理中心；管理入口、路由和按钮由权限码控制，后端对所有管理请求最终鉴权。
- 员工 3 提供认证、个人信息、权限码和统一错误结构；员工 4 提供知识库文档、Markdown、资源和引用定位；员工 5 提供检索、问答、会话、反馈、导出和收藏接口；员工 6 维护治理、CI 和部署基线。
- OpenAPI 是前后端接口单一事实来源；生成的 TypeScript 类型和 Mock 使用同一契约，未确认字段不能被标记为联调完成。

## 长期安全与实现决定

- 前端认证优先使用 HttpOnly Cookie，不在 localStorage、URL 或日志中保存 Token。
- 流式问答使用原生 Fetch + ReadableStream + TextDecoder + AbortController，不新增专用 SSE 依赖。
- Markdown 采用服务端清洗加前端 DOMPurify 二次过滤；下载统一走鉴权接口。
- 每个新功能分支从最新 `main` 创建；依赖分支必须等待父 PR 合并，避免堆叠未合并代码造成冲突。
- 2026-07-15 确认员工 1 的统一前端 P0 采用整体交付：一个总 Issue、一个 `feature/<issue>-unified-web-p0` 长期功能分支、15 个里程碑和一个持续更新的 Draft PR。每个里程碑先本地通过再推送；全量本地 E2E、最终 CI 和测试环境验收通过后才转 Ready；合并后统一关闭总 Issue 并删除长期分支。
- 2026-07-15 项目负责人废除“管理员必须把 `quality` 配置为 GitHub 必需状态检查”的规则；它不再是编码启动或里程碑验收条件。每个里程碑的本地门禁、Pull Request CI 和非作者评审仍然保留。
- 2026-07-15 M01 首装审计确认原固定版本 Axios `1.13.2` 与 Vite `7.2.2` 已受高危安全公告影响，因此只做安全补丁升级并重新固定为 Axios `1.18.1`、Vite `7.3.6`。
- 2026-07-15 项目负责人批准 V2 前端改版采用 Ant Design Vue 与 pnpm；仓库固定为 registry 当前可用的 `ant-design-vue@4.2.6`、`pnpm@11.13.0` 和 `@lucide/vue@1.24.0`。提示词中的 Ant Design Vue 5.x 当前不存在；`lucide-vue-next@1.0.0` 已被官方废弃并要求改用 `@lucide/vue`，两者都不能照搬为实现版本。
- 2026-07-16 项目负责人确认 M01 V2 为正式视觉与交互基线，对应生产实现提交 `4903e9d`；M02–M14 的本地页面必须继承其 tokens、用户/管理壳层、响应式和无障碍行为。后续真实认证、权限和业务联调仍以 OpenAPI 为准，不能用 design-only 页面替代。
- 2026-07-16 M02–M14 已按 M01 V2 建立 18 个工作区正式路由的本地可交互基线；个人资料保留为账号菜单弹窗，不新增 `/profile`，管理端“用户与角色”“文档与任务”使用组合子导航。2026-07-17 项目负责人要求个人资料弹窗同步优化为紧凑身份头、资料概览和接入说明，桌面双列、移动端单列；用户端保留 `/preferences` 主操作，仍不虚构资料编辑或认证接口。固定样例只用于页面与交互验证，真实认证、权限、上传、下载、轮询和流式问答继续等待 OpenAPI 契约。
- 2026-07-16 用户工作区首页升级为企业 AI 搜索工作台，复用 M01 V2 壳层与 tokens，并新增搜索结果、知识空间、数据源、历史、收藏和搜索设置路由。2026-07-17 项目负责人确认搜索设置不显示在用户主导航，`/settings` 页面与底部账号菜单入口继续保留；用户主导航将“AI 助手”放在第二位、紧随“AI 搜索”，移动端底部四个高频入口顺序不变。当前业务数据与交互均使用严格类型的本地 Mock；Markdown 通过 `markdown-it@14.1.0` 禁用 HTML 后再由 `dompurify@3.3.0` 二次过滤。真实搜索、文件上传、收藏持久化与权限联调继续以 OpenAPI 契约为准。
- 2026-07-16 项目负责人要求模块命名保持一致：侧栏直达模块名称必须与顶栏标题和页面主标题对应；结果页、详情页可使用上下文标题，但面包屑父级和 eyebrow 必须显示所属模块的规范名称。
- 2026-07-17 项目负责人批准通知中心、帮助中心和偏好设置开始前端实现；当前新增 `/notifications`、`/admin/notifications`、`/help`、`/preferences` 本地交互基线。桌面端通知铃铛在鼠标移入或键盘聚焦时预览最近 4 条通知，预览卡片水平中心与铃铛中心对齐，预览内可将当前区域通知全部标为已读；点击铃铛仍进入完整通知中心，移动端保持直接跳转。通知未读状态按用户端与管理端分别保存在当前 Pinia 会话，帮助搜索和偏好表单保持页面局部状态；在 OpenAPI 契约确认前不创建生产接口、不做持久化或外部客服集成。
- 2026-07-17 偏好设置的全局外观模式固定为“跟随系统、浅色、深色”三档，由独立 Pinia Store 同步用户端、管理端、登录页和异常页，并驱动语义 CSS tokens 与 Ant Design Vue 主题算法。仅浅色/深色枚举写入固定的 `localStorage` 键；跟随系统不写存储，通知、账号资料和其他业务偏好仍不持久化。
- 2026-07-18 前后端联调确认：`dev:web:api` 是统一前端访问真实 FastAPI 的唯一前端运行模式，`dev:web` 和 Vitest 继续使用 Mock；前端 Access Token 只保存在运行时内存，由统一 API Client 注入 `Authorization`，401 时通过后端 HttpOnly `refresh_token` Cookie 刷新一次并重放请求，不写入 `localStorage`。
- 2026-07-18 AI 搜索真实联调先走后端关键词检索以保证无外部 embedding 模型配置时可交付；前端 `smart`、`precise`、`document` 暂映射为后端 `keyword`，后续接入真实 embedding/rerank 模型后再开放 `hybrid` 和 `vector`。
- 2026-07-18 员工 5 检索路由历史权限码 `retrieval:read` 与员工 3 种子权限码 `retrieval.search` 存在命名差异；联调层保留二者兼容，新增接口时优先沿用种子数据和 OpenAPI 确认后的权限码，避免登录成功后业务接口被 403 阻断。
- 2026-07-18 明天交付最小闭环以员工 4 文档处理产物 `document_chunks` 作为 RAG 关键词检索事实来源；员工 5 原检索 SQL 不再读取独立 `chunks` 表，否则上传后的文档无法被检索命中。
- 2026-07-18 知识库创建接口必须同步创建创建人的用户级知识库 `admin` 授权；管理员角色可旁路查看全部知识库。这个兼容保证空库环境中“创建知识库 -> 上传文档 -> 检索”不会被权限模型卡住。
- 2026-07-18 种子数据需要保留默认知识库和 `document.upload` 权限码，便于 Docker 或本地数据库初始化后直接做最小演示；已有旧库若未重新 seed，管理员仍可通过 `admin.document.upload` 完成上传。
- 2026-07-18 真实 API 运行模式统一由 `frontend/web/src/config/runtime.ts` 控制：`dev:web:api` 与生产 Docker 构建默认访问真实后端，`dev:web`、Vitest 和显式 `VITE_USE_REAL_API=false` 才使用 Mock。后续新增前端服务不得再直接散落判断 `import.meta.env.MODE === "api"`。
- 2026-07-18 真实 API 模式下前端路由启用登录守卫：业务路由先检查内存 Access Token，没有 Token 时尝试用 HttpOnly Refresh Token 恢复，失败再跳转 `/login?redirect=...`；Mock 和测试模式不启用守卫，以保留设计验收路径。

## 非机密仓库备注

- GitHub 仓库：`studynightfive/team_projects`，默认分支 `main`。
- 2026-07-19 RAG 真实问答链路新增 `POST /api/v1/retrieval/answer`：后端先复用真实检索命中文档片段，再调用 DeepSeek OpenAI 兼容聊天接口生成基于引用的答案；前端 AI 搜索与 AI 助手真实模式均走该接口。文档切分继续使用本地 Markdown-aware chunker，以保证处理结果稳定、可重复、可追溯；DeepSeek 不负责原文切分。Chunker 优先按 Markdown 标题、段落、表格和代码块形成语义块，`chunk_size`/`chunk_overlap` 仅用于超长段落兜底滑窗拆分。
- 2026-07-19 DeepSeek 聊天模型默认使用 `deepseek-v4-pro`；真实 API 模式下搜索问题不写入 URL 查询参数，刷新页面不恢复上一条提问，避免问题内容残留在地址栏。
- 2026-07-19 RAG 回答完成后会复用已有 `conversations/messages` 表保存用户问题、AI 回答和引用；真实 API 模式下历史会话与搜索历史从该表读取，我的空间从真实知识库列表读取，收藏内容通过 `/api/v1/favorites` 写入后端收藏表。
- 2026-07-19 真实 API 模式下，AI 搜索框的知识库选择必须从 `/api/v1/knowledge-bases` 读取当前账号可访问知识库；选中项通过 `workspaceId` 传入前端搜索请求，并由真实 RAG 服务转换为后端 `kb_id`。知识库名称按去首尾空格、大小写不敏感规则唯一，服务层返回 409，数据库层通过 `uq_knowledge_bases_name_normalized` 防止并发重名。
- 2026-07-19 交付演示范围收敛为企业知识库闭环，用户端不再暴露 `/data-sources` 页面、导航或顶部状态入口；真实模式“我的下载”统一调用 `/api/v1/exports`，下载文件必须使用后端返回的签名 `download_url` 走鉴权接口，不展示固定下载样例。
- 2026-07-19 因后端没有独立深度研究任务接口，用户端移除 `/research` 页面、导航、首页快捷入口和 `research` 搜索模式；当前交付只保留真实可用的 AI 搜索/RAG 问答、企业知识库、上传、历史、收藏和下载闭环。
- 2026-07-19 管理中心页面统一改为真实 API 服务层读取和写入，不再在页面内直接读取 `localPageData` 或 `foundationData` 固定样例；测试环境只保留接口形状 mock。API 启动会幂等补齐演示账号 `admin/admin123`、`liuhaiwang/1234567`、`qmxl/1234567`，注册页通过公开查重接口和后端唯一性约束避免账号 ID 重复，注册成功的普通用户进入用户管理列表。
- 2026-07-19 用户端交付范围继续收敛：AI 助手页面因与 AI 搜索共用同一条真实 RAG 回答链路而移除，问答入口统一到 AI 搜索，记录查看保留在历史会话；用户与管理员壳层账号资料统一来自登录态 `/api/v1/me`，真实 API 模式下 `/admin` 路由必须具备管理员权限。
- 2026-07-19 认证与权限边界进一步收敛：登录接口 401 在登录页显示账号或密码错误，普通业务接口 401 仍表示会话失效；退出登录必须调用 `/api/v1/auth/logout` 并清理前端内存会话。管理员编辑已有用户时只允许调整角色，不修改账号 ID 或姓名；企业知识库页按 `admin.knowledge_base.create` 权限展示创建入口，超级管理员与知识库编辑者可创建知识库，普通用户不展示入口且后端继续返回 403。
- 2026-07-19 通知中心已接入真实 API：新增 `notifications` 表和 `/api/v1/notifications` 读写接口，用户通知按当前登录用户持久化，管理员通知仅管理员可见；前端顶栏预览和通知中心真实模式不再读取固定样例。RAG 索引核查结论：上传文档会转 Markdown 并写入 `document_chunks`；已新增 `document_chunks.embedding_vector vector(1024)` 和 HNSW 索引，并配置 `dashscope / qwen3.7-text-embedding` 作为默认 Qwen embedding 模型；无 `DASHSCOPE_API_KEY` 时仍保留 `embedding_json` deterministic stub 兜底。
- 2026-07-19 晚间真实 RAG 联调确认：`deploy/env/.env` 是 Docker 生效配置文件；DeepSeek 与 DashScope Key 仅保存在该本地文件。演示文档重新处理后 30 个 active chunk 均写入 1024 维 `embedding_vector`，`/api/v1/retrieval/answer` 通过 `hybrid` 检索加 `deepseek-v4-pro` 生成带引用编号的答案。
- 2026-07-19 AI 搜索页的范围选择收敛为单一真实知识库选择，不再提供“全部企业知识/全部当前知识库”聚合范围；右侧辅助信息只展示真实知识库列表统计与 RAG citations。知识库上传和管理权限边界固定为：超级管理员与知识库编辑者可上传、创建、编辑知识库，普通用户只能查看、检索和问答。
- 2026-07-19 文档模块的知识库访问鉴权必须同时检查用户级和角色级 `KnowledgeBasePermission`，与知识库列表和 `/me` 的权限继承保持一致；普通用户可进入有权知识库的文档目录和文档预览，但上传仍必须具备 `document.upload` 或 `admin.document.upload`。真实前端详情页在接口加载完成前只显示加载态，不得先渲染“知识库不存在/文档不存在”。
- 2026-07-19 管理端模型管理必须把 RAG 链路显式拆成聊天模型和 embedding 模型：DeepSeek 聊天模型从 `DEEPSEEK_CHAT_MODEL`/`DEEPSEEK_API_KEY` 幂等写入模型表，Qwen embedding 模型从 DashScope 配置写入；AI 搜索真实模式的模型下拉读取启用聊天模型并向 `/api/v1/retrieval/answer` 传递 `chat_model_id`。管理端页面不得回退到固定样例；命中率测试页已接入真实测试集创建/编辑、候选 chunk 检索、keyword/vector/hybrid 运行和指标明细，不再依赖固定样例或只读后端数据。
- 2026-07-19 交付演示可使用真实 API 中的 `医疗信息化演示测试集`：绑定演示知识库 10 个医疗信息化问题和真实 `document_chunks.id`，推荐参数 `hybrid / TopK 8 / threshold 0 / rerank false`；当前验证结果为 10 题命中 9 题，Hit Rate `0.9`。
- 2026-07-15 接管项目治理时，远端 `main` 基线为 `c57255a162ffbd8ba59e353f9f46588c2e80e192`，仓库尚无工程代码、治理文件、Issue 模板或 CI。
- 当前协作账号对仓库是 Write 权限而不是 Admin；项目不再要求管理员配置 GitHub 必需状态检查，也不再维护分支保护配置脚本。
- 项目直接依赖必须精确锁定；Node.js `22.23.1`、pnpm `11.13.0`、Python `3.10.20`、uv `0.8.22`。
- 2026-07-16 员工6 初始化后端基础设施时发现两个依赖版本冲突，已修复并记录：
  - `redis` 从方案定版 `6.4.0` 降级为 `5.2.1`：`arq==0.26.3` 的依赖约束为 `redis>=4.2.0,<6`，不兼容 redis 6.x。后续若需升级 redis 6.x，必须同步升级 arq 到支持 redis 6 的版本。
  - `pydantic-settings` 从方案定版 `2.12.0` 升级为 `2.14.0`：`docling==2.112.0` 的传递依赖 `docling-core` 要求 `pydantic-settings>=2.14.0`。后续若需降级 pydantic-settings，必须同步降级 docling 到兼容版本。
  - 以上两个版本偏离已体现于 `backend/pyproject.toml` 和 `backend/uv.lock`，CI 中的 `uv sync --frozen` 以此为准。
  - 2026-07-16 CI 中 uv 从方案定版 `0.8.22` 升级为 `0.11.26`：本地生成 `uv.lock` 使用的 uv 版本为 0.11.26，旧版 CI 无法正确解析 lock 文件路径。`uv sync` 命令同步改为 `cd backend && uv sync --frozen`。

## 员工 4 文档处理（2026-07-17）

- 模块：`backend/app/documents`、`backend/app/parsers`
- 迁移：`backend/migrations/versions/0002_documents_tables.py`
- 默认 `WORKER_INLINE=true`；ARQ 任务 `process_document_task`
- 向量链路已增加真实 pgvector 字段 `document_chunks.embedding_vector vector(1024)`；配置 `DASHSCOPE_API_KEY` 后新上传文档会写入 Qwen3 embedding，旧 `embedding_json` deterministic stub 仅作为无外部模型时的处理兜底。
