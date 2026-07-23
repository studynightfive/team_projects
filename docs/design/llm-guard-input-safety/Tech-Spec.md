# LLM Guard 输入安全 Tech-Spec

> 状态：已于 2026-07-22 撤销。运行代码不再加载本文所述模型、线程池和缓存，替代方案见
> [撤除后端 LLM Guard 模型扫描 Tech-Spec](../remove-llm-guard-backend/Tech-Spec.md)。

## 依赖与配置

- 固定依赖 `llm-guard==0.3.16`。
- 固定 `torch==2.7.1` 并从 PyTorch 官方 CPU wheel 源安装，禁止 API 镜像引入 CUDA
  运行库。
- `llm-guard` 的未使用 Presidio 扫描器限制 `cryptography<44.1`；uv 明确覆盖为项目
  已锁定的 `cryptography==46.0.3`，不通过降级加密库解决冲突。运行时不得实例化
  Presidio 扫描器。
- `LLM_GUARD_ENABLED`：总开关，默认开启。
- `LLM_GUARD_PRELOAD`：启动后后台预热，默认开启。
- `LLM_GUARD_FAIL_CLOSED`：扫描异常是否拒绝请求，默认开启。
- `LLM_GUARD_BAN_TOPICS_THRESHOLD`：主题分类阈值，默认 `0.5`。该值与官方示例一致，
  并通过隐晦中文赌博语义用例校准；提高阈值会增加漏检风险。
- `LLM_GUARD_PROMPT_INJECTION_THRESHOLD`：提示词注入阈值，默认 `0.8`。
- `LLM_GUARD_SCAN_TIMEOUT_SECONDS`：调用方等待扫描结果的最大时间。
- `LLM_GUARD_THREAD_WORKERS`：专用推理线程池大小，默认 1。

## 运行结构

1. `ensure_safe_query` 先执行现有 NFKC 规范化关键词规则。
2. 非测试环境且开关开启时，把同步模型扫描提交到专用 `ThreadPoolExecutor`。
3. `_get_scanners` 在线程内用互斥锁构造单例，仅创建 `BanTopics` 和
   `PromptInjection`。
4. `BanTopics` 使用官方 BGE-M3 多语言模型和 `0.5` 阈值，作为规则层之外的
   语义辅助判定。中文涉黄赌毒的常见同义词与规避写法由前置 NFKC 规则层确定性
   拦截，避免仅靠零样本分类阈值造成漏检或误杀医疗问题。
5. 两个扫描器按上述顺序执行，任一拒绝即停止；不把清洗后的文本替换为用户问题。
6. 模型实例和推理调用串行化，避免 Transformers Pipeline 并发访问造成内存峰值。
7. FastAPI lifespan 创建后台预热任务，关闭时等待或取消预热并关闭线程池。

## 接入点

- `search()`：所有检索和命中率测试入口。
- `answer()`：在答案缓存之前检查，并将已检查标记传给内部检索，避免重复推理。
- `/chat/stream`：创建流响应前检查，内部检索复用已检查标记。
- `POST /conversations`：保存首问之前检查。
- `POST /conversations/{id}/messages`：仅扫描 `role=user` 的消息。

## 部署

- API 容器设置 `HF_HOME=/app/model-cache` 并挂载 `llm_guard_model_cache`。
- 模型缓存只挂载到 API，不挂载到 Worker、迁移或 Web 容器。
- 生产环境必须保持单容器单 Worker；扩容通过增加 API 容器副本完成。

## 验证

- 本地规则、模型主题拒绝、注入拒绝、正常医疗问题、超时和异常关闭测试。
- 单例构造与线程名测试。
- 检索、答案缓存前、流式问答、会话首问和追加消息入口回归测试。
- Ruff、mypy、pytest、Docker 构建与真实容器预热日志验证。
