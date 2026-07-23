# 2026-07-22 撤除后端 LLM Guard 修正记录

## 修正原因

后端 `BanTopics` 与 `PromptInjection` 会对正常医疗信息化问题做概率判定，存在合法问题
返回“输入不合法”的误判；CPU 模型推理同时增加了冷启动和查询等待时间。

## 修正内容

| 模块 | 修正结果 |
|---|---|
| FastAPI 输入校验 | 删除模型扫描，只保留 NFKC 规范化后的明确涉黄、涉赌、涉毒词条校验 |
| 应用生命周期 | 删除模型后台预热、线程池与关闭逻辑 |
| 健康检查 | Ready 仅检查数据库、Redis 和文件存储 |
| Python 依赖 | 删除 `llm-guard`、PyTorch、Transformers 及其守卫专用间接依赖 |
| Docker | 删除 Hugging Face 缓存目录、环境变量和命名卷 |
| 前端交互 | 保留明确敏感词即时提示和搜索按钮禁用 |
| 文档 | 将原 LLM Guard 方案标记为已撤销，并同步本地及云部署说明 |

## 行为变化

- 正常医疗问题和一般指令表达不再经过 `BanTopics` 或 `PromptInjection`，可直接进入 RAG。
- 明确命中涉黄、涉赌、涉毒词表的输入仍在前后端被拒绝。
- 复杂改写主题和提示词注入不再由本地输入模型识别，需由权限、审计、模型供应商内容安全
  和网关策略共同治理。

## 验证记录

- 后端迁移和 `alembic check` 通过，Ruff、mypy 均无问题。
- 后端全量测试 `382 passed, 2 skipped`，覆盖率 61.79%；样本校验 45 通过、0 失败、
  20 待制作。
- 前端 TypeScript、ESLint、生产构建通过，95 个 Vitest 测试全部通过。
- 静态 OpenAPI 与 FastAPI 运行时契约一致，生成类型已同步。
- 使用新锁文件无缓存构建成功；运行依赖不再包含 `llm-guard`、PyTorch、Transformers。
- 本地 API、Worker、Web、PostgreSQL、Redis 全部健康；Ready 只返回
  `database/redis/storage=ok`。
- 实际 API 容器接受“请说明医院感染控制与病毒防控信息系统的建设方案”，且启动日志没有
  输入模型加载或预热记录。
