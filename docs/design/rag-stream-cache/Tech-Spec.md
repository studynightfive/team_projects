# RAG 流式回答、处理摘要与相似问题缓存技术方案

## 接口契约

新增：

```http
POST /api/v1/retrieval/answer/stream
Accept: text/event-stream
Content-Type: application/json
Authorization: Bearer <access-token>
```

请求体继续复用 `RagAnswerRequest`。响应事件顺序如下：

```text
start
stage(cache)
stage(retrieval)
stage(rerank，可选)
citation*
stage(generation)
delta*
done | error
```

`stage` 是可审计执行摘要，字段包括阶段标识、显示名称、状态和已耗时；它不包含模型
思维链。`done` 返回模型、总耗时、是否生成、是否命中缓存及缓存匹配类型。

## 后端设计

### 流式生成

- 在检索模块提供流式答案生成器，复用现有 `search()`、模型解析和 Prompt 构建。
- Provider 使用已有 `stream=True` 能力，答案增量直接转换为 SSE `delta`。
- 增量过滤器跨分片移除 `<think>...</think>`，不向客户端输出隐藏推理内容。
- 只有收到完整模型结果后才写入缓存；取消和异常结果不缓存。
- SSE 响应设置 `Cache-Control: no-cache` 与 `X-Accel-Buffering: no`。

### 缓存范围

缓存范围摘要由以下数据稳定序列化后计算 SHA-256：

- 当前用户 ID；
- 当前请求实际可访问的知识库 ID 集合；
- 相关知识库中文档数量、更新时间、版本总和、活动分块数量和最新分块时间；
- 聊天、Embedding、Rerank 模型 ID；
- 检索模式、TopK、阈值、是否重排和元数据过滤条件。

文档变化会产生新的范围摘要，因此旧缓存即使尚未到期也不会被读取。

### 相似问题

- 完全匹配优先使用精确缓存键。
- 每个缓存范围维护有 TTL 的候选索引，最多读取最近的有限数量候选。
- 对规范化问题计算中英文词元、中文二元组和字符序列相似度。
- 仅达到配置的高阈值时复用，默认阈值为 `0.92`。
- Redis 连接、解码或索引异常只记录错误类型并按缓存未命中处理。

## 前端设计

- 真实 API 模式通过原生 Fetch 调用流式接口，并复用内存 Access Token。
- 使用 `ReadableStream` 与 `TextDecoder` 增量解析 SSE，支持跨网络分片事件。
- `AbortController` 同时负责重新搜索、用户取消和页面卸载。
- 页面保留答案面板，新增紧凑的处理阶段列表和“停止生成”操作。
- 收到引用后更新来源区域，收到 `delta` 后实时更新 Markdown。
- `done` 后才开放收藏、复制和导出；缓存命中类型显示在答案说明中。
- Mock 模式继续保持原行为，不伪造真实流式网络调用。

## 兼容性

- `/api/v1/retrieval/answer` 请求结构不变，只新增可选响应字段。
- `from_cache` 保留；新增 `cache_match` 与 `cache_similarity`。
- `/api/v1/chat/stream` 不删除、不改为 AI 搜索依赖。

## 验证步骤

1. 单元测试覆盖缓存范围、文档版本变化、精确命中、相似命中、低相似不命中和 Redis 降级。
2. 后端接口测试覆盖 SSE 顺序、思维标签过滤、取消及异常事件。
3. 前端测试覆盖分片解析、实时答案、引用更新、取消和错误收尾。
4. 重新导出 OpenAPI 并生成 TypeScript 类型。
5. 运行 Ruff、mypy、后端测试、前端类型检查、Lint、组件测试与生产构建。
6. 在 1440px、1280px 和 375px 下验证加载、生成、缓存命中、失败和取消状态。
