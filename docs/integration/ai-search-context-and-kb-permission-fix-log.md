# AI 搜索范围与知识库管理权限修正记录

## 背景

交付演示复查发现三个问题：AI 搜索页仍存在“全部企业知识”这种泛范围选项；右侧辅助信息容易被误认为固定样例；普通用户端不应具备上传和管理知识库能力，但知识库编辑者与超级管理员仍必须保留该能力。

## 修正内容

1. 收敛 AI 搜索范围。
   - 删除 AI 搜索框中的“全部企业知识/全部当前知识库”入口。
   - 搜索提交必须绑定一个真实知识库，知识库选项来自 `/api/v1/knowledge-bases`。
   - 删除右侧上下文面板中的“已选择范围”栏目，只展示当前知识库、模型、可访问知识库数量和就绪文档数量。

2. 右侧辅助信息改为真实接口结果。
   - 当前知识库、可访问知识库数量、就绪文档数量均来自真实知识库列表。
   - 引用来源概览只展示真实 RAG 返回的 citations；未检索前显示空态说明，不再展示固定来源样例。

3. 修正知识库上传与管理权限。
   - 普通用户角色不再包含 `document.upload`，普通用户端隐藏上传入口并在操作函数中二次拦截。
   - 文档上传接口只接受 `document.upload` 或 `admin.document.upload`，不再把 `document.view` 当成上传权限。
   - 知识库创建和编辑接口分别要求 `admin.knowledge_base.create`、`admin.knowledge_base.edit`。
   - 演示账号中，`admin` 和 `qmxl` 保留上传、创建、编辑知识库能力，`liuhaiwang` 只能查看和检索。

4. 清理演示 mock 残留。
   - 删除 mock 搜索范围中的“全部企业知识”选项。
   - 搜索设置页默认范围改为“企业知识库”，避免辅助页面继续出现不需要的全量企业范围口径。

## 涉及文件

- `frontend/web/src/components/search/AiSearchBox.vue`
- `frontend/web/src/components/search/SearchContextPanel.vue`
- `frontend/web/src/views/UserHomeView.vue`
- `frontend/web/src/views/user/SearchView.vue`
- `frontend/web/src/views/user/KnowledgeDetailView.vue`
- `frontend/web/src/views/user/SearchSettingsView.vue`
- `frontend/web/src/mocks/ai-search.ts`
- `backend/app/common/seed.py`
- `backend/app/documents/router.py`
- `backend/app/documents/service.py`
- `backend/app/knowledge/service.py`

## 验证记录

- 后端语法检查：`python -m compileall backend/app/common/seed.py backend/app/documents/router.py backend/app/documents/service.py backend/app/knowledge/service.py`。
- 后端 lint：`uv run ruff check app/common/seed.py app/documents/router.py app/documents/service.py app/knowledge/service.py`。
- 前端类型检查：`pnpm.cmd run typecheck:web`。
- 前端生产构建：`pnpm.cmd run build:web`。
- Docker 重建并重启：`docker compose --env-file deploy/env/.env -f deploy/docker-compose.yml build api-server worker web`，随后重启 `api-server`、`worker`、`web`。
- 真实接口权限抽查：
  - `admin`：可上传、可创建知识库、可编辑知识库。
  - `qmxl`：可上传、可创建知识库、可编辑知识库。
  - `liuhaiwang`：不可上传、不可创建知识库、不可编辑知识库。
  - 普通用户直接调用创建知识库接口返回 403。
  - 编辑者创建临时知识库返回 201，同名再次创建返回 409；临时测试数据已清理。

## 剩余说明

本次没有重构组员已有页面结构，只收敛 AI 搜索页的范围选择、上下文展示和后端权限边界。帮助、偏好等非交付闭环页面仍可能保留界面级样例，但 AI 搜索、企业知识库、上传、RAG 问答、历史、收藏和下载闭环继续使用真实 API。

## 追加修正：普通用户查看文档目录闪烁与权限继承

2026-07-19 复查发现，普通用户从企业知识库列表点击“查看文档”时，页面会先短暂显示红色“知识库不存在”错误态，随后又恢复；同时文档模块只检查用户级知识库授权，未继承角色级知识库授权，导致普通用户能看见知识库列表，但进入文档目录时可能被拒绝。

已修正：

- `KnowledgeDetailView.vue` 在真实接口加载期间优先显示加载态，加载完成后才判断知识库是否不存在；接口错误优先显示“文档加载失败”，不再误报“知识库不存在”。
- `DocumentDetailView.vue` 在真实文档详情加载期间显示“正在加载文档”，避免预览页初始渲染“文档不存在”。
- `backend/app/documents/permissions.py` 的 `user_can_access_kb` 补齐角色级 `KnowledgeBasePermission` 检查，与知识库列表和 `/me` 返回的权限模型保持一致。

补充验证：

- 普通用户 `liuhaiwang` 登录后 `/api/v1/knowledge-bases` 返回 200。
- 普通用户进入可访问知识库的 `/api/v1/knowledge-bases/{kb_id}/documents` 返回 200，即使没有文档也显示空目录，不跳转为知识库不存在。
- 普通用户上传接口 `/api/v1/knowledge-bases/{kb_id}/documents` 返回 403。

## 追加修正：企业知识库页按权限提供新建入口

2026-07-19 复查发现，超级管理员与知识库编辑者虽然后端已经具备 `admin.knowledge_base.create` 权限，但用户侧企业知识库页面没有“新建知识库”入口，演示时必须绕到管理中心才能建立新的知识库。

已修正：

- `frontend/web/src/views/user/KnowledgeListView.vue` 在真实 API 模式下读取当前登录用户权限，只有具备 `admin.knowledge_base.create` 的账号显示“新建知识库”按钮。
- 新建抽屉复用真实 `POST /api/v1/knowledge-bases` 接口，支持填写名称、说明、切分大小和重叠字符；创建成功后刷新真实知识库列表。
- 普通用户仍不展示创建入口；即使绕过前端，后端创建接口仍会返回 403。

补充验证：

- `pnpm.cmd run typecheck:web` 通过。
- `pnpm.cmd run build:web` 通过。
