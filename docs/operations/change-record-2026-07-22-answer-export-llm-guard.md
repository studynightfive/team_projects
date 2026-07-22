# 2026-07-22 答案导出与 LLM Guard 修正记录

## 交付范围

- AI 搜索答案可选择 PDF、Word 或 Markdown，并在浏览器支持时先选择保存位置。
- 答案导出任务持久化到“我的下载”，可通过鉴权签名地址再次下载。
- FastAPI 接入真实 `BanTopics` 与 `PromptInjection`，只加载这两个安全模型。
- 涉黄赌毒规则与模型扫描覆盖检索、RAG 回答、流式问答和用户会话消息。

## 修正明细

| 模块 | 原问题 | 修正结果 |
|---|---|---|
| 答案导出 | 即时 Blob 不形成下载记录，格式与保存位置不可选 | `/api/v1/exports/answer` 创建持久任务并返回导出编号，前端先选择格式和目标位置 |
| 我的下载 | 只适合文档打包，答案记录无法准确展示 | 区分 `document` 与 `answer` 来源，展示真实文件名并复用签名下载接口 |
| 输入安全 | 仅有本地关键词规则，模型未真正加载 | 固定 `llm-guard==0.3.16`，加载 BGE-M3 BanTopics 与 PromptInjection |
| FastAPI 并发 | Transformers 同步推理会阻塞事件循环 | 单例模型放入专用线程池，推理串行化并设置请求超时 |
| 云端就绪 | API 启动完成时模型可能仍在预热 | `/api/v1/health/ready` 增加 `llm_guard` 检查，预热期间返回 503 |
| 故障策略 | 模型不可用时行为不明确 | 默认 fail closed，返回通用 503，不记录用户原文或内部异常详情 |

## 安全模型配置

配置项位于 `deploy/env/.env.example`，实际值只写入未提交的
`deploy/env/.env`：

| 配置 | 默认 | 作用 |
|---|---:|---|
| `LLM_GUARD_ENABLED` | `true` | 总开关 |
| `LLM_GUARD_PRELOAD` | `true` | FastAPI 启动后后台预热 |
| `LLM_GUARD_FAIL_CLOSED` | `true` | 扫描异常时拒绝请求 |
| `LLM_GUARD_BAN_TOPICS_THRESHOLD` | `0.5` | 禁止主题阈值 |
| `LLM_GUARD_PROMPT_INJECTION_THRESHOLD` | `0.8` | 提示词注入阈值 |
| `LLM_GUARD_SCAN_TIMEOUT_SECONDS` | `30` | 单次扫描等待上限 |
| `LLM_GUARD_THREAD_WORKERS` | `1` | 专用推理线程数 |

`llm-guard` 的未使用 Presidio 依赖声明限制旧版 `cryptography`。本项目不实例化
Presidio 扫描器，并通过 uv 覆盖依赖继续使用已锁定的 `cryptography==46.0.3`，
避免为未使用功能降低现有加密库版本。

## 运行态验收

- 前端类型检查、ESLint、94 个 Vitest 测试和生产构建通过。
- 后端迁移、`alembic check`、Ruff、mypy 和全量测试通过：381 passed、
  2 skipped，覆盖率 62.05%；样本校验 45 通过、0 失败、20 待制作。
- 首次启动下载约 1.1 GB 模型文件到命名卷 `kb-llm-guard-model-cache`。
- 本机 CPU 模式预热后日志出现 `llm_guard_models_ready`，稳定内存约 3.1 GiB。
- 正常医疗信息化问题返回 200。
- 六组中文涉黄、涉赌、涉毒同义词和隐晦表达均返回 422。
- 三组不命中词表的中文语义样本由日志明确标记为 `scanner=ban_topics`。
- 英文提示词注入返回 422，日志明确标记为 `scanner=prompt_injection`。
- 日志只包含扫描器、类别与分数，不包含用户问题原文。

## 限制与部署要求

- 本地 Compose 为 API 设置 4 GiB 上限；生产环境建议每个 API 副本至少 6 GiB
  内存、2 vCPU，并保持单容器单 Uvicorn Worker。
- 首次部署必须允许下载固定模型版本，或在发布阶段预填充模型缓存。
- `showSaveFilePicker` 仅在支持该 API 的浏览器中启用；其他浏览器回退到标准下载，
  由浏览器下载设置决定保存位置。
- 零样本分类不能替代确定性规则。中文常见规避词先由 NFKC 规则层拦截，
  BanTopics 负责补充语义覆盖，PromptInjection 独立识别提示词注入。
