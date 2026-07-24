# 业务看板与用户激励机制技术方案

## 1. 技术选择

新增结构化 `retrieval_metrics` 表记录检索完成事实。审计日志继续负责“谁执行了什么操作”，
指标表负责“这次检索命中了多少、是否生成、是否使用缓存、耗时多少”。两类数据职责不同，
避免从自由文本审计详情中解析 KPI。

积分不新增可写余额表，而是从已就绪文档事实动态聚合。这样可以天然避免重复处理、事务回放
或后台任务重试造成重复加分，也不需要维护积分余额与文档状态的一致性。

## 2. 数据模型

`retrieval_metrics`：

- `id`：UUID 主键。
- `user_id`：请求用户，删除用户后置空。
- `department_id`：请求发生时的部门快照，删除部门后置空。
- `knowledge_base_id`：检索范围，可为空。
- `event_type`：`search` 或 `answer`。
- `hit_count`：最终引用分块数。
- `generated`：是否完成模型生成。
- `cache_hit`：是否复用答案缓存。
- `took_ms`：端到端耗时。
- `request_id`：HTTP 请求 ID。
- `created_at`：记录时间。

`event_type + request_id` 设置唯一约束，防止同一请求因重试提交两次指标。

## 3. 写入时机

- `/retrieval/search`：搜索成功后写入 `search` 记录，与审计日志同一事务提交。
- `/retrieval/answer`：回答成功后写入 `answer` 记录。
- `/retrieval/answer/stream`：收到内部 `done` 事件后保存其耗时、生成和缓存字段，并使用已发出的
  citation 数作为命中数；客户端取消或流异常不伪装为完成。

指标写入只保存数值和标识，不保存问题、回答或敏感原文。

## 4. API

### 4.1 管理业务看板

`GET /api/v1/admin/dashboard`

查询参数：

- `days`：`7 | 30 | 90`，默认 30。
- `department_id`：超级管理员可选；部门管理员固定为本部门。
- `leaderboard_page`：默认 1。
- `leaderboard_page_size`：10、20 或 50，默认 10。

响应保留已有总量字段以兼容现有调用，并新增：

- `period`
- `scope`
- `knowledge_coverage`
- `active_searches`
- `effective_answers`
- `unanswered_queries`
- `document_processing`
- `answer_cache`
- `response_time`
- `department_leaderboard`

### 4.2 我的激励

`GET /api/v1/me/incentives`

查询参数：

- `page`：默认 1。
- `page_size`：10、20 或 50，默认 10。

响应：

- `points`
- `contribution_count`
- `department_rank`
- `department_member_count`
- `badges`
- `next_badge`
- `rules`
- `contributions`

## 5. 聚合与分页

- 知识库和文档统计复用 `KnowledgeBase`、`Document` 的真实状态与部门字段。
- 用户贡献按 `Document.created_by + Document.content_hash` 分组，只选择已就绪且启用索引的文档。
- 部门榜单先按用户和内容哈希去重，再聚合到部门。
- 贡献明细在数据库中完成排序、总数统计和分页，不把固定上限当作完整列表。

## 6. 前端

- 管理首页增加统计周期和部门筛选、7 项业务 KPI、部门贡献榜与刷新状态。
- 管理首页不再依赖审计日志作为主看板内容；审计页仍保留独立入口。
- 用户工作台增加紧凑的“我的贡献”区域，失败时不阻断 AI 搜索主流程。
- 分页复用 `ListPagination.vue`。
- 页面仅消费真实服务接口，不增加 Mock 样例。

## 7. 安全与性能

- 服务端强制部门数据边界，前端筛选不作为权限控制。
- 指标表不保存用户问题和答案，降低敏感数据扩散。
- 为统计期、部门、用户和事件类型建立组合索引。
- 看板聚合限定最多 90 天；分页大小最大 50。
- 贡献积分由事实动态计算，不提供客户端可写接口。

## 8. 验证

- Alembic：升级、降级往返与 `alembic check`。
- 后端：指标写入、权限范围、KPI 口径、积分去重、徽章和分页测试。
- OpenAPI：生成 YAML 与 TypeScript 类型后无差异。
- 前端：类型检查、Lint、Vitest、生产构建。
- 浏览器：1440px、1280px、375px 检查加载、空、失败、长文本与分页。
