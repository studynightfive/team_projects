# 云端验收缺口修正 Tech-Spec

## RAG 预处理

新增统一查询预处理服务。NFKC 关键词规则只提供风险候选，再复用所选聊天模型做结构化
JSON 语义判定，同时产出 `primary` 和少量 `variants`。结果按“模型 + 规范化问题”写入 Redis 短期
缓存；没有模型、模型超时或返回非法 JSON 时保留规则改写并按配置降级。

检索服务接受预处理后的多查询列表：关键词对各变体检索，向量只计算主查询一次以控制
延迟，再通过现有 RRF 合并。最终仍使用原问题执行重排和生成，避免改写改变用户意图。
会话中的省略追问把最近一条用户问题作为检索上下文，但不写入答案缓存；完整独立问题
即使位于已有对话中，也可以安全读写缓存。

新增 `POST /api/v1/retrieval/guard/check`：

```json
{
  "query": "用户输入",
  "chat_model_id": "可选模型 ID"
}
```

响应只包含 `allowed`、`category`、`message` 和 `semantic_checked`，不向前端暴露内部提示词。

## Langfuse

使用固定版本 Python SDK，封装单例客户端和空操作上下文。只有同时开启开关并提供公钥、
私钥时才初始化。trace 使用请求 ID、用户 ID、会话 ID、知识库范围、模型与耗时等结构化
元数据；默认 `LANGFUSE_CAPTURE_CONTENT=false`，不上传问题、命中片段或答案正文。

观测故障只记录不含凭据和正文的告警，不中断 RAG。流式生成结束或取消时由上下文管理器
关闭 observation，应用关闭时 flush。

## 文档与导出

- `BatchReprocessRequest.options` 继续作为事实契约，前端补传 `chunk_strategy`、
  `chunk_size`、`chunk_overlap`，切分大小与处理服务统一限制为 200–4000。
- 删除成功后按 ID 更新活动列表和回收站，再发起一次 `silent` 加载；加载状态不切换为
  loading，防止内容闪烁。
- `AnswerExportRequest.filename` 与 `ConvertAnswerExportRequest.filename` 为可选基础文件名。
  后端移除扩展名、路径分隔符、控制字符和 Windows 保留名，限制长度，再按目标格式追加
  扩展名。未提供时维持原时间戳命名。

## 部门看板

服务端先解析唯一作用域，然后所有语句复用该部门条件。前端校验响应作用域与当前选择
一致，并用请求序号阻止迟到响应覆盖新范围。只有超级管理员显示“全部部门/其他部门”
选择器；普通部门管理员固定本部门，避免展示一个必然被后端拒绝的选项。

## 配置

- `RAG_SEMANTIC_GUARD_ENABLED=true`
- `RAG_SEMANTIC_GUARD_MODEL_ID=`
- `RAG_SEMANTIC_GUARD_TIMEOUT_SECONDS=8`
- `RAG_QUERY_PREPROCESS_CACHE_TTL_SECONDS=900`
- `RAG_SEMANTIC_GUARD_FAIL_CLOSED=false`
- `LANGFUSE_ENABLED=false`
- `LANGFUSE_PUBLIC_KEY=`
- `LANGFUSE_SECRET_KEY=`
- `LANGFUSE_BASE_URL=https://cloud.langfuse.com`
- `LANGFUSE_ENVIRONMENT=development`
- `LANGFUSE_RELEASE=`
- `LANGFUSE_CAPTURE_CONTENT=false`

## 验证

运行后端 Ruff、Mypy、相关单元/契约/集成测试；更新 OpenAPI 并生成前端类型；运行前端
TypeScript、ESLint、Vitest 和生产构建。文档删除、重新处理、导出弹窗和看板额外检查
375px、1280px、1440px 三种宽度。
