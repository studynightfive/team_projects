# 撤除后端 LLM Guard 模型扫描 Tech-Spec

## 技术决策

`app.rag.guard.ensure_safe_query` 保持异步签名和所有现有调用点，仅执行 NFKC 规范化后的
确定性关键词分类。这样无需修改检索、问答、会话和命中率测试的调用契约，也不会把同步
模型推理留在请求路径中。

## 删除范围

- 删除 `BanTopics`、`PromptInjection`、扫描器单例、推理锁、线程池、超时和故障策略。
- 删除 FastAPI lifespan 中的模型预热与关闭逻辑。
- 删除 Ready 探针中的 `llm_guard` 检查。
- 删除 `Settings` 中所有 `llm_guard_*` 字段及部署环境变量。
- 删除 `llm-guard`、`torch`、PyTorch CPU 索引和仅用于依赖冲突的 uv override。
- 删除 API 镜像的 Hugging Face 缓存目录和 Compose 命名卷。

## 保留范围

- `classify_prohibited_input` 及三类明确关键词表。
- `ensure_safe_query` 的函数名、异步接口和 422 错误契约。
- 所有业务入口在缓存、数据库写入、检索和外部模型调用之前执行校验的顺序。
- 前端搜索框的明确关键词即时提示与提交禁用。

## 验证

- 单元测试覆盖混淆敏感词、正常医疗问题、一般指令表达与业务入口短路。
- Ready 接口断言只包含 `database`、`redis`、`storage`。
- `rg` 确认运行时代码、部署配置和依赖中不再引用 LLM Guard。
- 运行 Ruff、mypy、全量 pytest，并重建本地 API/Worker 镜像验证运行态。
