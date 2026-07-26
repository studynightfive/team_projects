# 会话式 AI 搜索技术方案

## 1. 数据模型

在 `conversations` 表增加 `knowledge_base_ids` JSONB 字段，保存去重后的知识库 ID 列表。现有 `kb_id` 继续保存首个知识库，兼容旧会话和旧聊天接口。

旧数据迁移时写入 `[kb_id]`。读取时如果新字段为空，同样回退为 `[kb_id]`。

## 2. API 契约

### `POST /api/v1/retrieval/answer/stream`

请求体新增：

```json
{
  "conversation_id": "可选，会话 UUID"
}
```

行为：

- 未传入时，后端在通过知识库权限校验后创建会话。
- 已传入时，只允许会话所属用户续写，并校验请求知识库集合与会话范围一致。
- `start` 事件返回 `conversation_id`、当前用户消息 `message_id`。
- `done` 事件返回 `conversation_id`、助手消息 `message_id`。
- 缓存命中、无检索结果和正常生成均保存助手消息及引用。

### `GET /api/v1/conversations/{conversation_id}`

返回本人单个会话，用于刷新搜索页时恢复会话范围。`ConversationResponse` 新增：

```json
{
  "knowledge_base_ids": ["kb-1", "kb-2"]
}
```

### 会话消息

助手消息的 `citations` 保存 `SearchHit` 的完整公开字段，以便历史页面恢复引用。旧消息缺少的新字段按可选值处理。

## 3. RAG 上下文

生成消息顺序：

1. 系统约束；
2. 当前轮检索片段；
3. 最近的历史用户与助手消息；
4. 当前用户问题。

历史消息按时间升序读取，只取最新版本，并限制消息数与总字符数。检索片段仍受现有上下文预算控制。

首轮继续使用精确和语义答案缓存。存在历史消息时跳过答案缓存，原因是同一句追问在不同会话上下文中的含义可能不同；检索向量仍按当前问题计算。

## 4. 前端状态

搜索页使用：

- `draftQuery`：输入框草稿；
- `turns`：当前会话的用户问题、流式状态、答案和错误；
- `activeConversationId`：后端会话 ID；
- `workspaceIds`：当前会话固定知识库范围。

提交时先复制草稿到新轮次并清空草稿，再启动流式请求。流式回调只更新对应轮次。页面底部自动跟随最新输出，用户主动向上滚动后暂停跟随。

“新建对话”中止当前流、清空 `turns` 和 `activeConversationId`，移除 URL 中的会话 ID，但保留知识库与模型选择。

## 5. 路由与兼容

- 新增 `/conversations` 对话历史页面。
- `/favorites` 重定向到 `/conversations`，保留旧书签兼容。
- 历史页使用 `/search?conversation=<id>` 打开或继续会话；URL 不包含问题正文。
- 首页明确发起的问题仍使用一次性导航状态；空间页只传知识库预选状态。

## 6. 验证

- 后端：迁移、会话权限、流式持久化、历史提示词、缓存策略、多知识库范围。
- 前端：空间跳转、输入清空、多轮渲染、新建对话、历史分页与恢复。
- 门禁：Ruff、Mypy、Pytest、TypeScript、ESLint、Vitest、生产构建。
- 浏览器：1440px、1280px、375px，覆盖加载、空态、错误、长回答和连续提问。
